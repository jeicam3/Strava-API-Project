from datetime import datetime

def process_laps_data(laps):
    result = []
    for lap in laps:
        lap_id = lap['id']
        name = lap['name']
        time_int = lap['moving_time']
        time = time_toString(time_int)
        pace = calculate_pace(lap['moving_time'], lap['distance'])
        distance = lap['distance']

        result_element= {
            'lap_id': lap_id,
            'name': name,
            'time_int': time_int,
            'time': time,
            'distance': distance,
            'pace': pace
        }
        result.append(result_element)
    return result

def process_activity_data(activity):
    activity_id = activity['id']
    name = activity['name']
    time_int = activity['moving_time']
    time = time_toString(time_int)
    pace = calculate_pace(activity['moving_time'], activity['distance'])
    distance = activity['distance']
    type = activity['type']
    strava_date = activity['start_date']    #strava format
    start_date = datetime.fromisoformat(strava_date)    #database format

    result = {
        'activity_id': activity_id,
        'name': name,
        'time_int': time_int,
        'time': time,
        'distance': distance,
        'pace': pace,
        'type': type,
        'date': start_date
    }
    return result

def time_toString(time):
    hours = time // 3600
    minutes = (time % 3600) // 60
    seconds = time % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def calculate_pace(time, distance):
    if distance > 0:
        dist_km = distance / 1000
        seconds_per_k = time / dist_km
        minutes = int(seconds_per_k) // 60
        seconds = int(seconds_per_k) % 60
        return f"{minutes:02d}:{seconds:02d} min/km"
    else:
        return 0