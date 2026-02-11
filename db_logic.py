from sqlalchemy.orm import Session
from models import init_db, Activity, Lap, Block
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

engine = init_db()

def insert_activity_data(activities, laps_array):
    session = Session(engine)
    try:
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
                    pace = activity['pace']
                )
                session.add(new_activity)

                for i, lap in enumerate(laps, start=1):
                    new_lap = Lap(
                        lap_id = lap['lap_id'],
                        name = lap['name'],
                        distance = lap['distance'],
                        time = lap['time'],
                        time_int = lap['time_int'],
                        lap_idx = i,
                        pace = lap['pace']
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
        
def add_Block(name, start, end):
    session = Session(engine)
    try:
        new_block = Block(
            name=name,
            start_date=start,
            end_date=end
        )
        session.add(new_block)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Nieoczekiwany błąd: {e}")
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
        
def get_period_activities(start, end):
    with Session(engine) as session:
        activities = session.query(Activity).filter(Activity.date >= start, Activity.date <= end)
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