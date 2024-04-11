import os
import connexion
from connexion import NoContent
import yaml
import uuid
import logging
import logging.config
import json
import time
from datetime import datetime
from pykafka import KafkaClient

# New code to determine the environment and load configuration files accordingly
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# External Logging Configuration
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# Inside your app initialization or function, after loading app_config
kafka_config = app_config['events']
kafka_server = f"{kafka_config['hostname']}:{kafka_config['port']}"
 
def initialize_kafka_producer_with_retry(kafka_config):
    """Initialize Kafka producer with retry logic."""
    retry_count = 0
    while retry_count < kafka_config['max_retries']:
        try:
            logger.info('Attempting to connect to Kafka...')
            kafka_client = KafkaClient(hosts=f"{kafka_config['hostname']}:{kafka_config['port']}")
            kafka_topic = kafka_client.topics[str.encode(kafka_config['topic'])]
            kafka_producer = kafka_topic.get_sync_producer()
            logger.info('Successfully connected to Kafka')
            return kafka_producer
        except Exception as e:
            logger.error(f"Failed to connect to Kafka on retry {retry_count}: {e}")
            time.sleep(kafka_config['retry_interval'])
            retry_count += 1
            print('RETRYING ATTEMPT:', retry_count)
    logger.error("Failed to initialize Kafka producer after max retries")
    return None

producer = initialize_kafka_producer_with_retry(kafka_config)

def generate_trace_id():
    return str(uuid.uuid4())

# Function for adding a new artist profile
def addArtist(body):
    event_name = "addArtist"
    trace_id = generate_trace_id()
    body['trace_id'] = trace_id
    logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

    msg = {
        "type": event_name,
        # Use datetime.utcnow() instead of datetime.now() to get the current UTC time
        "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced {event_name} event to Kafka topic.")
    return NoContent, 201

# Function for updating artist's social media metrics
def updateSocialMedia(body):
    event_name = "updateSocialMedia"
    trace_id = generate_trace_id()
    body['trace_id'] = trace_id
    logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

    msg = {
        "type": event_name,
        "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced {event_name} event to Kafka topic.")
    return NoContent, 201

# Function for updating artist's radio play data
def updateRadioPlay(body):
    event_name = "updateRadioPlay"
    trace_id = generate_trace_id()
    body['trace_id'] = trace_id
    logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

    msg = {
        "type": event_name,
        "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced {event_name} event to Kafka topic.")
    return NoContent, 201

# Function for tracking a specific artist
def trackArtist(body):
    event_name = "trackArtist"
    trace_id = generate_trace_id()
    body['trace_id'] = trace_id
    logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

    msg = {
        "type": event_name,
        "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced {event_name} event to Kafka topic.")
    return NoContent, 201

# Setting up the Connexion application
app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api("openapi.yml", base_path="/receiver", strict_validation=True,
validate_responses=True)

if __name__ == "__main__":
    event_log_config = app_config['event_log']
    event_log_producer = initialize_kafka_producer_with_retry(event_log_config)
    if event_log_producer:
        startup_message = {
            "code": "0001",
            "message": "Receiver service ready and connected to Kafka."
        }
        event_log_producer.produce(json.dumps(startup_message).encode('utf-8'))
        logger.info("Published startup message to event_log topic.")
    app.run(port=8080, host="0.0.0.0")