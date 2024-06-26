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
                        detect_and_store_anomaly(message.value.decode('utf-8'))
            else:
                logger.error("Kafka client could not be initialized. Retrying...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error consuming Kafka messages: {e}. Attempting to restart consumer.")
            time.sleep(5)

def detect_and_store_anomaly(message):
    logger.debug(f"Analyzing message for anomalies: {message}")
    parsed_message = json.loads(message)

    # Define anomaly conditions for each type
    is_anomaly = False
    event_type = parsed_message['type']

    if event_type == "addArtist":
        # Anomaly condition: more than 5 top tracks or more than 3 certifications
        if len(parsed_message['payload'].get('top_tracks', [])) > 5 or len(parsed_message['payload'].get('certifications', [])) > 3:
            is_anomaly = True

    elif event_type == "updateSocialMedia":
        # Anomaly condition: more than 1 million followers or more than 1,000,000 plays
        if parsed_message['payload'].get('followers', 0) > 1000000 or parsed_message['payload'].get('plays', 0) > 1000000:
            is_anomaly = True

    elif event_type == "trackArtist":
        # track artist doesn't really allow for anomalies
        is_anomaly = False

    elif event_type == "updateRadioPlay":
        # Anomaly condition: more than 1000000 spins or fewer than 10 spins
        if parsed_message['payload'].get('spins', 0) > 1000000 or parsed_message['payload'].get('spins', 0) < 10:
            is_anomaly = True

    # Log and store the anomaly if detected
    if is_anomaly:
        store_anomaly_log(message)
        logger.info(f"Anomaly detected and logged for event type: {event_type}")
    else:
        logger.info(f"No anomaly detected for event type: {event_type}")

def store_anomaly_log(message):
    logger.debug(f"Storing event log: {message}")
    parsed_message = json.loads(message)
    connection = sqlite3.connect('/data/anomaly_logs.db')
    cursor = connection.cursor()
    try:
        # Prepare data to insert
        event_id = uuid.uuid4()  # Generate a new UUID for each event
        trace_id = parsed_message['payload']['trace_id']
        event_type = parsed_message['type']
        anomaly_type = 'anomaly'  # Static value as per original code
        description = f"Anomaly in event type {event_type}"
        date_created = parsed_message['datetime']

        # Execute insert statement
        cursor.execute('''
            INSERT INTO anomalies (event_id, trace_id, event_type, anomaly_type, description, date_created)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(event_id), trace_id, event_type, anomaly_type, description, date_created))

        connection.commit()
        logger.info(f"Successfully stored anomaly event with uid {event_id} and type {event_type}")

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
    logger.debug("Fetching detailed anomaly records from the database.")
    grouped_anomalies = {}  # This will store the categorized anomalies

    try:
        connection = sqlite3.connect('/data/anomaly_logs.db')
        cursor = connection.cursor()

        # Fetch all columns for all anomalies
        cursor.execute('''
            SELECT anomaly_type, event_id, trace_id, event_type, description, date_created FROM anomalies
        ''')

        # Process each row in the fetched data
        for row in cursor.fetchall():
            anomaly_type, event_id, trace_id, event_type, description, date_created = row
            # Initialize a list for the anomaly type if it has not been used yet
            if anomaly_type not in grouped_anomalies:
                grouped_anomalies[anomaly_type] = []

            # Append a dictionary of this row's data to the appropriate list
            grouped_anomalies[anomaly_type].append({
                'event_id': event_id,
                'trace_id': trace_id,
                'event_type': event_type,
                'description': description,
                'date_created': date_created
            })

        logger.info(f"Successfully fetched and grouped anomaly records: {json.dumps(grouped_anomalies, indent=2)}")

    except Exception as e:
        logger.error(f"Failed to fetch anomaly records due to an error: {e}")

    finally:
        connection.close()
        logger.debug("Database connection closed.")

    return grouped_anomalies

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

