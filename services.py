from datetime import datetime
import math
import pandas as pd

def process_laps_data(laps, streams):
    result = []
    lap_begin_distance = 0
    lap_end_distance = 0
    for lap in laps:
        lap_id = lap['id']
        name = lap['name']
        time_int = lap['moving_time']
        time = time_toString(time_int)
        pace = calculate_pace(lap['moving_time'], lap['distance'])
        distance = lap['distance']
        lap_end_distance += distance
        avg_hr = calculate_lap_avg_hr(streams, lap_begin_distance, lap_end_distance)
        lap_begin_distance += distance

        result_element= {
            'lap_id': lap_id,
            'name': name,
            'time_int': time_int,
            'time': time,
            'distance': distance,
            'pace': pace,
            'avg_hr': avg_hr
        }
        result.append(result_element)
    return result

def process_activity_data(activity, streams):
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
        'date': start_date,
        'training_load': calculate_TL(streams)
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
    
def calculate_TL(streams):
    tl = 0
    hr_rest = 60
    hr_max = 205
    for i in range(1, len(streams['hr_data'])):
        delta_t = (streams['time_data'][i] - streams['time_data'][i-1]) / 60 #here we need delta time in minutes
        curr_hr = streams['hr_data'][i]

        hr_ratio = (curr_hr - hr_rest) / (hr_max - hr_rest)
        if hr_ratio > 0:
            impulse = delta_t * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)
            tl += impulse
    return int(tl)

def calculate_lap_avg_hr(streams, begin, end):
    #df = pd.DataFrame(streams)

    streams = convert_streams(streams)

    data_dict = {}
    for s in streams:
        data_dict[s['type']] = s['data']

    df = pd.DataFrame({k: pd.Series(v) for k, v in data_dict.items()})

    if df['hr_data'].empty:
        return 0
    lap_data = df[(df['dist_data'] >= begin) & (df['dist_data'] <= end)]
    if lap_data.empty:
        return 0
    avg = lap_data['hr_data'].mean()
    if pd.isna(avg):
        return 0
    
    return int(avg)

def convert_streams(streams):
    return [{'type': 'dist_data', 'data': streams['dist_data']}, {'type': 'hr_data', 'data': streams['hr_data']}]