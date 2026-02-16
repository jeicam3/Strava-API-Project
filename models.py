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

    user_id = Column(Integer, ForeignKey('users.user_id'))
    owner = relationship("User", back_populates="activities")

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
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    user_id = Column(Integer, ForeignKey('users.user_id'))
    owner = relationship("User", back_populates="blocks")

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    gender = Column(String)

    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)

    hr_max = Column(Integer, nullable=True, default=None)
    z1_limit = Column(Integer, nullable=True, default=None)
    z2_limit = Column(Integer, nullable=True, default=None)
    z3_limit = Column(Integer, nullable=True, default=None)
    z4_limit = Column(Integer, nullable=True, default=None)

    activities = relationship("Activity", back_populates="owner")
    blocks = relationship("Block", back_populates="owner")

def init_db(db_url="sqlite:///strava_data.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine