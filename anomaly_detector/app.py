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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

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

# Inside your app initialization or function, after loading app_config
kafka_config = app_config['events']
kafka_server = f"{kafka_config['hostname']}:{kafka_config['port']}"

def initialize_db():
    logger.debug("Initializing database and tables if not exists")
    connection = sqlite3.connect('/data/anomaly_logs.db')
    cursor = connection.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomaly (
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

def consume_messages():
    retry_count = 0
    while retry_count < kafka_config['max_retries']:
        try:
            logger.info(f"Attempting to connect to Kafka, try {retry_count + 1}")
            client = KafkaClient(hosts=f"{kafka_config['hostname']}:{kafka_config['port']}")
            topic = client.topics[str.encode(kafka_config['topic'])]
            consumer = topic.get_simple_consumer(
                consumer_group=b'event_group',
                reset_offset_on_start=False,
                auto_offset_reset=OffsetType.LATEST
            )
            logger.info("Successfully connected to Kafka")

            break
        except Exception as e:
            logger.error(f"Failed to connect to Kafka on try {retry_count + 1}: {e}")
            time.sleep(kafka_config['retry_interval'])
            retry_count += 1

    for msg in consumer:
        if msg is not None:
            msg_str = msg.value.decode('utf-8')
            message = json.loads(msg_str)
            logger.info(f"Message: {message}")
            payload = message["payload"]
            print(payload)

            # try:
            #     if message["type"] == "addArtist":
            #         # Ensure list fields are serialized to JSON string
            #         payload['top_tracks'] = json.dumps(payload.get('top_tracks', []))
            #         payload['certifications'] = json.dumps(payload.get('certifications', []))
            #         artist = Artist(**payload)
            #         session.add(artist)

            #     elif message["type"] == "updateSocialMedia":
            #         social_media_record = session.query(SocialMedia).filter_by(
            #             artist_id=payload['artist_id'], platform=payload['platform']).first()
            #         if social_media_record:
            #             social_media_record.followers = payload['followers']
            #             social_media_record.plays = payload['plays']
            #         else:
            #             new_social_media = SocialMedia(**payload)
            #             session.add(new_social_media)

            #     session.commit()
            # except Exception as e:
            #     logger.error(f"Failed to process message: {e}")
            #     session.rollback()
            # finally:
            #     session.close()

            # consumer.commit_offsets()

def init_scheduler():
    """Initialize the scheduler to run consume_messages periodically."""
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(consume_messages, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()

# Initialize Connexion application
app = connexion.App(__name__, specification_dir='./')
app.add_api("openapi.yml", base_path="/<new service>", strict_validation=True,
            validate_responses=True)

if __name__ == '__main__':
    initialize_db()
    init_scheduler()
    app.run(port=8130, host="0.0.0.0")
    logger.info("Application started")

