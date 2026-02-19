from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi import Form
from fastapi import Request
import strava_services as s
from datetime import datetime
from db_logic import insert_activity_data, delete, rename, change_session, get_session, add_Block, delete_block, get_block_period, get_block_object, get_access_token, get_user_data, update_HRzones
from data_analysis import get_calendar_blocks, get_activity_details, quick_upload_dates, generate_period_chart

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Strava Analytics App")

@app.get("/")
async def root(request: Request):
    ath_id = request.cookies.get("athlete_id")
    if ath_id:
        return RedirectResponse(url="/calendar", status_code=303)
    
    return RedirectResponse(url="/login", status_code=303)
    #return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/login")
async def login(request: Request):
    auth_url = s.authorization()
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback(code: str):
    return s.callback_func(code)

@app.get("/upload_activities")
def upload_actvities(request: Request, start_date, end_date):
    ath_id = request.cookies.get("athlete_id")
    if not ath_id:
        return RedirectResponse(url="/login")
    token = get_access_token(int(ath_id))
    result = s.get_activities(start_date, end_date, token, request.cookies.get("athlete_id"))

    if result == None:
        return templates.TemplateResponse(
            request=request, 
            name="message.html", 
            context={"status": "error", "message": "No activities were uploaded"}
        )

    activities_data, laps_data = result
    if activities_data != None:
        result = insert_activity_data(activities_data, laps_data, int(request.cookies.get("athlete_id")))
        if result['status'] == 'success':
            return templates.TemplateResponse(
            request=request, 
            name="message.html", 
            context={"status": "success", "message": f"Successfully update {result['count']} activities."}
        )
        else:
            return templates.TemplateResponse(
            request=request, 
            name="message.html", 
            context={"status": "error", "message": "Failed to upload activities due to a database error."}
        )
    else:
        return templates.TemplateResponse(
            request=request, 
            name="message.html", 
            context={"status": "error", "message": "Failed to upload activities due to a request error."}
        )

@app.get("/calendar", response_class=HTMLResponse)
def calendar(request: Request):
    blocks_tables = get_calendar_blocks(request.cookies.get("athlete_id"))
    return templates.TemplateResponse(
        request=request, 
        name="calendar.html",
        context={"blocks": blocks_tables}
    )

@app.get("/show_details", response_class=HTMLResponse)
def get_details(request: Request, activity_id: int):
    act_html, laps_html =  get_activity_details(activity_id)

    if act_html is None:
        return templates.TemplateResponse(
            request=request, 
            name="message.html", 
            context={"status": "danger", "message": "Activity not found."}
        )
    return templates.TemplateResponse(
        request=request,
        name="details.html",
        context={
            "act_html": act_html,
            "laps_html": laps_html,
            "activity_id": activity_id,
            "session": get_session(activity_id)
        }
    )

@app.get("/upload_latest", response_class=HTMLResponse)
def upload_latest(request: Request):
    after, before = quick_upload_dates()
    return upload_actvities(request, after, before)

@app.get("/manual_upload", response_class=HTMLResponse)
def show_sync_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload_form.html",
        context={}
    )

@app.get("/delete_activity/{activity_id}", response_class=HTMLResponse)
def delete_activity(request: Request, activity_id: int):
    try:
        delete(activity_id)
        return RedirectResponse(url="/calendar", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": f"An error occured: {str(e)}"}
        )
    
@app.post("/rename_activity/{activity_id}", response_class=HTMLResponse)
def rename_act(request: Request, activity_id: int, new_name: str = Form(...)):
    try:
        rename(activity_id, new_name)
        return RedirectResponse(url=f"/show_details?activity_id={activity_id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": f"An error occured: {str(e)}"}
        )
    
@app.get("/set_session/{activity_id}", response_class=HTMLResponse)
def set_session(request: Request, activity_id: int):
    try:
        change_session(activity_id)
        return RedirectResponse(url=f"/show_details?activity_id={activity_id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": f"An error occured: {str(e)}"}
        )
    
@app.post("/add_block", response_class=HTMLResponse)
def add_tblock(request: Request, name: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        result = add_Block(name, start_dt, end_dt, request.cookies.get("athlete_id"))
        return RedirectResponse(url="/calendar", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": f"An error occured: {str(e)}"}
        )
    
@app.get("/delete_block/{block_id}", response_class=HTMLResponse)
def delete_tblock(request: Request, block_id: int):
    try:
        if delete_block(block_id):
            return RedirectResponse(url="/calendar", status_code=303)
        else:
            return templates.TemplateResponse(
                request=request,
                name="message.html",
                context={"status": "danger", "message": f"Cannot delete this block"}
            )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": f"An error occured: {str(e)}"}
        )
    
@app.get("/block_details/{block_id}/{data_type}", response_class=HTMLResponse)
def show_block_summary(request: Request, block_id, data_type):
    start, end = get_block_period(block_id)
    block = get_block_object(block_id)
    chart = generate_period_chart(start, end, data_type, request.cookies.get("athlete_id"))
    if block != None:
        return templates.TemplateResponse(
            request=request,
            name="block.html",
            context={"chart": chart, "block": block}
        )
    else:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": "Cannot show details for this block"}
        )
    
@app.get('/get_chart/{block_id}', response_class=HTMLResponse)
async def get_chart_only(request: Request, block_id: int, type: str = 'distance_km'):
    block = get_block_object(block_id)
    
    if not block:
        return "<p>Block not found</p>"
    chart_html = generate_period_chart(block.start_date, block.end_date, type, request.cookies.get("athlete_id"))
    
    return chart_html

@app.get('/settings', response_class=HTMLResponse)
def show_settings_view(request: Request):
    acc_data = get_user_data(request.cookies.get("athlete_id"))

    if acc_data:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={"user": acc_data}
        )
    else:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": "Unable to show settings screen due to an error"}
        )
    
@app.get('/settings/view', response_class=HTMLResponse)
def get_hr_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/HRzones_view.html",
        context={'user': get_user_data(request.cookies.get("athlete_id"))}
    )

@app.get('/settings/edit', response_class=HTMLResponse)
def get_hr_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/HRzones_form.html",
        context={'user': get_user_data(request.cookies.get("athlete_id"))}
    )

@app.post('/settings/update', response_class=HTMLResponse)
def update_zones(
        request: Request,
        hr_max: int = Form(...), 
        z1_limit: int = Form(...),
        z2_limit: int = Form(...),
        z3_limit: int = Form(...),
        z4_limit: int = Form(...)
):
    
    update_data = {
        'hr_max': hr_max,
        'z1': z1_limit,
        'z2': z2_limit,
        'z3': z3_limit,
        'z4': z4_limit
    }

    if(update_HRzones(request.cookies.get("athlete_id"), update_data)):
        return templates.TemplateResponse(
            request=request,
            name="partials/HRzones_view.html",
            context={'user': get_user_data(request.cookies.get("athlete_id"))}
        )
    else:
        return templates.TemplateResponse(
            request=request,
            name="message.html",
            context={"status": "danger", "message": "Unable to apply changes due to an error"}
        )