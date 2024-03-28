from sqlalchemy import Column, Integer, String, DateTime
from base import Base

class Stats(Base):
    """ Artist Statistics """
    __tablename__ = "stats"
    
    id = Column(Integer, primary_key=True)
    total_artists = Column(Integer, nullable=False)
    max_followers = Column(Integer, nullable=False)
    max_spins = Column(Integer, nullable=False)
    number_of_tracked_artists = Column(Integer, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    
    def __init__(self, total_artists, max_followers, max_spins, number_of_tracked_artists, last_updated):
        """ Initializes an artist statistics object """
        self.total_artists = total_artists
        self.max_followers = max_followers
        self.max_spins = max_spins
        self.number_of_tracked_artists = number_of_tracked_artists
        self.last_updated = last_updated
        
    def to_dict(self):
        """ Dictionary Representation of artist statistics """
        return {
            'total_artists': self.total_artists,
            'max_followers': self.max_followers,
            'max_spins': self.max_spins,
            'number_of_tracked_artists': self.number_of_tracked_artists,
            'last_updated': self.last_updated.strftime("%Y-%m-%dT%H:%M:%S")
        }
