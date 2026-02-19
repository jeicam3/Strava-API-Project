import os
import time
from dotenv import load_dotenv, set_key
import requests
from services import process_laps_data, process_activity_data
from datetime import datetime
from db_logic import insert_user
from fastapi import Response, responses
import requests

load_dotenv()

CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
REDIRECT_URI = "http://127.0.0.1:8000/callback"
    
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
    
    return auth_url

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
        data = response.json()
        athlete = data['athlete']
        db_data= {
            'athlete_id': athlete['id'],
            'name': f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(),
            'gender': athlete['sex'],
            'access_token': data['access_token'],
            'refresh_token': data['refresh_token'],
            'expires_at': data['expires_at']
        }
        #update_env_file(data)
        #load_dotenv(override=True)
        if insert_user(db_data):
            response = responses.RedirectResponse(url="/calendar", status_code=303)
        
            response.set_cookie(
                key="athlete_id", 
                value=str(athlete['id']), 
                httponly=True, 
                max_age=2592000
            )
            return response
        else:
            return {'error': 'Database insert error'}
    else:
        return {"error": "Code exchange error", "details": response.json()}
    
def get_activities(start_date, end_date, access_token, ath_id):
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
            streams = get_streams(activity_id, access_token)
            if laps_response.status_code == 200:
                laps = laps_response.json()
                laps_array.append(process_laps_data(laps, streams))
            else:
                continue
            activities_array.append(process_activity_data(activity, streams, ath_id))
        return activities_array, laps_array
    else:
        return None
    
def get_streams(activity_id, access_token):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'keys': 'heartrate,time,distance', 'key_by_type': 'true'}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Błąd pobierania streams: {response.status_code} - {response.text}")
        return {'hr_data': [], 'time_data': [], 'dist_data': []}
    data = response.json()

    # Używamy .get(), aby uniknąć błędu, jeśli tętno nie było rejestrowane
    streams = {
        'hr_data': data.get('heartrate', {}).get('data', []),
        'time_data': data.get('time', {}).get('data', []),
        'dist_data': data.get('distance', {}).get('data', [])
    }
    
    return streams

def get_athlete_data(access_token):
    url = "https://www.strava.com/api/v3/athlete"
    headers = {'Authorization': f'Bearer {access_token}'}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        athlete = response.json()
        return {
            'athlete_id': athlete['id'],
            'name': athlete['username'],
            'gender': athlete['sex']
        }
    else: return None

def ensure_access_token(user_data):
    curr_time = int(time.time())

    if user_data['expires_at'] < curr_time + 60:
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'refresh_token': user_data['refresh_token'],
            'grant_type': 'refresh_token'
        }

        response = requests.post("https://www.strava.com/oauth/token", data=payload)

        if response.status_code == 200:
            response = response.json()

            user_data['access_token'] = response['access_token']
            user_data['refresh_token'] = response['refresh_token']
            user_data['expires_at'] = response['expires_at']

            return user_data
        
        else:
            return None
    else:
        return user_data
