from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql.functions import now
from base import Base
from datetime import datetime, timezone
import json

class Artist(Base):
    """ Artist Profile """

    __tablename__ = 'artists'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    region = Column(String, nullable=False)
    top_tracks = Column(String, nullable=True)
    certifications = Column(String, nullable=True)
    trace_id = Column(String, nullable=True)  
    date_created = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))  # Sets the date/time record is created

    def __init__(self, id, name, genre, region, top_tracks, certifications, trace_id=None):
        """ Initializes an artist profile """
        self.id = id
        self.name = name
        self.genre = genre
        self.region = region
        self.top_tracks = top_tracks
        self.certifications = certifications
        self.trace_id = trace_id  
        self.date_created = datetime.now(timezone.utc)

    def to_dict(self):
        """ Dictionary Representation of an artist profile """
        return {
            'id': self.id,
            'name': self.name,
            'genre': self.genre,
            'region': self.region,
            'top_tracks': json.loads(self.top_tracks) if self.top_tracks else [],
            'certifications': json.loads(self.certifications) if self.certifications else [],
            'trace_id': self.trace_id,
            'date_created': self.date_created
        }
