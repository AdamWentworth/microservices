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

# New code to determine the environment and load configuration files accordingly
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

logger = logging.getLogger(__name__)
logger.info(f"Logging configured using {log_conf_file}, running in {'Test' if 'TARGET_ENV' in os.environ and os.environ['TARGET_ENV'] == 'test' else 'Dev'} environment")

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
logger.info(f"Application configuration loaded from {app_conf_file}")

def initialize_db():
    logger.debug("Initializing database and tables if not exists")
    connection = sqlite3.connect('event_logs.db')
    cursor = connection.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_logs (
            id INTEGER PRIMARY KEY,
            uid TEXT NOT NULL UNIQUE,
            message TEXT NOT NULL,
            code TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
                topic = client.topics[b'event_log']
                consumer = topic.get_simple_consumer()
                logger.info(f"Subscribed to topic 'event_log'")
                for message in consumer:
                    if message is not None:
                        logger.debug(f"Received message: {message.value.decode('utf-8')}")
                        store_event_log(message.value.decode('utf-8'))
            else:
                logger.error("Kafka client could not be initialized. Retrying...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error consuming Kafka messages: {e}. Attempting to restart consumer.")
            time.sleep(5)

def store_event_log(message):
    logger.debug(f"Storing event log: {message}")
    parsed_message = json.loads(message)
    connection = sqlite3.connect('event_logs.db')
    cursor = connection.cursor()
    utc_now = datetime.now(timezone.utc)
    try:
        cursor.execute('''
            INSERT INTO event_logs (uid, message, code, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (parsed_message.get('uid'), message, parsed_message.get('code'), utc_now.strftime('%Y-%m-%d %H:%M:%S')))
        connection.commit()
        logger.info(f"Successfully stored event log with uid {parsed_message.get('uid')} and code {parsed_message.get('code')}")
    except Exception as e:
        logger.error(f"Failed to insert event log into database: {e}")
    finally:
        connection.close()

def get_events_stats():
    logger.debug("Fetching events statistics from the database.")
    try:
        connection = sqlite3.connect('event_logs.db')
        cursor = connection.cursor()

        cursor.execute('''
            SELECT code, COUNT(*) FROM event_logs GROUP BY code
        ''')
        stats = {code: count for code, count in cursor.fetchall()}
        logger.info(f"Successfully fetched events statistics: {stats}")

    except Exception as e:
        logger.error(f"Failed to fetch events statistics due to an error: {e}")
        stats = {}

    finally:
        connection.close()
        logger.debug("Database connection closed.")

    return stats

def get_kafka_client(retries=5, wait_time=5):
    logger.debug(f"Attempting to connect to Kafka with {retries} retries remaining")
    with open('app_conf.yml', 'r') as f:
        config = yaml.safe_load(f.read())
        kafka_config = config['kafka']
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

# Initialize Connexion application
app = connexion.App(__name__, specification_dir='./')
app.add_api("openapi.yml", base_path="/event-logger", strict_validation=True,
            validate_responses=True)

if __name__ == '__main__':
    initialize_db()
    logger.info("Database initialized, starting Kafka consumer thread")
    Thread(target=consume_events, daemon=True).start()
    app.run(port=8120, host="0.0.0.0")
    logger.info("Application started")

