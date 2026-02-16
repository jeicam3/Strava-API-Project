from sqlalchemy.orm import Session
from models import init_db, Activity, Lap, Block, User
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging
from sqlalchemy import select
from datetime import datetime, time

engine = init_db()

def insert_activity_data(activities, laps_array, user_id):
    session = Session(engine)
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        for activity, laps in zip(activities, laps_array):
            exists = session.query(Activity).filter_by(activity_id=activity['activity_id']).first()
            
            if not exists:
                new_activity = Activity(
                    activity_id=activity['activity_id'],
                    name=activity['name'],
                    distance=activity['distance'],
                    time=activity['time'],
                    time_int=activity['time_int'],
                    type=activity['type'],
                    date=activity['date'],
                    pace = activity['pace'],
                    training_load = activity['training_load']
                )
                user.activities.append(new_activity)
                #session.add(new_activity)

                for i, lap in enumerate(laps, start=1):
                    new_lap = Lap(
                        lap_id = lap['lap_id'],
                        name = lap['name'],
                        distance = lap['distance'],
                        time = lap['time'],
                        time_int = lap['time_int'],
                        lap_idx = i,
                        pace = lap['pace'],
                        avg_hr = lap['avg_hr']
                    )
                    new_activity.laps.append(new_lap)

        session.commit()
        return {'status': 'success', 'message': "Completed", 'count': len(activities)}

    except IntegrityError as e:
        session.rollback()
        logging.error(f"Błąd spójności bazy danych: {e}")
        return {'status': 'error', 'message': "Błąd spójności danych (np. duplikat)"}
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"Błąd SQLAlchemy: {e}")
        return {'status': 'error', 'message': "Wystąpił błąd podczas zapisu do bazy danych"}
    except Exception as e:
        session.rollback()
        logging.error(f"Nieoczekiwany błąd: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()

def delete(activity_id):
    with Session(engine) as session:
        activity = session.query(Activity).filter_by(activity_id=activity_id).first()
        if activity:
            session.delete(activity)
            session.commit()

def rename(activity_id, new_name):
    with Session(engine) as session:
            activity = session.query(Activity).filter_by(activity_id=activity_id).first()
            if activity:
                activity.name = new_name
                session.commit()

def change_session(activity_id):
    with Session(engine) as session:
        activity = session.query(Activity).filter_by(activity_id=activity_id).first()
        if activity:
            activity.Session = not activity.Session
            session.commit()

def get_session(activity_id):
    with Session(engine) as session:
        activity = session.query(Activity).filter_by(activity_id=activity_id).first()
        if activity:
            return activity.Session
        
def add_Block(name, start, end, user_id):

    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d")
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d")
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    session = Session(engine)
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        new_block = Block(
            name=name,
            start_date=start_dt,
            end_date=end_dt
        )
        user.blocks.append(new_block)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Unexpected error: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()

def delete_block(block_id):    
    with Session(engine) as session:
        block = session.query(Block).filter_by(block_id=block_id).first()
        if block:
            session.delete(block)
            session.commit()
            return True
        else: 
            return False
        
def get_period_activities(start, end, ath_id):
    with Session(engine) as session:
        activities = session.query(Activity).filter(Activity.date >= start, Activity.date <= end, Activity.user_id == ath_id)
        return activities
    
def get_block_period(block_id):
    with Session(engine) as session:
        block = session.query(Block).filter_by(block_id=block_id).first()
        if block:
            return block.start_date, block.end_date
        return None, None
    
def get_block_object(block_id: int):
    block_id = int(block_id)
    with Session(engine) as session:
        if block_id > 0:
            block = session.query(Block).filter_by(block_id=block_id).first()
            if block:
                return block
        return None

def insert_user(data):
    session = Session(engine)
    try:
        user = session.query(User).filter(User.user_id == data['athlete_id']).first()
        if user:
            return True
        else:
            user = User(
                user_id=data['athlete_id'],
                name=data['name'],
                gender=data['gender'],
                access_token=data['access_token'],
                refresh_token=data['refresh_token'],
                expires_at=data['expires_at']
            )
            session.add(user)
            session.commit()
            return True
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()

def get_user_activities(ath_id):
    return select(Activity).where(Activity.user_id == ath_id)
    
def get_user_blocks(ath_id):
    return select(Block).where(Block.user_id == ath_id)

def get_access_token(ath_id):
    from strava_services import ensure_access_token
    session = Session(engine)
    try:
        user = session.query(User).filter(User.user_id == ath_id).first()
        if user:

            user_data = {
            'access_token': user.access_token,
            'refresh_token': user.refresh_token,
            'expires_at': user.expires_at
            }
            user_data = ensure_access_token(user_data)

            user.access_token = user_data['access_token']
            user.refresh_token = user_data['refresh_token']
            user.expires_at = user_data['expires_at']

            session.commit()

            return user.access_token
        else:
            return None
    except Exception as e:
        session.rollback()
        logging.error(f"Database error: {e}")
        return None
    finally:
        session.close()