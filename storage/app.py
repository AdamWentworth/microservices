import connexion
import yaml
import json
from connexion import NoContent
from flask import request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_, func
from base import Base
from artists import Artist
from social_media import SocialMedia
from radio_play import RadioPlay
from tracked_artist import TrackedArtist
import logging.config
from datetime import datetime, timezone
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread


import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# Load logging configuration
with open('log_conf.yml', 'r') as log_conf_file:
    log_config = yaml.safe_load(log_conf_file)
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# Load database configuration from app_conf.yml
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f)

# MySQL database connection details from app_conf.yml
db_user = app_config['datastore']['user']
db_password = app_config['datastore']['password']
db_host = app_config['datastore']['hostname']
db_port = app_config['datastore']['port']
db_name = app_config['datastore']['db']

logger.info(f"Connecting to DB. Hostname:{db_host}, Port:{db_port}")

# Initialize SQLAlchemy with MySQL
engine = create_engine(f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
Base.metadata.bind = engine

Session = sessionmaker(bind=engine)

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

def process_messages():
    hostname = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                         reset_offset_on_start=False,
                                         auto_offset_reset=OffsetType.LATEST)

    for msg in consumer:
        if msg is not None:
            msg_str = msg.value.decode('utf-8')
            message = json.loads(msg_str)
            logger.info(f"Message: {message}")
            payload = message["payload"]
            session = Session()

            try:
                if message["type"] == "addArtist":
                    # Ensure list fields are serialized to JSON string
                    payload['top_tracks'] = json.dumps(payload.get('top_tracks', []))
                    payload['certifications'] = json.dumps(payload.get('certifications', []))
                    artist = Artist(**payload)
                    session.add(artist)

                elif message["type"] == "updateSocialMedia":
                    social_media_record = session.query(SocialMedia).filter_by(
                        artist_id=payload['artist_id'], platform=payload['platform']).first()
                    if social_media_record:
                        social_media_record.followers = payload['followers']
                        social_media_record.plays = payload['plays']
                    else:
                        new_social_media = SocialMedia(**payload)
                        session.add(new_social_media)

                elif message["type"] == "updateRadioPlay":
                    radio_play_record = session.query(RadioPlay).filter_by(
                        artist_id=payload['artist_id'], region=payload['region'], song_title=payload['song_title']).first()
                    if radio_play_record:
                        radio_play_record.spins = payload['spins']
                    else:
                        new_radio_play = RadioPlay(**payload)
                        session.add(new_radio_play)

                elif message["type"] == "trackArtist":
                    tracked_artist = TrackedArtist(**payload)
                    session.add(tracked_artist)

                session.commit()
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                session.rollback()
            finally:
                session.close()

            consumer.commit_offsets()

def get_artists_by_timestamp(start_timestamp, end_timestamp):
    logger.info(f"Received request for get_artists_by_timestamp with start_timestamp={start_timestamp} and end_timestamp={end_timestamp}")

    try:
        session = Session()

        logger.info(f"Handling get_artists_by_timestamp request: start_timestamp={start_timestamp}, end_timestamp={end_timestamp}")

        # Parse the timestamps to datetime objects including their timezone information
        start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
        end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")

        # Convert parsed datetime objects to UTC
        start_datetime_utc = start_datetime.astimezone(timezone.utc)
        end_datetime_utc = end_datetime.astimezone(timezone.utc)

        # Use the UTC datetime objects for querying the database
        results = session.query(Artist).filter(
            and_(Artist.date_created >= start_datetime_utc, Artist.date_created < end_datetime_utc)).all()
        
        json_results = []
        for result in results:
            json_results.append(result.to_dict())
        
        logger.info(f"Completed get_artists_by_timestamp request: Returned {len(json_results)} results")
    except Exception as e:
        print(e)
        json_results = []  # Ensure json_results is defined even in case of exception
    finally:
        session.close()  # Ensure the session is closed in a finally block
    return json_results, 200

def get_max_followers_by_timestamp(start_timestamp, end_timestamp):
    logger.info(f"Received request for get_max_followers_by_timestamp with start_timestamp={start_timestamp} and end_timestamp={end_timestamp}")
    session = Session()

    # Parse the input timestamps with timezone information
    start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
    end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")

    # Convert to UTC
    start_datetime_utc = start_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    end_datetime_utc = end_datetime.astimezone(timezone.utc).replace(tzinfo=None)

    logger.debug(f"Parsed and converted to UTC start_datetime={start_datetime_utc}, end_datetime={end_datetime_utc}")

    try:
        max_followers_query = session.query(SocialMedia.trace_id, func.max(SocialMedia.followers)).filter(
            SocialMedia.date_created >= start_datetime_utc,
            SocialMedia.date_created <= end_datetime_utc
        ).group_by(SocialMedia.trace_id).order_by(func.max(SocialMedia.followers).desc())
        logger.debug(f"Executing query for max followers: {str(max_followers_query)}")
        
        max_followers_record = max_followers_query.first()

        if max_followers_record:
            trace_id, max_followers = max_followers_record
            logger.info(f"Max followers found: {max_followers} for trace_id: {trace_id}")
            return {"max_followers": max_followers, "trace_id": trace_id}, 200
        else:
            logger.info("No max followers data found for the given timeframe")
            return {"message": "No data available for the given timeframe"}, 204

    except Exception as e:
        logger.error(f"Exception during query execution: {e}")
        return {"error": str(e)}, 500
    finally:
        session.close()

def get_radio_play_by_timestamp(start_timestamp, end_timestamp):
    logger.info(f"Received request for get_radio_play_by_timestamp with start_timestamp={start_timestamp} and end_timestamp={end_timestamp}")
    session = Session()

    # Parse the input timestamps with timezone information
    start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
    end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")

    # Convert to UTC
    start_datetime_utc = start_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    end_datetime_utc = end_datetime.astimezone(timezone.utc).replace(tzinfo=None)

    logger.debug(f"Parsed and converted to UTC start_datetime={start_datetime_utc}, end_datetime={end_datetime_utc}")

    try:
        max_radio_play_query = session.query(RadioPlay.trace_id, func.max(RadioPlay.spins)).filter(
            RadioPlay.date_created >= start_datetime_utc,
            RadioPlay.date_created <= end_datetime_utc
        ).group_by(RadioPlay.trace_id).order_by(func.max(RadioPlay.spins).desc())
        logger.debug(f"Executing query for max radio plays: {str(max_radio_play_query)}")

        max_radio_play_record = max_radio_play_query.first()

        if max_radio_play_record:
            trace_id, max_radio_play = max_radio_play_record
            logger.info(f"Max radio play found: {max_radio_play} for trace_id: {trace_id}")
            return {"max_radio_play": max_radio_play, "trace_id": trace_id}, 200
        else:
            logger.info("No max radio play data found for the given timeframe")
            return {"message": "No data available for the given timeframe"}, 204

    except Exception as e:
        logger.error(f"Exception during query execution: {e}")
        return {"error": str(e)}, 500
    finally:
        session.close()

def get_tracked_artists_by_timestamp(start_timestamp, end_timestamp):
    logger.info(f"Received request for get_tracked_artists_by_timestamp with start_timestamp={start_timestamp} and end_timestamp={end_timestamp}")

    session = Session()

    # Ensure datetime parsing includes the timezone if your database datetime values also include it
    start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
    end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")

    # If your database stores datetime in UTC or without timezone, convert your datetime objects to match
    # Example: Assuming your database uses UTC and your datetime objects are in a different timezone
    start_datetime_utc = start_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    end_datetime_utc = end_datetime.astimezone(timezone.utc).replace(tzinfo=None)

    logger.debug(f"Parsed and converted start_datetime={start_datetime_utc}, end_datetime={end_datetime_utc}")

    try:
        tracked_artists_query = session.query(TrackedArtist).filter(
            and_(
                TrackedArtist.date_created >= start_datetime_utc, 
                TrackedArtist.date_created < end_datetime_utc
            )
        )
        logger.debug(f"Executing query for tracked artists: {tracked_artists_query}")

        results = tracked_artists_query.all()

        if results:
            json_results = [result.to_dict() for result in results]
            logger.info(f"Completed get_tracked_artists_by_timestamp request: Returned {len(json_results)} results")
            return json_results, 200
        else:
            logger.info("No tracked artists data found for the given timeframe")
            return {"message": "No data available for the given timeframe"}, 204

    except Exception as e:
        logger.error(f"Exception during get_tracked_artists_by_timestamp execution: {e}")
        return {"error": str(e)}, 500
    finally:
        session.close()

def addArtist():
    session = Session()
    artist_details = request.get_json()
    
    if 'top_tracks' in artist_details:
        artist_details['top_tracks'] = json.dumps(artist_details['top_tracks'])
    if 'certifications' in artist_details:
        artist_details['certifications'] = json.dumps(artist_details['certifications'])

    trace_id = artist_details.pop('trace_id', None)
    new_artist = Artist(**artist_details, trace_id=trace_id)
    
    try:
        session.add(new_artist)
        session.commit()
        logger.debug(f"Stored event addArtist request with a trace id of {trace_id}")
        return NoContent, 201
    except Exception as e:
        logger.error(f"Error during commit: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def updateSocialMedia():
    session = Session()
    social_media_details = request.get_json()

    trace_id = social_media_details.pop('trace_id', None)
    new_social_media = SocialMedia(**social_media_details, trace_id=trace_id)
    try:
        session.add(new_social_media)
        session.commit()
        logger.debug(f"Stored event updateSocialMedia request with a trace id of {trace_id}")
        return NoContent, 200
    except Exception as e:
        logger.error(f"Error during commit: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def updateRadioPlay():
    session = Session()
    radio_play_details = request.get_json()

    trace_id = radio_play_details.pop('trace_id', None)
    new_radio_play = RadioPlay(**radio_play_details, trace_id=trace_id)
    try:
        session.add(new_radio_play)
        session.commit()
        logger.debug(f"Stored event updateRadioPlay request with a trace id of {trace_id}")
        return NoContent, 200
    except Exception as e:
        logger.error(f"Error during commit: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def trackArtist():
    session = Session()
    track_artist_details = request.get_json()

    trace_id = track_artist_details.pop('trace_id', None)
    new_tracked_artist = TrackedArtist(**track_artist_details, trace_id=trace_id)
    try:
        session.add(new_tracked_artist)
        session.commit()
        logger.debug(f"Stored event trackArtist request with a trace id of {trace_id}")
        return NoContent, 201
    except Exception as e:
        logger.error(f"Error during commit: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        
if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8090, host="0.0.0.0")
