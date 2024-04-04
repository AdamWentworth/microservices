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

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Inside your app initialization or function, after loading app_config
kafka_config = app_config['events']
kafka_server = f"{kafka_config['hostname']}:{kafka_config['port']}"

def initialize_kafka_producer():
    max_retries = kafka_config['max_retries'] 
    retry_count = 0
    sleep_interval = kafka_config['retry_interval']
    producer = None

    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to Kafka, try {retry_count + 1}")
            client = KafkaClient(hosts=kafka_server)
            topic = client.topics[str.encode(kafka_config['topic'])]
            producer = topic.get_sync_producer()
            logger.info("Kafka Producer established successfully.")
            break
        except Exception as e:
            logger.error(f"Failed to connect to Kafka on attempt {retry_count + 1}: {e}")
            time.sleep(sleep_interval)
            retry_count += 1

    if not producer:
        logger.error("Failed to establish Kafka Producer after maximum retries, exiting.")
        raise SystemExit("Kafka Producer Initialization Failure")

    return producer

producer = initialize_kafka_producer()

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
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
