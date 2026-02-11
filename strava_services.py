import os
from dotenv import load_dotenv, set_key
import requests
from services import process_laps_data, process_activity_data
import time
from datetime import datetime

CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
REDIRECT_URI = "http://127.0.0.1:8000/callback"

def update_env_file(data):
    env_path = ".env"

    set_key(env_path, "STRAVA_ACCESS_TOKEN", data.get("access_token"))
    set_key(env_path, "STRAVA_REFRESH_TOKEN", data.get("refresh_token"))
    set_key(env_path, "STRAVA_EXPIRES_AT", str(data.get("expires_at")))

def ensure_access_token():
    load_dotenv(override=True)
    expiration_time = int(os.getenv("STRAVA_EXPIRES_AT"))
    curr_time = int(time.time())
    if curr_time + 60 > expiration_time:
        payload = {
            'client_id': os.getenv("STRAVA_CLIENT_ID"),
            'client_secret': os.getenv("STRAVA_CLIENT_SECRET"),
            'refresh_token': os.getenv("STRAVA_REFRESH_TOKEN"),
            'grant_type': 'refresh_token'
        }
        url = "https://www.strava.com/oauth/token"
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            update_env_file(response.json())
            load_dotenv(override=True)
            return os.getenv("STRAVA_ACCESS_TOKEN")
    else:
        return os.getenv("STRAVA_ACCESS_TOKEN")
    

def authorization():
    #zakres
    scope = "read,activity:read_all"
    
    #URL autoryzacyjny
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    
    return {
        "login_url": auth_url
    }

def callback_func(code):
    #przygotowanie danych
    payload = {
        'client_id': os.getenv("STRAVA_CLIENT_ID"),
        'client_secret': os.getenv("STRAVA_CLIENT_SECRET"),
        'code': code,
        'grant_type': 'authorization_code' #potrzebne dla stravy
    }

    #wysłanie zapytania 
    url = "https://www.strava.com/oauth/token"
    response = requests.post(url, data=payload)
    
    #sprawdzene kodu i wypisanie informacji
    if response.status_code == 200:
        data = response.json()
        update_env_file(data)
        load_dotenv(override=True)
        return {"message": "Jest ok"}
    else:
        return {"error": "Błąd wymiany kodu", "details": response.json()}
    
def get_activities(start_date, end_date):
    access_token = ensure_access_token()
    after = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    before = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
    headers = {
        'authorization': f'Bearer {access_token}'
    }
    params = {
        'after': after,
        'before': before,
        'per_page': 50
    }
    url = "https://www.strava.com/api/v3/athlete/activities"
    response = requests.get(url,params=params, headers=headers)

    if response.status_code == 200:
        activities = response.json()
        activities_array = []
        laps_array = []
        for activity in activities:
            activity_id = activity['id']
            laps_url = f"https://www.strava.com/api/v3/activities/{activity_id}/laps"
            laps_response = requests.get(laps_url, params=params, headers=headers)
            if laps_response.status_code == 200:
                laps = laps_response.json()
                laps_array.append(process_laps_data(laps))
            else:
                return None
            activities_array.append(process_activity_data(activity))
        return activities_array, laps_array
    else:
        return None
