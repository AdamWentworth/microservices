import connexion
import yaml
from pykafka import KafkaClient
import logging.config
from threading import Thread
import sqlite3
from datetime import datetime, timezone
import json
import time

# Setup logging
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger(__name__)

def initialize_db():
    connection = sqlite3.connect('event_logs.db')
    cursor = connection.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_logs (
            id INTEGER PRIMARY KEY,
            message TEXT NOT NULL,
            code TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    connection.commit()
    connection.close()

def consume_events():
    retry = True
    while retry:
        try:
            client = get_kafka_client()
            if client is not None:
                topic = client.topics[b'event_log']
                consumer = topic.get_simple_consumer()
                for message in consumer:
                    if message is not None:
                        logger.info(f"Received message: {message.value.decode('utf-8')}")
                        store_event_log(message.value.decode('utf-8'))
            else:
                logger.error("Kafka client could not be initialized. Retrying...")
                time.sleep(5)  # Wait a bit before retrying to avoid spamming in case of persistent issues
        except Exception as e:
            logger.error(f"Error consuming Kafka messages: {e}. Attempting to restart consumer.")
            time.sleep(5)  # Wait a bit before retrying

def store_event_log(message):
    # Assuming message is a JSON string
    parsed_message = json.loads(message)
    connection = sqlite3.connect('event_logs.db')
    cursor = connection.cursor()

    # Get the current time in UTC format
    utc_now = datetime.now(timezone.utc)

    # Insert the message into the database with the UTC timestamp
    cursor.execute('''
        INSERT INTO event_logs (message, code, timestamp)
        VALUES (?, ?, ?)
    ''', (message, parsed_message.get('code'), utc_now.strftime('%Y-%m-%d %H:%M:%S')))

    connection.commit()
    connection.close()

def get_events_stats():
    connection = sqlite3.connect('event_logs.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT code, COUNT(*) FROM event_logs GROUP BY code
    ''')

    stats = {code: count for code, count in cursor.fetchall()}
    connection.close()
    return stats

def get_kafka_client(retries=5, wait_time=5):
    """
    Attempts to connect to Kafka with retry logic.

    :param retries: Number of attempts to connect.
    :param wait_time: Time to wait between retries in seconds.
    :return: KafkaClient instance or None if connection failed.
    """
    with open('app_conf.yml', 'r') as f:
        config = yaml.safe_load(f.read())
        kafka_config = config['kafka']
    while retries > 0:
        try:
            client = KafkaClient(hosts=f"{kafka_config['hostname']}:{kafka_config['port']}")
            logger.info("Successfully connected to Kafka.")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            retries -= 1
            if retries > 0:
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    logger.error("Unable to connect to Kafka after retries.")
    return None

# Initialize Connexion application
app = connexion.App(__name__, specification_dir='./')
app.add_api("openapi.yml", base_path="/event-logger", strict_validation=True,
            validate_responses=True)

if __name__ == '__main__':
    initialize_db()
    # Start Kafka consumer in a separate thread
    Thread(target=consume_events, daemon=True).start()
    app.run(port=8120, host="0.0.0.0")
