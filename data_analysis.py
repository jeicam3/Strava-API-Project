import pandas as pd
from models import init_db
from datetime import date, timedelta
from db_logic import get_period_activities
from services import time_toString
import plotly.express as px
import plotly.io as pio

engine = init_db()

def get_activities_data():
    df_activities = pd.read_sql_table('activities', engine)
    return format_distance(df_activities)

def get_laps_data():
    df_laps = pd.read_sql_table('laps', engine)
    return format_distance(df_laps)

def get_blocks_data():
    df_blocks = pd.read_sql_table('blocks', engine)
    return df_blocks

def get_weekly_grid(df_activities):
    df_activities = df_activities.sort_values(by='date', ascending=True)

    df_activities['link'] = df_activities.apply(
        lambda row: f'<a href="/show_details?activity_id={row["activity_id"]}">{row["name"]}</a>', 
        axis=1
    )

    df_activities['week_no'] = df_activities['date'].dt.isocalendar().week
    df_activities['day_name'] = df_activities['date'].dt.day_name()
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_activities['day_name'] = pd.Categorical(df_activities['day_name'], categories=days_order, ordered=True)
    
    grid = df_activities.pivot_table(
        index='week_no', 
        columns='day_name', 
        values='link', 
        aggfunc=lambda x: "".join(x)
    ).fillna('')

    grid.index.name = None
    grid.columns.name = None
    
    return grid.to_html(escape=False, classes="table")

def get_block_table(df_filtered, start_date):
    if df_filtered.empty:
        return "<p class='text-muted'>0 activities in this block.</p>"
    
    df_filtered = df_filtered.sort_values(by='date', ascending=True)
    df_filtered['link'] = df_filtered.apply(
        lambda row: f'<a href="/show_details?activity_id={row["activity_id"]}">{row["name"]}</a>', 
        axis=1
    )
    df_filtered['week_no'] = ((df_filtered['date'] - start_date).dt.days // 7) + 1
    df_filtered['day_name'] = df_filtered['date'].dt.day_name()
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_filtered['day_name'] = pd.Categorical(df_filtered['day_name'], categories=days_order, ordered=True)
    
    grid = df_filtered.pivot_table(
        index='week_no', 
        columns='day_name', 
        values='link', 
        aggfunc=lambda x: "".join(x)
    ).fillna('')

    grid.index.name = None
    grid.columns.name = None
    
    return grid.to_html(escape=False, classes="table table-striped")

def get_calendar_blocks():
    df_activities = get_activities_data()
    df_blocks = get_blocks_data()

    df_activities['date'] = pd.to_datetime(df_activities['date'])
    df_blocks['start_date'] = pd.to_datetime(df_blocks['start_date'])
    df_blocks['end_date'] = pd.to_datetime(df_blocks['end_date'])
    df_blocks = df_blocks.sort_values(by='start_date', ascending=False)
    
    df_unassigned = df_activities.copy()
    results = []
    for _, block in df_blocks.iterrows():
        mask = (df_activities['date'] >= block['start_date']) & (df_activities['date'] <= block['end_date'])
        block_activities = df_activities.loc[mask]
        block_html = get_block_table(block_activities, block['start_date'])
        results.append({
            "name": block['name'],
            "period": f"{block['start_date'].date()} - {block['end_date'].date()}",
            "html": block_html,
            "block_id": block['block_id']
        })
        df_unassigned = df_unassigned[~df_unassigned['activity_id'].isin(block_activities['activity_id'])]
    
    if not df_unassigned.empty:
        df_unassigned.sort_values(by='date', ascending=False)
        others_start = df_unassigned['date'].min()
        others_html = get_block_table(df_unassigned, others_start)
        results.append({
            "name": "Unassigned",
            "period": "---",
            "html": others_html,
            "block_id": -1
        })
    
    return results

def get_activity_details(activity_id):
    query_act = f"SELECT * FROM activities WHERE activity_id = {activity_id}"
    query_laps = f"SELECT * FROM laps WHERE activity_id = {activity_id} ORDER BY lap_idx ASC"

    act_info = pd.read_sql(query_act, engine)
    laps_info = pd.read_sql(query_laps, engine)

    if act_info.empty:
        return "<p>Activity not found</p>"

    act_info = format_distance(act_info)
    laps_info = format_distance(laps_info)

    if act_info['Session'].iloc[0]: laps_info = format_session_laps(laps_info)
    
    act_summary_cols = {
        'name': 'Activity',
        'type': 'Type',
        'distance_km': 'Distance',
        'pace': 'Avg Pace',
        'time': 'Time',
        'date': 'Date'
    }
    laps_summary_cols = {
        'name': 'Lap',
        'distance_km': 'Distance (km)',
        'time': 'Time',
        'pace': 'Avg Pace'
    }
    act_summary = act_info[list(act_summary_cols.keys())].rename(columns=act_summary_cols).T
    laps_summary = laps_info[list(laps_summary_cols.keys())].rename(columns=laps_summary_cols)
    act_html = act_summary.to_html(header=False, classes='table activity-summary',escape=False)

    if not laps_info.empty:
        laps_html = laps_summary.to_html(index=False, classes='table laps-table', escape=False)
    else:
        laps_html = "<p>No laps info</p>"

    return act_html, laps_html

def format_distance(data):
    data['distance_km'] = (data['distance'] / 1000).round(2)
    return data

def quick_upload_dates():
    today = date.today()
    before = today + timedelta(days=1)

    week_bef = today - timedelta(weeks=1) + timedelta(days=1)  
    query = f"SELECT date FROM activities ORDER BY date DESC LIMIT 1"
    latest = pd.read_sql(query, engine)
    if not latest.empty:
        latest = pd.to_datetime(latest['date'].iloc[0]).date()
        after = max(week_bef,latest)
    else:
        after = week_bef
    return after.strftime('%Y-%m-%d'), before.strftime('%Y-%m-%d')

def format_session_laps(laps_data):
    rep = 1
    total_laps = len(laps_data)
    
    for i, row in laps_data.iterrows():
        if row['lap_idx'] == 1:
            laps_data.at[i, 'name'] = "Warm-Up"
        elif row['lap_idx'] == total_laps:
            laps_data.at[i, 'name'] = "Cooldown"
        elif row['lap_idx'] % 2 == 0:
            laps_data.at[i, 'name'] = f'<span class="rep">Rep {rep}</span>'
            laps_data.at[i, 'distance_km'] = f'<span class="rep">{laps_data.at[i, 'distance_km']}</span>'
            laps_data.at[i, 'time'] = f'<span class="rep">{laps_data.at[i, 'time']}</span>'
            laps_data.at[i,'pace'] = f'<span rep="rep">{laps_data.at[i, 'pace']}</span>'
            rep += 1
        else:
            laps_data.at[i, 'name'] = "Rest"
            
    return laps_data

def get_chart_data(start, end, data_type):
    activities_query = get_period_activities(start, end)
    activities = pd.read_sql(activities_query.statement, engine)
    start = pd.to_datetime(start)
    
    if activities.empty:
        return pd.DataFrame(columns=['date', data_type])
    
    activities['date'] = pd.to_datetime(activities['date'])
    if data_type == "distance_km":
        activities = format_distance(activities)
        weekly_data = activities.resample('W', on='date').agg(chart_data=('distance_km', 'sum')).reset_index()
        weekly_data['chart_hover'] = weekly_data['chart_data'].round(2).astype(str) + " km"
    elif data_type == "time":
        weekly_data = activities.resample('W', on='date').agg(chart_data=('time_int', 'sum')).reset_index()
        weekly_data['chart_hover'] = weekly_data['chart_data'].apply(time_toString)
        weekly_data['chart_data'] = weekly_data['chart_data'] / 3600

    weekly_data['week_num'] = ((weekly_data['date'] - start).dt.days // 7) + 1
    weekly_data['week_label'] = "Week " + weekly_data['week_num'].astype(str)

    return weekly_data

def generate_period_chart(start, end, data_type):
    df_weekly = get_chart_data(start, end, data_type)
    if df_weekly.empty:
        return "<p class='text-muted text-center'>No data to display chart</p>"
    
    if data_type == "time":
        y_label = 'Time (h)'
        chart_title = "(Time)"
        hover_label = "Time"
    elif data_type == "distance_km":
        y_label = 'Distance (km)'
        chart_title = "(Distance)"
        hover_label = "Distance"

    y_max = df_weekly['chart_data'].max() * 1.2
    y_min = df_weekly['chart_data'].min() * 0.8

    fig = px.area(
        df_weekly, 
        x='week_label', 
        y='chart_data',
        title=f'Weekly Training Volume {chart_title}',
        labels={'chart_data': y_label, 'week_label': 'Week'},
        template='plotly_white',
        markers=True,
        range_y=[y_min, y_max]
    )

    fig.update_traces(
        customdata=df_weekly['chart_hover'],
        line_color='#fc4c02',
        line_width=3,
        marker=dict(size=8, color='#e34402', symbol='circle'),
        hovertemplate='<b>%{x}</b><br>' + hover_label + ': %{customdata}<extra></extra>'
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        height=350,
        hovermode="x unified"
    )
    chart_html = pio.to_html(fig, full_html=False, include_plotlyjs='False', config={'responsive': True})
    
    return chart_html