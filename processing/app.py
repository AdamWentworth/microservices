from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from base import Base 
from stats import Stats  
import requests
from datetime import datetime, timedelta, timezone
import logging.config
import yaml
import connexion
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

# Load logging and application configurations
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f)

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

CORS(app.app)

# Create SQLAlchemy engine and session
engine = create_engine(f"sqlite:///{app_config['datastore']['filename']}")
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

api_base_url = app_config['eventstore']['url']

def populate_stats():
    logger.info("Start Periodic Processing")
    session = DBSession()

    # Ensure current_datetime is timezone-aware and set to UTC
    current_datetime = datetime.now(timezone.utc)
    prev_stats = session.query(Stats).order_by(Stats.last_updated.desc()).first()

    if prev_stats:
        new_stats = Stats(
            total_artists=prev_stats.total_artists,
            max_followers=prev_stats.max_followers,
            max_spins=prev_stats.max_spins,
            number_of_tracked_artists=prev_stats.number_of_tracked_artists,
            last_updated=current_datetime  # Already in UTC
        )
    else:
        new_stats = Stats(
            total_artists=0,
            max_followers=0,
            max_spins=0,
            number_of_tracked_artists=0,
            last_updated=current_datetime  # Already in UTC
        )

    # Here's where the adjustment is made for datetime formatting
    last_updated_str = (prev_stats.last_updated if prev_stats else current_datetime - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_datetime_str = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    get_artists_url = f"{api_base_url}/artist/timestamp?start_timestamp={last_updated_str}&end_timestamp={current_datetime_str}"
    get_max_followers_url = f"{api_base_url}/social_media/max_followers_by_timestamp?start_timestamp={last_updated_str}&end_timestamp={current_datetime_str}"
    get_max_radio_play_url = f"{api_base_url}/artist/radio-play/timestamp?start_timestamp={last_updated_str}&end_timestamp={current_datetime_str}"
    get_tracked_artists_url = f"{api_base_url}/user/track-artist/timestamp?start_timestamp={last_updated_str}&end_timestamp={current_datetime_str}"

    try:
        # Fetch total number of artists
        logger.info(f"Requesting total number of artists from URL: {get_artists_url}")
        artist_response = requests.get(get_artists_url)
        if artist_response.status_code == 200:
            artists_data = artist_response.json()
            if artists_data:  # Check if the response is not empty
                new_stats.total_artists += len(artists_data)  # Update total artists
                for artist in artists_data:
                    trace_id = artist.get('trace_id', 'N/A')
                    artist_name = artist.get('name', 'Unknown Artist')
                    logger.info(f"Received data for artist '{artist_name}' with trace_id {trace_id}.")

        # Fetch max followers
        logger.info(f"Requesting max followers data from URL: {get_max_followers_url}")
        max_followers_response = requests.get(get_max_followers_url)
        if max_followers_response.status_code == 200:
            max_followers_data = max_followers_response.json()
            if max_followers_data and max_followers_data.get('max_followers') is not None:  # Check if data is meaningful
                new_stats.max_followers = max_followers_data.get('max_followers')
                trace_id = max_followers_data.get('trace_id', 'N/A')
                logger.info(f"Received max followers data: {new_stats.max_followers} with trace_id {trace_id}.")

        # Fetch max radio play
        logger.info(f"Requesting max radio play data from URL: {get_max_radio_play_url}")
        max_radio_play_response = requests.get(get_max_radio_play_url)
        if max_radio_play_response.status_code == 200:
            max_radio_play_data = max_radio_play_response.json()
            if max_radio_play_data and max_radio_play_data.get('max_radio_play') is not None:  # Check if data is meaningful
                new_stats.max_spins = max_radio_play_data.get('max_radio_play')
                trace_id = max_radio_play_data.get('trace_id', 'N/A')
                logger.info(f"Received max radio play data: {new_stats.max_spins} with trace_id {trace_id}.")

        # Fetch tracked artists
        logger.info(f"Requesting tracked artists data from URL: {get_tracked_artists_url}")
        tracked_artists_response = requests.get(get_tracked_artists_url)
        if tracked_artists_response.status_code == 200:
            tracked_artists_data = tracked_artists_response.json()
            if tracked_artists_data:  # Check if the response is not empty
                new_stats.number_of_tracked_artists += len(tracked_artists_data)
                for tracked_artist in tracked_artists_data:
                    trace_id = tracked_artist.get('trace_id', 'N/A')
                    artist_id = tracked_artist.get('artist_id', 'Unknown Artist')
                    logger.debug(f"Processing tracked artist ID: {artist_id}, Trace ID: {trace_id}")
        else:
            logger.warning(f"Failed to fetch tracked artists data. Status code: {tracked_artists_response.status_code}")

        # Commit the updates to the database
        session.add(new_stats)
        session.commit()
        logger.info("Stats updated with new data from storage service.")

    except Exception as e:
        logger.error(f"Error during stats population: {e}")
        session.rollback()
    finally:
        session.close()

    logger.info("Periodic Processing has ended")

def init_scheduler():
    """Initialize the scheduler to run fetch_and_update_stats periodically."""
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()

def get_stats():
    """
    Retrieve and return the latest event statistics from the 'stats' table using SQLAlchemy ORM.
    """
    session = DBSession()

    try:
        # Use SQLAlchemy to order stats entries by last_updated and get the most recent
        stats = session.query(Stats).order_by(Stats.last_updated.desc()).first()
        if stats:
            return {
                "total_artists": stats.total_artists,  
                "max_followers": stats.max_followers,  
                "max_spins": stats.max_spins,      
                "number_of_tracked_artists": stats.number_of_tracked_artists,
                "last_updated": stats.last_updated.strftime("%Y-%m-%dT%H:%M:%SZ") # Format datetime as string if needed
            }, 200
        else:
            # Return a message if no statistics were found
            return {"message": "No statistics found"}, 404
    finally:
        session.close()

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")
