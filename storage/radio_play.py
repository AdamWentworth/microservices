from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from base import Base
from datetime import datetime, timezone

class RadioPlay(Base):
    """ Radio Play Data for Artists """
    __tablename__ = 'radio_play'

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_id = Column(String, ForeignKey('artists.id'), nullable=False)
    region = Column(String, nullable=False)
    song_title = Column(String, nullable=False)
    spins = Column(Integer, nullable=False)
    trace_id = Column(String, nullable=True)  
    # Use func.now() for database default UTC datetime, assuming your database is configured for UTC
    date_created = Column(DateTime, nullable=False, default=func.now())

    def __init__(self, artist_id, region, song_title, spins, trace_id=None):
        """ Initializes radio play data for an artist """
        self.artist_id = artist_id
        self.region = region
        self.song_title = song_title
        self.spins = spins
        self.trace_id = trace_id  
        # Set date_created using timezone-aware UTC datetime
        self.date_created = datetime.now(timezone.utc)

    def to_dict(self):
        """ Dictionary Representation of radio play data """
        return {
            'id': self.id,
            'artist_id': self.artist_id,
            'region': self.region,
            'song_title': self.song_title,
            'spins': self.spins,
            'trace_id': self.trace_id,  
            # Ensure the datetime is serialized in a consistent way, e.g., ISO format
            'date_created': self.date_created
        }
