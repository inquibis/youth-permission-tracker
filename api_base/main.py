from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query, Response
from io import BytesIO
import qrcode
from schema import ActivityBase, FullActivity, PermissionGiven, YouthPermissionSubmission, Activity, ParentGuardian, MedicalInfo, EmergencyContact, Signature
import sqlite3
import os
import json
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta
import uuid
from contact_engine import ContactEngine

app = FastAPI()
contact_engine = ContactEngine()

# Allow CORS from any origin (use caution in production)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "data.sqlite3")



def get_db():
	return app.state._db


@app.on_event("startup")
def startup():
    # Ensure folder exists if DB_PATH includes a directory (e.g. /data/youth.db)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Helpful pragmas for reliability/performance on SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    # Core tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )

    # Stores the medical release submission payloads (JSON blobs)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS youth_medical (
            youth_id TEXT PRIMARY KEY,
            permission_code TEXT NOT NULL,
            youth TEXT NOT NULL,
            parent_guardian TEXT NOT NULL,
            medical TEXT NOT NULL,
            emergency_contact TEXT NOT NULL,
            signature TEXT NOT NULL,
            signed_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        );
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_youth_medical_permission_code ON youth_medical(permission_code);")

    # Activities table (matches your create_activity insert pattern)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT UNIQUE,
            activity_name TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            budget TEXT,
            total_cost REAL,
            actual_cost REAL,
            participants_youth_ids TEXT,
            groups TEXT,
            drivers TEXT,
            date_start datetime NOT NULL,
            date_end datetime NOT NULL,
            is_overnight INTEGER,
            is_coed INTEGER,
            thoughts TEXT,
            bishop_approval INTEGER,
            bishop_approval_date TEXT,
            stake_approval INTEGER,
            stake_approval_date TEXT,
            created_at TEXT DEFAULT (datetime('now')),

        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_activity_id ON activities(activity_id);")

    # Permission assignments table (matches your /activity-permissions endpoint)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_given (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youth_id TEXT,
            activity_id TEXT,
            permission_code TEXT,
            data JSON,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_activity_id ON permission_given(activity_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_youth_id ON permission_given(youth_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_permission_code ON permission_given(permission_code);")

    # Keep updated_at current on updates (SQLite trigger)
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_youth_medical_updated_at
        AFTER UPDATE ON youth_medical
        FOR EACH ROW
        BEGIN
            UPDATE youth_medical SET updated_at = datetime('now') WHERE youth_id = NEW.youth_id;
        END;
        """
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

@app.get("/health", tags=["health"])
async def health():
    # Basic DB liveness check
    db = get_db()
    db.execute("SELECT 1")
    return {"status": "ok"}


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
            user_data.youth.model_dump_json(),
            user_data.parent_guardian.model_dump_json(),
            user_data.medical.model_dump_json(),
            user_data.emergency_contact.model_dump_json(),
            user_data.signature.model_dump_json(),
            user_data.signed_at,
        ),
    )   
    db.commit()
    return {"message": "User created successfully."}


@app.get("/users/{youth_id}",tags=["users"],description="Get user by youth ID")
async def get_user(youth_id: str)->YouthPermissionSubmission:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(     
        "SELECT * FROM youth_medical WHERE youth_id = ?", (youth_id.lower(),)
    )
    row = cursor.fetchone()
    if row:
        parent_info = ParentGuardian(**json.loads(row["parent_guardian"]))
        medical_info = MedicalInfo(**json.loads(row["medical"]))
        emergency_info = EmergencyContact(**json.loads(row["emergency_contact"]))
        signature_info = Signature(**json.loads(row["signature"]))
        resp = YouthPermissionSubmission(
            permission_code=row["permission_code"],
            youth=json.loads(row["youth"]),
            parent_guardian=parent_info,
            medical=medical_info,
            emergency_contact=emergency_info,
            signature=signature_info,
            signed_at=row["signed_at"],
        )
        return resp
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
async def update_user(youth_id: str, user_data: YouthPermissionSubmission)->dict:     
    db = get_db()
    cursor = db.cursor()
    sql = """
    UPDATE youth_medical 
    SET permission_code = ?, youth = ?, parent_guardian = ?, medical = ?, emergency_contact = ?, signature = ?, signed_at = ?, updated_at = datetime('now')
    WHERE youth_id = ?
    """
    cursor.execute(
        sql,
        (
            user_data.permission_code,
            user_data.youth.model_dump_json(),
            user_data.parent_guardian.model_dump_json(),
            user_data.medical.model_dump_json(),
            user_data.emergency_contact.model_dump_json(),
            user_data.signature.model_dump_json(),
            user_data.signed_at,
            youth_id.lower(),
        ),
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "User updated successfully."}
    else:
        return {"message": "User not found."}
    

    
##### create activity management endpoints
def list_group_participants(group:str)->list:
    # get list of user ids in the group
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT youth_id, youth FROM youth_medical WHERE json_extract(youth, '$.group') = ?", (group,)
    )
    rows = cursor.fetchall()
    return [{"youth_id": row[0], "youth": json.loads(row[1])} for row in rows}]


@app.post("/activities", tags=["activities"], description="Create a new activity")
async def create_activity(activity_data: Activity):
    # fill in additional information
    coed = False
    if ("deacon"or "teacher"or"priest") and ("young women") in activity_data.groups:
        coed = True
    is_overnighter = False
    if hasattr(activity_data, 'date_start') and hasattr(activity_data, 'date_end'):
        if activity_data.date_start and activity_data.date_end:
            try:
                start_date = datetime.fromisoformat(activity_data.date_start).date()
                end_date = datetime.fromisoformat(activity_data.date_end).date()
                is_overnighter = start_date != end_date
            except (ValueError, AttributeError):
                pass

    activity_data.is_coed = coed
    activity_data.is_overnight = is_overnighter
    all_users = []
    for group in activity_data.groups:
        participants = list_group_participants(group)
        all_users.extend(participants)
    db = get_db()
    cursor = db.cursor()

    # generate an activity identifier and store the payload as JSON
    activity_id = str(uuid.uuid4())
    
    # Serialize complex fields as JSON
    budget_json = json.dumps(activity_data.budget) if hasattr(activity_data, 'budget') and activity_data.budget else None
    groups = activity_data.groups if hasattr(activity_data, 'groups') and activity_data.groups else None
    drivers = activity_data.drivers if hasattr(activity_data, 'drivers') and activity_data.drivers else None

    cursor.execute(
        """INSERT INTO activities 
           (activity_id, activity_name, description, date_start, date_end, location, budget, 
            participants_youth_ids, groups, drivers, is_overnight, is_coed) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            activity_id,
            activity_data.activity_name,
            activity_data.description,
            activity_data.date_start,
            activity_data.date_end,
            getattr(activity_data, 'location', None),
            budget_json,
            all_users,
            groups,
            drivers,
            1 if is_overnighter else 0,
            1 if coed else 0
        )
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



@app.get("/participants/{activity_id}", tags=["activities"], description="Get participants for activity by ID")
async def get_activity_participants(activity_id: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"participants": json.loads(row[0])}
    else:
        return {"message": "Activity not found."}


@app.get("/group-membership/{group}", tags=["activities"], description="Get participants for a group")
async def get_group_membership(group: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE groups LIKE ?", (f"%{group}%",)
    )
    rows = cursor.fetchall()
    all_participants = []
    for row in rows:
        all_participants.extend(json.loads(row[0]))
    return {"participants": all_participants}


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
        data_json = permission_data.model_dump_json()
    else:
        data_json = json.dumps(permission_data)
    
    cursor.execute(
        "INSERT INTO permission_given (youth_id, activity_id, permission_code, data) VALUES (?, ?, ?, ?)",
        (youth_id, permission_data.activity_id, permission_data.permission_code, data_json)
    )
    db.commit()
    
    return {"message": "Permission to attend activity recorded.", "youth_id": youth_id} 
    

@app.get("/activities-all", tags=["activities"], description="Get all activities")
def get_all_activities(include_past: bool = Query(False, description="Include past activities")):
    db = get_db()
    cursor = db.cursor()
    if include_past:
        cursor.execute("SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups FROM activities")
    else:
        cursor.execute("SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups FROM activities WHERE date_end >= date('now')")
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        activities.append(ActivityBase(**row))
    return {"activities": activities}


###################
## Activity Helper Functions
##################

@app.get("/sms-activity-permission/{activity_id}", summary="Generate SMS content for activity permission")
def email_activity_permission(activity_id: str = Query(..., description="The ID of the activity")):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT  activity_name, date_start, date_end, drivers, description, groups FROM activities WHERE activity_id = ?", (activity_id,)    
    )    
    row = cursor.fetchone()
    if not row:
        return Response(content="Activity not found.", status_code=404)
    #TODO get list of users and loop through contact
    base_url = os.getenv("BASE_URL", "http://localhost")
    act_url = f"http://{base_url}/activity-permission/{activity_id}"
    activity_data = ActivityBase(**row)
    text_content = f"Permission Request for {activity_data.activity_name} on {activity_data.date_start} {act_url}"
    #TODO send text message
    return {"Mesages Sent": "successful"}


@app.get("/email-activity-permission/{activity_id}", summary="Generate email content for activity permission")
def email_activity_permission(activity_id: str = Query(..., description="The ID of the activity")):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT  activity_name, date_start, date_end, drivers, description, groups FROM activities WHERE activity_id = ?", (activity_id,)    
    )    
    row = cursor.fetchone()
    if not row:
        return Response(content="Activity not found.", status_code=404)
    activity_data = ActivityBase(**row)
    base_url = os.getenv("BASE_URL", "http://localhost")
    act_url = f"http://{base_url}/activity-permission/{activity_id}"
    email_content = f"""
    Subject: Permission Request for {activity_data.activity_name}

    Dear Parent/Guardian,

    We are excited to inform you about an upcoming activity: {activity_data.activity_name}.

    Details of the Activity:
    - Description: {activity_data.description}
    - Date Start: {activity_data.date_start}
    - Date End: {activity_data.date_end}
    - Drivers: {', '.join(activity_data.drivers) if activity_data.drivers else 'N/A'}
    - Groups Involved: {', '.join(activity_data.groups) if activity_data.groups else 'N/A'}

    Please review the details and provide your permission for your child to participate in this activity.
    {act_url}

    Thank you,
    Activity Coordinator
    """
    #TODO get list of users and loop through contact
    #TODO send email
    return {"email_content": email_content}


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


    ##################
    ### Reconcile activity
    ##################
@app.post("/activities/reconcile", tags=["activities"], description="Reconcile activities")
async def reconcile_activities(data:FullActivity):
    db = get_db()
    cursor = db.cursor()

    # Serialize complex fields as JSON
    budget_json = json.dumps(data.budget) if hasattr(data, 'budget') and data.budget else None
    groups = data.groups if hasattr(data, 'groups') and data.groups else None
    drivers = data.drivers if hasattr(data, 'drivers') and data.drivers else None

    cursor.execute(
        """UPDATE activities 
           SET activity_name = ?, description = ?, location = ?, budget = ?, 
               total_cost = ?, actual_cost = ?, participants_youth_ids = ?, 
               groups = ?, drivers = ?, date_start = ?, date_end = ?, 
               is_overnight = ?, is_coed = ?, thoughts = ?, bishop_approval = ?, 
               bishop_approval_date = ?, stake_approval = ?, stake_approval_date = ?
           WHERE activity_id = ?""",
        (
            data.activity_name,
            data.description,
            getattr(data, 'location', None),
            budget_json,
            data.total_cost,
            data.actual_cost,
            data.participants_youth_ids,
            groups,
            drivers,
            data.date_start,
            data.date_end,
            1 if data.is_overnight else 0,
            1 if data.is_coed else 0,
            data.thoughts,
            1 if data.bishop_approval else 0,
            data.bishop_approval_date,
            1 if data.stake_approval else 0,
            data.stake_approval_date,
            data.activity_id
        )
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "Activity reconciled successfully."}
    else:
        return {"message": "Activity not found."}


@app.get("/activities/reconcile/{activity_id}", tags=["activities"], description="Get activity for reconciliation by ID")
def get_activity_for_reconciliation(activity_id: str)->FullActivity:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if not row:
        return Response(content="Activity not found.", status_code=404)
    activity_data = FullActivity(**row)
    return activity_data


@app.put("/activities/reconcile/{activity_id}", tags=["activities"], description="Update activity for reconciliation by ID")
def update_activity_for_reconciliation(activity_id: str, data: FullActivity):
    db = get_db()
    cursor = db.cursor()

    # Serialize complex fields as JSON
    budget_json = json.dumps(data.budget) if hasattr(data, 'budget') and data.budget else None
    groups = data.groups if hasattr(data, 'groups') and data.groups else None
    drivers = data.drivers if hasattr(data, 'drivers') and data.drivers else None

    cursor.execute(
        """UPDATE activities 
           SET activity_name = ?, description = ?, location = ?, budget = ?, 
               total_cost = ?, actual_cost = ?, participants_youth_ids = ?, 
               groups = ?, drivers = ?, date_start = ?, date_end = ?, 
               is_overnight = ?, is_coed = ?, thoughts = ?, bishop_approval = ?, 
               bishop_approval_date = ?, stake_approval = ?, stake_approval_date = ?
           WHERE activity_id = ?""",
        (
            data.activity_name,
            data.description,
            getattr(data, 'location', None),
            budget_json,
            data.total_cost,
            data.actual_cost,
            data.participants_youth_ids,
            groups,
            drivers,
            data.date_start,
            data.date_end,
            1 if data.is_overnight else 0,
            1 if data.is_coed else 0,
            data.thoughts,
            1 if data.bishop_approval else 0,
            data.bishop_approval_date,
            1 if data.stake_approval else 0,
            data.stake_approval_date,
            activity_id
        )
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "Activity reconciled successfully."}
    else:
        return {"message": "Activity not found."}


if __name__ == "__main__":
	import uvicorn
	uvicorn.run("api_base.main:app", host="0.0.0.0", port=8000, reload=True)