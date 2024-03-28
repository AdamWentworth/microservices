from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from base import Base
from datetime import datetime, timezone

class TrackedArtist(Base):
    """ Tracked Artist Information """

    __tablename__ = 'tracked_artists'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    artist_id = Column(String, ForeignKey('artists.id'), nullable=False)
    trace_id = Column(String, nullable=True)  
    # Use func.now() for database default UTC datetime, assuming your database is configured for UTC
    date_created = Column(DateTime, nullable=False, default=func.now())

    def __init__(self, user_id, artist_id, trace_id=None):
        """ Initializes tracked artist information """
        self.user_id = user_id
        self.artist_id = artist_id
        self.trace_id = trace_id  
        # Set date_created using timezone-aware UTC datetime
        self.date_created = datetime.now(timezone.utc)

    def to_dict(self):
        """ Dictionary Representation of tracked artist information """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'artist_id': self.artist_id,
            'trace_id': self.trace_id,  
            # Ensure the datetime is serialized in a consistent way, e.g., ISO format
            'date_created': self.date_created
        }
