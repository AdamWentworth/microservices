import os
import connexion
from connexion import NoContent
import yaml
import logging.config
from pykafka import KafkaClient
import json
from flask_cors import CORS  # Ensure you import CORS

# New conditional configuration loading based on TARGET_ENV
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load application and logging configuration dynamically
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# Initialize the Connexion application
app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('openapi.yml', base_path='/audit', strict_validation=True, validate_responses=True)

# Disable CORS in the test environment
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)  # app.app refers to the underlying Flask app
    app.app.config['CORS_HEADERS'] = 'Content-Type'

# Function to get an event reading based on type and index
def get_event_reading(index, event_type):
    hostname = f"{app_config['kafka']['hostname']}:{app_config['kafka']['port']}"
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config['kafka']['topic'])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    logger.info(f"Retrieving {event_type} at index {index}")
    try:
        count = 0
        for msg in consumer:
            if msg is not None:
                msg_str = msg.value.decode('utf-8')
                event = json.loads(msg_str)
                if event['type'] == event_type:
                    if count == index:
                        return event, 200
                    count += 1
        logger.error(f"{event_type} not found at index {index}")
        return {"message": "Not Found"}, 404
    except Exception as e:
        logger.error("Error retrieving message: " + str(e))
        return {"message": "Internal Server Error"}, 500

# Defining the operations for Connexion to map to
def get_artist_event(index):
    return get_event_reading(index, 'addArtist')

def get_social_media_event(index):
    return get_event_reading(index, 'updateSocialMedia')

def get_radio_play_event(index):
    return get_event_reading(index, 'updateRadioPlay')

def get_track_artist_event(index):
    return get_event_reading(index, 'trackArtist')

# Setting up the Connexion application
app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('openapi.yml', base_path='/audit', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    app.run(port=8110, host="0.0.0.0")
