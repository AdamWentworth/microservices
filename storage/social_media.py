from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from base import Base
from datetime import datetime, timezone

class SocialMedia(Base):
    """ Social Media Metrics for Artists """

    __tablename__ = 'social_media'

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_id = Column(String, ForeignKey('artists.id'), nullable=False)
    platform = Column(String, nullable=False)
    followers = Column(Integer, nullable=False)
    plays = Column(Integer, nullable=False)
    trace_id = Column(String, nullable=True)  
    # Use func.now() for database default UTC datetime, assuming your database is configured for UTC
    date_created = Column(DateTime, nullable=False, default=func.now())

    def __init__(self, artist_id, platform, followers, plays, trace_id=None):
        """ Initializes social media metrics for an artist """
        self.artist_id = artist_id
        self.platform = platform
        self.followers = followers
        self.plays = plays
        self.trace_id = trace_id  
        # Set date_created using timezone-aware UTC datetime
        self.date_created = datetime.now(timezone.utc)

    def to_dict(self):
        """ Dictionary Representation of social media metrics """
        return {
            'id': self.id,
            'artist_id': self.artist_id,
            'platform': self.platform,
            'followers': self.followers,
            'plays': self.plays,
            'trace_id': self.trace_id,  
            # Ensure the datetime is serialized in a consistent way, e.g., ISO format
            'date_created': self.date_created
        }
