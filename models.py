from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Boolean, Date
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import create_engine, ForeignKey
Base = declarative_base()

class Activity(Base):
    __tablename__ = 'activities'

    activity_id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String)
    type = Column(String)
    distance = Column(Float)
    time = Column(String)
    time_int = Column(Integer)
    #total_elevation_gain = Column(Float)
    date = Column(DateTime)
    pace = Column(String)
    Session = Column(Boolean, default=False)
    training_load = Column(Integer)
    laps = relationship("Lap", back_populates="activity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Activity(name='{self.name}', type='{self.type}', date='{self.start_date}')>"
    
class Lap(Base):
    __tablename__ = 'laps'

    lap_id = Column(BigInteger, primary_key=True, autoincrement=False)
    activity_id = Column(BigInteger, ForeignKey('activities.activity_id'), nullable=False)
    lap_idx = Column(Integer, nullable=False)
    name = Column(String)
    distance = Column(Float)
    time = Column(String)
    time_int = Column(Integer)
    pace = Column(String)
    avg_hr = Column(Integer)

    activity = relationship("Activity", back_populates="laps")

class Block(Base):
    __tablename__ = 'blocks'

    block_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    start_date = Column(Date)
    end_date = Column(Date)

def init_db(db_url="sqlite:///strava_data.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine