import connexion
import yaml
from pykafka import KafkaClient
import logging.config
from threading import Thread
import sqlite3
from datetime import datetime, timezone
import json
import time
import os
from pykafka.common import OffsetType
import uuid

# Determine the environment and load configuration files accordingly
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Setup logging
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')
logger.info(f"Logging configured using {log_conf_file}, running in {'Test' if 'TARGET_ENV' in os.environ and os.environ['TARGET_ENV'] == 'test' else 'Dev'} environment")

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
logger.info(f"Application configuration loaded from {app_conf_file}")

def initialize_db():
    logger.debug("Initializing database and tables if not exists")
    connection = sqlite3.connect('/data/anomaly_logs.db')
    cursor = connection.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY ASC, 
            event_id VARCHAR(250) NOT NULL,
            trace_id VARCHAR(250) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            anomaly_type VARCHAR(100) NOT NULL,
            description VARCHAR(250) NOT NULL,
            date_created VARCHAR(100) NOT NULL
        )
    ''')
    connection.commit()
    connection.close()
    logger.info("Database initialization complete")

def consume_events():
    logger.info("Starting to consume events from Kafka")
    retry = True
    while retry:
        try:
            client = get_kafka_client()
            if client is not None:
                topic = client.topics[b'events']
                consumer = topic.get_simple_consumer()
                logger.info(f"Subscribed to topic 'events'")
                for message in consumer:
                    if message is not None:
                        logger.debug(f"Received message: {message.value.decode('utf-8')}")
                        store_anomaly_log(message.value.decode('utf-8'))
                        # print(f"Received message: {message.value.decode('utf-8')}")
            else:
                logger.error("Kafka client could not be initialized. Retrying...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error consuming Kafka messages: {e}. Attempting to restart consumer.")
            time.sleep(5)

def store_anomaly_log(message):
    logger.debug(f"Storing event log: {message}")
    parsed_message = json.loads(message)
    connection = sqlite3.connect('/data/anomaly_logs.db')
    cursor = connection.cursor()
    try:
        cursor.execute('''
            INSERT INTO anomalies (event_id, trace_id, event_type, anomaly_type, description, date_created)
            VALUES (?, ?, ?, ?, ?, ?)
                       
                       # I got stuck here. I was simply trying to get any data from my object to store
                       # object looks like this:
                       {"type": "addArtist", "datetime": "2024-04-14T03:30:17", "payload": {"id": "42ee3c4e-b447-49f4-9bfc-f0b32360d469", "name": "Artist PC5CX", "genre": "Genre 2GLK3", "region": "Region REACO", "top_tracks": ["Track 2", "Track 13"], "certifications": ["Certification 95HMX"], "trace_id": "dbbdd93c-2c9e-4832-9c12-9ff9c8f7869e"}}
                       # My plan once I could successfully store anything was to then add conditional logic for what an anomaly would be and only store conditionally based on that but I kept running into the same error for 90 minutes straight.
                       # 2024-04-19 00:15:57,704 - basicLogger - ERROR - Failed to insert anomaly into database: string indices must be integers
                       # I couldn't figure out how to fix it but I know if I could've gotten over this one hurdle I could've accomplished a lot more...
        ''', (uuid.uuid4().int, parsed_message.get('payload','trace_id'), parsed_message.get('type'), parsed_message.get('type'), 'anomaly', parsed_message.get('datetime')))
        connection.commit()
        logger.info(f"Successfully stored anomaly event with uid {parsed_message.get('event_id')} and type {parsed_message.get('type')}")
    except Exception as e:
        logger.error(f"Failed to insert anomaly into database: {e}")
    finally:
        connection.close()


def get_kafka_client(retries=5, wait_time=5):
    logger.debug(f"Attempting to connect to Kafka with {retries} retries remaining")
    with open('app_conf.yml', 'r') as f:
        config = yaml.safe_load(f.read())
        kafka_config = config['events']
    while retries > 0:
        try:
            client = KafkaClient(hosts=f"{kafka_config['hostname']}:{kafka_config['port']}")
            logger.info("Successfully connected to Kafka.")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}. Retrying in {wait_time} seconds...")
            retries -= 1
            time.sleep(wait_time)
    logger.error("Unable to connect to Kafka after retries.")
    return None

def get_anomalies():
    logger.debug("Fetching events statistics from the database.")
    try:
        connection = sqlite3.connect('/data/anomaly_logs.db')
        cursor = connection.cursor()

        cursor.execute('''
            SELECT anomaly_type, COUNT(*) FROM anomaly_logs GROUP BY anomaly_type
        ''')
        anomalies = {anomaly: count for anomaly, count in cursor.fetchall()}
        logger.info(f"Successfully fetched anomaly statistics: {anomalies}")

    except Exception as e:
        logger.error(f"Failed to fetch anomaly statistics due to an error: {e}")
        anomalies = {}

    finally:
        connection.close()
        logger.debug("Database connection closed.")

    return anomalies

# Initialize Connexion application
app = connexion.App(__name__, specification_dir='./')
app.add_api("openapi.yml", base_path="/anomaly_detector", strict_validation=True,
            validate_responses=True)

if __name__ == '__main__':
    initialize_db()
    logger.info("Database initialized, starting Kafka consumer thread")
    Thread(target=consume_events, daemon=True).start()
    app.run(port=8130, host="0.0.0.0")
    logger.info("Application started")

