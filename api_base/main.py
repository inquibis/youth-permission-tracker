from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query, Response
from io import BytesIO
import qrcode
from schema import ActivityBase, PermissionGiven, YouthPermissionSubmission, Activity
import sqlite3
import os
import json
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta
import uuid

app = FastAPI()

# Allow CORS from any origin (use caution in production)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

DB_PATH = "data.sqlite3"


def get_db():
	return app.state._db


@app.on_event("startup")
def startup():
	conn = sqlite3.connect(DB_PATH, check_same_thread=False)
	conn.execute(
		"CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT)"
	)
	conn.commit()
	app.state._db = conn


@app.on_event("shutdown")
def shutdown():
	db = getattr(app.state, "_db", None)
	if db:
		db.close()


##################
### API Endpoints
##################

@app.get("/")
async def read_root():
	db = get_db()
	db.execute("INSERT INTO visits (created_at) VALUES (datetime('now'))")
	db.commit()
	cur = db.execute("SELECT COUNT(*) FROM visits")
	count = cur.fetchone()[0]
	return {"message": "Hello, world!", "visits": count}


##### User Management Endpoints #####
@app.post("/users", tags=["users"], description="Create a new user")
async def create_user(user_data: YouthPermissionSubmission):
    db = get_db()
    cursor = db.cursor()
    sql = """
    INSERT INTO youth_medical 
            (youth_id, permission_code, youth, parent_guardian, medical, emergency_contact, signature, signed_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(
		sql,
        (
            f"{user_data.youth.first_name.lower()}_{user_data.youth.last_name.lower()}",
            user_data.permission_code,
            user_data.youth.json(),
            user_data.parent_guardian.json(),
            user_data.medical.json(),
            user_data.emergency_contact.json(),
            user_data.signature.json(),
            user_data.signed_at,
        ),
    )   
    db.commit()
	return {"message": "User created successfully."}


@app.get("/users/{youth_id}",tags=["users"],description="Get user by youth ID")
async def get_user(youth_id: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(     
        "SELECT * FROM youth_medical WHERE youth_id = ?", (youth_id.lower(),)
    )
    row = cursor.fetchone()
    if row:
        return {key: row[key] for key in row.keys()}
    else:
        return {"message": "User not found."}
	
	
@app.delete("/users/{youth_id}",tags=["users"],description="Delete user by youth ID")
async def delete_user(youth_id: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM youth_medical WHERE youth_id = ?", (youth_id.lower(),)
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "User deleted successfully."}
    else:
        return {"message": "User not found."}   

@app.put("/users/{youth_id}", tags=["users"], description="Update user by youth ID")
async def update_user(youth_id: str, user_data: YouthPermissionSubmission):     
    db = get_db()
    cursor = db.cursor()
    sql = """
    UPDATE youth_medical 
    SET permission_code = ?, youth = ?, parent_guardian = ?, medical = ?, emergency_contact = ?, signature = ?, signed_at = ?
    WHERE youth_id = ?
    """
    cursor.execute(
        sql,
        (
            user_data.permission_code,
            user_data.youth.json(),
            user_data.parent_guardian.json(),
            user_data.medical.json(),
            user_data.emergency_contact.json(),
            user_data.signature.json(),
            user_data.signed_at,
            youth_id.lower(),
        ),
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "User updated successfully."}
    else:
        return {"message": "User not found."}
    

    
##### activity management endpoints
@app.post("/activities", tags=["activities"], description="Create a new activity")
async def create_activity(activity_data: Activity):
    db = get_db()
    cursor = db.cursor()

    # create simple activities table to store JSON payloads
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT,
            data JSON,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    # generate an activity identifier and store the payload as JSON
    activity_id = str(uuid.uuid4())
    if hasattr(activity_data, "json"):
        data_json = activity_data.json()
    else:
        data_json = json.dumps(activity_data)

    cursor.execute(
        "INSERT INTO activities (activity_id, data) VALUES (?, ?)",
        (activity_id, data_json),
    )
    db.commit()
    return {"message": "Activity created successfully.", "activity_id": activity_id}


@app.get("/activities/{activity_id}", tags=["activities"], description="Get activity by ID")
async def get_activity(activity_id: str)->Activity:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT data FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"data": row[0]}
    else:
        return {"message": "Activity not found."}


@app.delete("/activities/{activity_id}", tags=["activities"], description="Delete activity by ID")
async def delete_activity(activity_id: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM activities WHERE activity_id = ?", (activity_id,)
    )
    db.commit()
    return {"message": "Activity deleted successfully."}


@app.put("/activities/{activity_id}", tags=["activities"], description="Update activity by ID")
async def update_activity(activity_id: str, activity_data: Activity):
    # Implementation for updating an activity
    return {"message": "Activity updated successfully."}    








@app.get("/activities/permission-info/{activity_id}",tags=["activities"],description="Get permission info for activity by ID")
async def get_activity_permission_info(activity_id: str)->ActivityBase:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT  activity_name, date_start, date_end, drivers, description, groups FROM activities WHERE activity_id = ?", (activity_id,)    
    )    
    row = cursor.fetchone()
    return_data = ActivityBase(**row)
    if row:
        return return_data
    else:
        return {"message": "Activity not found."}


@app.post("/activity-permissions", tags=["activity-permissions"], description="Assign permission to activity")
async def assign_permission_to_activity(permission_data: PermissionGiven):

    db = get_db()
    cursor = db.cursor()
    
    # Create the permission_given table if it doesn't exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_given (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youth_id TEXT,
            activity_id TEXT,
            permission_code TEXT,
            data JSON,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    
    # Get the youth_id from youth_medical table using permission_code
    cursor.execute(
        "SELECT youth_id FROM youth_medical WHERE permission_code = ?",
        (permission_data.permission_code,)
    )
    row = cursor.fetchone()
    
    if not row:
        return {"message": "Permission code not found."}
    
    youth_id = row[0]
    
    # Insert the permission data into permission_given table
    if hasattr(permission_data, "json"):
        data_json = permission_data.json()
    else:
        data_json = json.dumps(permission_data)
    
    cursor.execute(
        "INSERT INTO permission_given (youth_id, activity_id, permission_code, data) VALUES (?, ?, ?, ?)",
        (youth_id, permission_data.activity_id, permission_data.permission_code, data_json)
    )
    db.commit()
    
    return {"message": "Permission to attend activity recorded.", "youth_id": youth_id} 
    







@app.get("/activity-qrcode", summary="Generate QR for the activity")
def generate_qr(acivity_id: str = Query(..., description="The ID of the activity")):
    qr = qrcode.QRCode(box_size=10, border=4)
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    url = f"{base_url}/activity-permission/{acivity_id}"
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


@app.get("/activity-calendar", summary="Generate calendar invite for the activity")
def invite(activity_id: str = Query(..., description="The ID of the activity")):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT  activity_name, date_start, date_end, drivers, description, groups FROM activities WHERE activity_id = ?", (activity_id,)    
    )    
    row = cursor.fetchone()
    if not row:
        return Response(content="Activity not found.", status_code=404)
    activity_data = ActivityBase(**row)
    dt_start = datetime.fromisoformat(activity_data.date_start)
    dt_end = datetime.fromisoformat(activity_data.date_end)

    cal = Calendar()
    cal.add("prodid", "-//Your App//youth-permission//EN")
    cal.add("version", "2.0")

    evt = Event()
    evt.add("uid", str(uuid.uuid4()))
    evt.add("dtstamp", datetime.utcnow())
    evt.add("dtstart", dt_start)
    evt.add("dtend", dt_end)
    evt.add("summary", activity_data.activity_name)
    if activity_data.description:
        evt.add("description", activity_data.description)
    if activity_data.groups:
        evt.add("location", vText(activity_data.groups))
    cal.add_component(evt)
    ics_bytes = cal.to_ical()

    return Response(
        content=ics_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="invite.ics"'},
    )

if __name__ == "__main__":
	import uvicorn
	uvicorn.run("api_base.main:app", host="0.0.0.0", port=8000, reload=True)