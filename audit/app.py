import json
from flask import Flask, request, jsonify
from pykafka import KafkaClient
import yaml
import logging.config
from flask_cors import CORS
import os  # Import os for environment variable access

# New conditional configuration loading based on TARGET_ENV
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load application configuration dynamically
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load logging configuration dynamically
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

app = Flask(__name__)
CORS(app)

def get_event_reading(index, event_type):
    """Generic function to get an event reading based on type and index."""
    # Corrected from 'events' to 'kafka'
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
                        return jsonify(event), 200
                    count += 1
        logger.error(f"{event_type} not found at index {index}")
        return {"message": "Not Found"}, 404
    except Exception as e:
        logger.error("Error retrieving message: " + str(e))
        return {"message": "Internal Server Error"}, 500

@app.route('/artist', methods=['GET'])
def get_artist_event():
    index = request.args.get('index', default=0, type=int)
    return get_event_reading(index, 'addArtist')  # Changed from 'artist' to 'addArtist'

@app.route('/social-media', methods=['GET'])
def get_social_media_event():
    index = request.args.get('index', default=0, type=int)
    return get_event_reading(index, 'updateSocialMedia')  # Make sure this matches exactly

@app.route('/radio-play', methods=['GET'])
def get_radio_play_event():
    index = request.args.get('index', default=0, type=int)
    return get_event_reading(index, 'updateRadioPlay')  # Make sure this matches exactly

@app.route('/track-artist', methods=['GET'])
def get_track_artist_event():
    index = request.args.get('index', default=0, type=int)
    return get_event_reading(index, 'trackArtist')  # Make sure this matches exactly

if __name__ == '__main__':
    app.run(port=8110, host="0.0.0.0")
