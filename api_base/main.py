from typing import Dict, List, Union, Optional, Any
from fastapi import FastAPI, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query, Response
from fastapi import Request
from io import BytesIO
from fastapi.params import Depends
from fastapi import HTTPException, status, Depends as fastapiDepends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import qrcode
from pathlib import Path as PathlibPath
from schema import ActivityApprovals, ActivityBase, ActivityHealthReport, ActivityInvitees, AdminUser, ConcernSurvey, FullActivity, InterestSurvey, PermissionGiven, PersonalGoal, ReturnGroupActivityList, UserReturnModel, YouthPermissionSubmission, Activity, ParentGuardian, MedicalInfo, EmergencyContact, Signature
import sqlite3
import os
import json
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta, timezone
import uuid
from contact_engine import ContactEngine
from db_setup import DBSetup
from jose import jwt, JWTError

app = FastAPI()
contact_engine = ContactEngine()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Allow CORS from any origin (use caution in production)
app.add_middleware( 
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "/data/data.sqlite3")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30



# def get_db():
# 	return app.state._db


@app.on_event("startup")
def startup():
    db_path = PathlibPath(DB_PATH)
    # 1. DB_PATH must include a filename
    if not db_path.suffix:
        raise RuntimeError(
            f"Invalid DB_PATH '{db_path}'. "
            "DB_PATH must point to a SQLite file, e.g. '/data/data.sqlite3'."
        )

    # 2. Parent directory must be creatable
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(
            f"Cannot create database directory '{db_path.parent}': {e}"
        ) from e

    # 3. Parent path must be a directory
    if not db_path.parent.is_dir():
        raise RuntimeError(
            f"DB_PATH parent '{db_path.parent}' exists but is not a directory."
        )

    # 4. Try opening SQLite to catch permission/locking issues early
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception as e:
        raise RuntimeError(
            f"SQLite failed to open database at '{DB_PATH}': {e}"
        ) from e

    conn.row_factory = sqlite3.Row

    # Helpful pragmas for reliability/performance on SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    db_setup=DBSetup(conn)
    db_setup.create_tables()
    db_setup.load_admins()
    app.state._db = conn
    conn.close()



@app.on_event("shutdown")
def shutdown():
	db = getattr(app.state, "_db", None)
	if db:
		db.close()


def get_db():
    """
    Per-request SQLite connection.
    Ensures each request gets a fresh connection that is closed after the request.
    """
    db_path = PathlibPath(DB_PATH)

    # Fail loudly if DB_PATH is invalid
    if not db_path.suffix:
        raise RuntimeError(
            f"Invalid DB_PATH '{DB_PATH}'. DB_PATH must point to a SQLite file, e.g. '/data/data.sqlite3'."
        )

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Pragmas (safe to do per connection)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    try:
        yield conn
    finally:
        conn.close()


def require_role(allowed_roles: set[str]):
    """Verifies if the JWT token has the required role necessary to access the given endpoint
    Returns:
        Returns the user info from the token if role check passes
    Args:
        allowed_roles (set[str]): List of roles which are allowed
    """
    def role_checker(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        role = payload.get("role")
        username = payload.get("sub")

        if not role or not username:
            raise HTTPException(status_code=403, detail="Token missing user/role")

        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return payload  # return user info if needed
    return role_checker


def audit_log_event(
    *,
    request: Request,
    actor_username: Optional[str],
    actor_role: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    success: bool = True,
    details: Optional[dict[str, Any]] = None,
    db = Depends(get_db)
) -> None:
    """
    Logs an audit event to the audit_log table.
    Args:
        request (Request): FastAPI request object to extract client info
        actor_username (Optional[str]): Username of the actor performing the action
        actor_role (Optional[str]): Role of the actor
        action (str): Action being performed
        resource_type (Optional[str]): Type of resource being acted upon
        resource_id (Optional[str]): Identifier of the resource
        success (bool): Whether the action was successful
        details (Optional[dict[str, Any]]): Additional details about the event
        db: Database connection
    """
    cursor = db.cursor()

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    cursor.execute(
        """
        INSERT INTO audit_log (
            actor_username, actor_role, action, resource_type, resource_id,
            success, details, client_ip, user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            actor_username,
            actor_role,
            action,
            resource_type,
            resource_id,
            1 if success else 0,
            json.dumps(details or {}),
            client_ip,
            user_agent,
        ),
    )
    db.commit()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Creates a JWT access token.
    Args:
        data (dict): Data to encode in the token
        expires_delta (timedelta | None): Optional expiration time delta
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


#############################################################################################################
### API Endpoints
#############################################################################################################

@app.get("/")
async def read_root(db=Depends(get_db))->dict:
	db.execute("INSERT INTO visits (created_at) VALUES (datetime('now'))")
	db.commit()
	cur = db.execute("SELECT COUNT(*) FROM visits")
	count = cur.fetchone()[0]
	return {"message": "Hello, world!", "visits": count}


@app.get("/health", tags=["health"])
async def health(db=Depends(get_db))->dict:    
    db.execute("SELECT 1")
    return {"status": "ok"}


#####################################
##### User Management Endpoints #####
#####################################
@app.post("/token", tags=["auth"])
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = fastapiDepends(),
    db=Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute(
        'SELECT username, password, role, "group" FROM admin_users WHERE username = ?',
        (form_data.username,),
    )
    user = cursor.fetchone()

    if not user or user["password"] != form_data.password:
        audit_log_event(
            request=request,
            actor_username=form_data.username,
            actor_role=None,
            action="LOGIN",
            resource_type="auth",
            resource_id=form_data.username,
            success=False,
            details={"reason": "bad_credentials"},
        )
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token = create_access_token(
        {"sub": user["username"], "role": user["role"], "org_group": user["org_group"]}
    )

    audit_log_event(
        request=request,
        actor_username=user["username"],
        actor_role=user["role"],
        action="LOGIN",
        resource_type="auth",
        resource_id=user["username"],
        success=True,
        details={},
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/login", tags=["admin-users"], description="Admin user login")
def login(request:Request, username: str, password: str, db=Depends(get_db)):
    cursor = db.cursor()
    if os.getenv("ENV", "test").lower() == "test":
        token_data = {
            "username": username,
            "role": "admin",
            "org_group": "admin"
        }
        access_token = create_access_token(
            {"sub": token_data["username"], "role": token_data["role"], "org_group": token_data["org_group"]}
        )
        return {"message": "Login successful (debug mode)", "access_token": access_token, "token_type": "bearer"}
    
    cursor.execute(
        "SELECT role, org_group, username FROM admin_users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = cursor.fetchone()
    
    if user:
        # Create JWT token with admin's username, role, and group
        token_data = {
            "username": user[2],
            "role": user[0],
            "org_group": user[1]
        }
        access_token = create_access_token(
            {"sub": user["username"], "role": user["role"], "org_group": user["org_group"]}
        )

        audit_log_event(
            request=request,
            actor_username=user["username"],
            actor_role=user["role"],
            action="LOGIN",
            resource_type="auth",
            resource_id=user["username"],
            success=True,
            details={},
        )

        return {"access_token": access_token, "token_type": "bearer"}
    else:
        return {"message": "Invalid credentials"}

def guid():
    """Generate a unique GUID/UUID string"""
    return str(uuid.uuid4())
    
@app.post("/youth", tags=["users"], description="Create a new youth user")
def create_youth_account(username:str, password:str, group:str, db=Depends(get_db))->UserReturnModel:
    cursor = db.cursor()
    user_id = guid()
    cursor.execute(
        "INSERT INTO admin_users (username, password, role, org_group, user_id) VALUES (?, ?, ?, ?, ?)",
        (username, password, "youth", group, user_id)
    )
    db.commit()
    # user_id = cursor.lastrowid
    return UserReturnModel(user_id=user_id)


@app.post("/users", tags=["users"], description="Create a new user")
async def create_user(user_data: YouthPermissionSubmission, db=Depends(get_db)):
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
async def get_user(youth_id: str, db=Depends(get_db))->Union[YouthPermissionSubmission,dict]:
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
            youth_id=youth_id
        )
        return resp
    else:
        return {"message": "User not found."}
	
	
@app.delete("/users/{youth_id}",tags=["users"],description="Delete user by youth ID")
async def delete_user(youth_id: str,db=Depends(get_db)):
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
async def update_user(youth_id: str, user_data: YouthPermissionSubmission, db=Depends(get_db))->Dict[str, str]:
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
    

@app.get("/users-health", tags=["users"], description="Get health information of all users of an activity")
async def get_users_health(request: Request, activity_id: str, user=Depends(require_role({"advisor", "admin", "ecc_admin"})), db=Depends(get_db))->List[MedicalInfo]:
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if not row:
        return []
    youth_ids = json.loads(row[0])
    medical_infos = []
    for youth_id in youth_ids:
        cursor.execute(
            "SELECT medical FROM youth_medical WHERE youth_id = ?", (youth_id,)
        )
        med_row = cursor.fetchone()
        if med_row:
            medical_info = MedicalInfo(**json.loads(med_row[0]))
            medical_infos.append(medical_info)

    # Audit: log count, not the sensitive data itself
    audit_log_event(
        request=request,
        actor_username=user.get("sub"),
        actor_role=user.get("role"),
        action="get_users_health",
        resource_type="activity",
        resource_id=activity_id,
        success=True,
        details={
            "participants_count": len(youth_ids),
            "contacts_returned": len(medical_infos),
        },
    )
    return medical_infos


@app.get("/users-emergency-contacts", tags=["users"], description="Get emergency contacts of all users of an activity")
async def get_users_emergency_contacts(activity_id: str,  user=Depends(require_role({"advisor", "admin", "ecc_admin"})), db=Depends(get_db))->List[EmergencyContact]:
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if not row:
        return []
    youth_ids = json.loads(row[0])
    emergency_contacts = []
    for youth_id in youth_ids:
        cursor.execute(
            "SELECT emergency_contact FROM youth_medical WHERE youth_id = ?", (youth_id,)
        )
        em_row = cursor.fetchone()
        if em_row:
            emergency_info = EmergencyContact(**json.loads(em_row[0]))
            emergency_contacts.append(emergency_info)
    return emergency_contacts


#######################################
######  Interests and Concerns
######################################
@app.post("/interest-survey", tags=["interest-survey"], description="Submit interest survey")
async def submit_interest_survey(data:InterestSurvey,db=Depends(get_db)):
    cursor = db.cursor()
    # verify if user already has interests entered for this year and if so return error
    sql = "SELECT COUNT(*) FROM interest_survey WHERE youth_id = ? AND strftime('%Y', submitted_at) = strftime('%Y', 'now')"
    cursor.execute(sql, (data.youth_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        return {"message": "Interest survey already submitted for this year."}

    sql = """
    INSERT INTO interest_survey (youth_id, interests, "org_group", submitted_at)
    VALUES (?, ?, ?, ?)
    """
    cursor.execute(
        sql,
        (
            data.youth_id,
            json.dumps(data.interests),
            data.org_group,
            datetime.now().isoformat(),
        ),
    )
    db.commit()
    return {"message": "Interest survey submitted successfully."}


@app.post("/interest-survey-reset", tags=["interest-survey"], description="Reset interest survey for youth")
async def reset_interest_survey(youth_id: str,db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM interest_survey WHERE youth_id = ?", (youth_id,)
    )
    db.commit()
    return {"message": "Interest survey reset successfully."}


@app.get("/interest-survey/{group}", tags=["interest-survey"])
async def get_interest_survey(group: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute('SELECT interests FROM interest_survey WHERE "group" = ?', (group,))
    rows = cursor.fetchall()
    return [json.loads(r[0]) for r in rows]


@app.get("/group-concerns/{group}", tags=["interest-survey"])
async def get_concern_survey(group: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute('SELECT concerns FROM concern_survey WHERE "org_group" = ?', (group,))
    rows = cursor.fetchall()
    return [json.loads(r[0]) for r in rows]



@app.post("/group-concerns", tags=["interest-survey"], description="Submit concern survey for a group")
async def submit_concern_survey(data:ConcernSurvey, db=Depends(get_db)):
    cursor = db.cursor()
    sql = """
    INSERT INTO concern_survey (concerns, org_group, submitted_at)
    VALUES (?, ?, ?)
    """
    cursor.execute(
        sql,
        (
            json.dumps(data.concerns),
            data.org_group,
            datetime.now().isoformat(),
        ),
    )
  
    db.commit()
    return {"message": "Concern survey submitted successfully."}


#######################################
##### create activity management endpoints
#######################################
@app.get("/group-participants/{group}", tags=["activities"], description="Get list of participants for a group")
def list_group_participants(group:str, db=Depends(get_db))->list:
    # get list of user ids in the group
    cursor = db.cursor()
    cursor.execute(
        "SELECT youth_id, youth FROM youth_medical WHERE json_extract(youth, '$.org_group') = ?", (group,)
    )
    rows = cursor.fetchall()
    return rows


@app.post("/activities", tags=["activities"], description="Create a new activity")
async def create_activity(activity_data: Activity, db=Depends(get_db)):
    # fill in additional information
    coed = False
    if ("deacon"or "teacher"or"priest") and ("young women") in activity_data.groups:
        coed = True
    is_overnighter = False
    if hasattr(activity_data, 'date_start') and hasattr(activity_data, 'date_end'):
        if activity_data.start_time and activity_data.end_time:
            try:
                start_date = datetime.fromisoformat(activity_data.start_time).date()
                end_date = datetime.fromisoformat(activity_data.end_time).date()
                is_overnighter = start_date != end_date
            except (ValueError, AttributeError):
                pass

    activity_data.is_coed = coed
    activity_data.is_overnight = is_overnighter
    all_users = []
    for group in activity_data.groups:
        participants = list_group_participants(group)
        all_users.extend(participants)
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
            participants_youth_ids, groups, drivers, is_overnight, is_coed, requires_permission) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            activity_id,
            activity_data.name,
            activity_data.description,
            activity_data.start_time,
            activity_data.end_time,
            getattr(activity_data, 'location', None),
            budget_json,
            all_users,
            groups,
            drivers,
            1 if is_overnighter else 0,
            1 if coed else 0,
            1 if activity_data.requires_permission else 0
        )
    )
    db.commit()
    return {"message": "Activity created successfully.", "activity_id": activity_id}


@app.get("/activities/{activity_id}", tags=["activities"], description="Get activity by ID")
async def get_activity(activity_id: str, db=Depends(get_db))->Activity:
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
async def delete_activity(activity_id: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM activities WHERE activity_id = ?", (activity_id,)
    )
    db.commit()
    return {"message": "Activity deleted successfully."}


@app.put("/activities/{activity_id}", tags=["activities"], description="Update activity by ID")
async def update_activity(activity_id: str, activity_data: Activity, db=Depends(get_db)):
    cursor = db.cursor()
    
    # Check if activity exists
    cursor.execute("SELECT activity_id FROM activities WHERE activity_id = ?", (activity_id,))
    if not cursor.fetchone():
        return {"message": "Activity not found."}
    
    # Calculate additional information
    coed = False
    if ("deacon" or "teacher" or "priest") and ("young women") in activity_data.groups:
        coed = True
    is_overnighter = False
    if hasattr(activity_data, 'start_time') and hasattr(activity_data, 'end_time'):
        if activity_data.start_time and activity_data.end_time:
            try:
                start_date = datetime.fromisoformat(activity_data.start_time).date()
                end_date = datetime.fromisoformat(activity_data.end_time).date()
                is_overnighter = start_date != end_date
            except (ValueError, AttributeError):
                pass
    
    # Serialize complex fields as JSON
    budget_json = json.dumps(activity_data.budget) if hasattr(activity_data, 'budget') and activity_data.budget else None
    groups = activity_data.groups if hasattr(activity_data, 'groups') and activity_data.groups else None
    drivers = activity_data.drivers if hasattr(activity_data, 'drivers') and activity_data.drivers else None
    
    # Get all users for updated groups
    all_users = []
    for group in activity_data.groups:
        participants = list_group_participants(group)
        all_users.extend(participants)
    
    # Update the activity
    cursor.execute(
        """UPDATE activities SET 
           activity_name = ?, description = ?, date_start = ?, date_end = ?, location = ?, 
           budget = ?, participants_youth_ids = ?, groups = ?, drivers = ?, 
           is_overnight = ?, is_coed = ?, requires_permission = ?
           WHERE activity_id = ?""",
        (
            activity_data.name,
            activity_data.description,
            activity_data.start_time,
            activity_data.end_time,
            getattr(activity_data, 'location', None),
            budget_json,
            all_users,
            groups,
            drivers,
            1 if is_overnighter else 0,
            1 if coed else 0,
            1 if activity_data.requires_permission else 0,
            activity_id
        )
    )
    db.commit()
    return {"message": "Activity updated successfully."}



@app.get("/participants/{activity_id}", tags=["activities"], description="Get participants for activity by ID")
async def get_activity_participants(activity_id: str, db=Depends(get_db))->List[ActivityInvitees]:
    cursor = db.cursor()
    cursor.execute(
        "SELECT activities.participants_youth_ids, youth.first_name, youth.last_name FROM activities INNER JOIN youth ON activities.participants_youth_ids = youth.youth_id WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if row:
        participants = []
        youth_ids = json.loads(row["participants_youth_ids"])
        for youth_id in youth_ids:
            cursor.execute(
                "SELECT first_name, last_name FROM youth WHERE youth_id = ?", (youth_id,)
            )
            youth_row = cursor.fetchone()
            if youth_row:
                participant = ActivityInvitees(
                    youth_id=youth_id,
                    first_name=youth_row["first_name"],
                    last_name=youth_row["last_name"]
                )
                participants.append(participant)
        return participants
    else:
        return {"message": "Activity not found."}


@app.get("/group-membership/{group}", tags=["activities"], description="Get participants for a group")
async def get_group_membership(group: str, db=Depends(get_db)):
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
async def get_activity_permission_info(activity_id: str, db=Depends(get_db))->ActivityBase:
    cursor = db.cursor()
    cursor.execute(
        "SELECT  activity_name, date_start, date_end, drivers, description, groups, requires_permission, location FROM activities WHERE activity_id = ?", (activity_id,)    
    )    
    row = cursor.fetchone()
    return_data = ActivityBase(**row)
    if row:
        return return_data
    else:
        return {"message": "Activity not found."}


@app.post("/activity-permissions", tags=["activity-permissions"], description="Assign permission to activity")
async def assign_permission_to_activity(permission_data: PermissionGiven, db=Depends(get_db)):
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


@app.get("/activity-groups", tags=["activities"], description="Get all group activities")
def get_activity_groups(db=Depends(get_db),user=Depends(require_role({"advisor", "admin", "ecc_admin", "president"})))->List[ReturnGroupActivityList]:
    group = user.get("org_group")
    cursor = db.cursor()
    cursor.execute(
        "SELECT activity_id, activity_name, date_start, requires_permission FROM activities WHERE groups LIKE ?", (f"%{group}%",)
    )
    rows = cursor.fetchall()
    return [ReturnGroupActivityList(**row) for row in rows]


@app.get("/activity-health-reports/{activity_id}", tags=["activities"], description="Get health reports for activity by ID")
def get_activity_health_reports(activity_id: str, db=Depends(get_db), users=Depends(require_role({"advisor", "admin", "ecc_admin", "president"})))->ActivityHealthReport:
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if not row:
        return {"message": "Activity not found."}
    
    youth_ids = json.loads(row["participants_youth_ids"])
    
    medications = []
    allergies = []
    dietary_restrictions = []
    medical_conditions = []
    special_notes = []
    for youth_id in youth_ids:
        cursor.execute(
            "SELECT medical, allergies, dietary_restrictions, medical_conditions, medications, special_notes FROM youth_medical WHERE youth_id = ?", (youth_id,)
        )
        med_row = cursor.fetchone()
        if med_row:
            medical_info = MedicalInfo(**json.loads(med_row[0]))
            medications.insert(0, medical_info.medications)
            allergies.insert(0, medical_info.allergies)
            dietary_restrictions.insert(0, medical_info.dietary_restrictions)
            medical_conditions.insert(0, medical_info.medical_conditions)
            special_notes.insert(0, medical_info.special_notes)
    
    return ActivityHealthReport(
        medications=medications,
        allergies=allergies,
        dietary_restrictions=dietary_restrictions,
        medical_conditions=medical_conditions,
        special_notes=special_notes
    )


@app.get("/activities-all-parents", tags=["activities"], description="Get all activities with parent details")
def get_all_activities_with_parents(parent_code:str = Query(..., description="Parent permission code"), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups, requires_permission FROM activities WHERE activity_id IN (SELECT activity_id FROM permission_given WHERE permission_code = ?)", (parent_code,)
    )
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        activities.append(ActivityBase(**row))
    return {"activities": activities}


@app.get("/activities-all", tags=["activities"], description="Get all activities")
def get_all_activities(include_past: bool = Query(False, description="Include past activities"), db=Depends(get_db) )->Dict[str, List[ActivityBase]]:
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


@app.get("/activities-pending-approval", tags=["activities"], description="Get all activities pending approval")
def get_activities_pending_approval(db=Depends(get_db))->List[ActivityApprovals]:
    cursor = db.cursor()
    cursor.execute("SELECT activity_id, activity_name, date_start, date_end, bishop_approval INTEGER, bishop_approval_date, stake_approval, stake_approval_date, groups, requires_permission FROM activities WHERE requires_permission == 1 AND (bishop_approval IS NULL OR stake_approval IS NULL) AND start_time >= date('now')")
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        #TODO fetch youth with permission for each activity to set total youth and total permissions
        cursor.execute("SELECT * FROM permission_given WHERE activity_id = ?", (row["activity_id"],)) # TODO change so it combines all youth and those with permission
        act = ActivityApprovals(
            activity_id=row["activity_id"],
            activity_name=row["activity_name"],
            date_start=row["date_start"],
            bishop_approval=bool(row["bishop_approval"]) if row["bishop_approval"] is not None else None,
            bishop_approval_date=row["bishop_approval_date"],
            stake_approval=bool(row["stake_approval"]) if row["stake_approval"] is not None else None,
            stake_approval_date=row["stake_approval_date"],
            groups=row["groups"],
            total_youth=1,
            total_youth_permission=1,
            youth_approvals=[PermissionGiven(**pg_row) for pg_row in cursor.fetchall()]  # TODO show dict of all youth and if have permission
        )
        activities.append(act)
    return activities
        
    


####################################
## Ecclesiastical Activity Endpoints
####################################
@app.post("/admin-users", tags=["admin-users"], description="Create a new admin user")
async def create_admin_user(user =  AdminUser, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE admin_users SET username = ?, password = ?, role = ? WHERE org_group = ?",
        (user.username, user.password, user.role,user.role, user.org_group)
    )
    db.commit()
    return {"message": "Admin user created successfully."}


@app.get("/login", tags=["admin-users"], description="Admin user login")
def login_func(username: str, password: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT role, org_group, username FROM admin_users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = cursor.fetchone()
    
    if user:
        # Create JWT token with admin's username, role, and group
        token_data = {
            "username": user[2],
            "role": user[0],
            "org_group": user[1]
        }
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data["exp"] = expire
        access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"message": "Login successful", "access_token": access_token, "token_type": "bearer"}
    else:
        return {"message": "Invalid credentials"}


@app.post("/login-verify", tags=["admin-users"], description="Verify admin user token")
def verify_login(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"message": "Token is valid", "payload": payload}
    except JWTError:
        return {"message": "Invalid token"}


@app.get("/activity-permission-ecclesiastical", summary="Get activity permission details for Bishop/Stake President")
def get_activity_permission_ecclesiastical(is_bishop: bool = Query(..., description="Is the requester a bishop?"), is_stake_president: bool = Query(..., description="Is the requester a stake president"), db=Depends(get_db))->List[FullActivity]:
# get a list of all activities needing ecclesiastical approval
    cursor = db.cursor()
    where_clause = ""
    if is_bishop:
        where_clause = "bishop_approval IS NULL"
    elif is_stake_president:
        where_clause = "stake_approval IS NULL"
    cursor.execute("SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups, requires_permission FROM activities WHERE requires_permission == 1 AND {where}".format(where=where_clause))
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        activities.append(FullActivity(**row))
    return activities

@app.post(
    "/activity-permission-ecclesiastical/{activity_id}/approve",
    summary="Approve activity permission for Bishop/Stake President",
)
def approve_activity_permission_ecclesiastical(
    activity_id: str = Path(..., description="The ID of the activity"),
    is_bishop: bool = Query(..., description="Is the requester a bishop?"),
    is_stake_president: bool = Query(..., description="Is the requester a stake president?"),
    db=Depends(get_db),
):
    cursor = db.cursor()
    if is_bishop:
        cursor.execute("UPDATE activities SET bishop_approval = 1, bishop_approval_date = datetime('now') WHERE activity_id = ?", (activity_id,))
    elif is_stake_president:
        cursor.execute("UPDATE activities SET stake_approval = 1, stake_approval_date = datetime('now') WHERE activity_id = ?", (activity_id,))
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "Activity approved successfully."}
    else:
        return {"message": "Activity not found."}   

###################
## Activity Helper Functions
##################

@app.get(
    "/sms-activity-permission/{activity_id}",
    summary="Generate SMS content for activity permission",
)
def sms_activity_permission(
    activity_id: str = Path(..., description="The ID of the activity"),
    db=Depends(get_db),
):
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


@app.get(
    "/email-activity-permission/{activity_id}",
    summary="Generate email content for activity permission",
)
def email_activity_permission(
    activity_id: str = Path(..., description="The ID of the activity"),
    db=Depends(get_db),
):
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
def invite(activity_id: str = Query(..., description="The ID of the activity"), db=Depends(get_db)):
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
async def reconcile_activities(data:FullActivity, db=Depends(get_db)):
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
def get_activity_for_reconciliation(activity_id: str, db=Depends(get_db))->FullActivity:
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
def update_activity_for_reconciliation(activity_id: str, data: FullActivity, db=Depends(get_db)):
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

    ##################
    ### Reconcile activity
    ##################

@app.post("/goals", tags=["goals"], description="Set personal goal")
def set_personal_goal(data: PersonalGoal, db=Depends(get_db), user=Depends(require_role("youth"))):
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO personal_goals (youth_id, goal_area, goal_name, goal_description,  target_date, status, progress_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.youth_id,
            data.goal_area,
            data.goal_name,
            data.goal_description,
            data.target_date,
            data.status,
            json.dumps(data.progress_notes) if data.progress_notes else None
        )
    )
    db.commit()
    return {"message": "Personal goal set successfully."}

@app.get("/goals/{youth_id}", tags=["goals"], description="Get personal goals for youth")
def get_personal_goals(youth_id: str, db=Depends(get_db), user=Depends(require_role("youth")))->List[PersonalGoal]:
    cursor = db.cursor()
    cursor.execute(
        "SELECT youth_id, goal_area, goal_name, goal_description, target_date, status, progress_notes, completed FROM personal_goals WHERE youth_id = ? group by goal_area", (youth_id,)
    )
    rows = cursor.fetchall()
    goals = []
    for row in rows:
        progress_notes = json.loads(row["progress_notes"]) if row["progress_notes"] else None
        goal = PersonalGoal(
            youth_id=row["youth_id"],
            goal_area=row["goal_area"],
            goal_name=row["goal_name"],
            goal_description=row["goal_description"],
            target_date=row["target_date"],
            status=row["status"],
            progress_notes=progress_notes,
            completed=bool(row["completed"])
        )
        goals.append(goal)
    return goals


@app.put("/goals/{youth_id}/{goal_name}", tags=["goals"], description="Update personal goal for youth")
def update_personal_goal(youth_id: str, goal_name: str, data: PersonalGoal, db=Depends(get_db), user=Depends(require_role("youth"))):
    cursor = db.cursor()
    cursor.execute(
        """UPDATE personal_goals 
           SET goal_area = ?, goal_description = ?, target_date = ?, status = ?, progress_notes = ?, completed = ?
           WHERE youth_id = ? AND goal_name = ?""",
        (
            data.goal_area,
            data.goal_description,
            data.target_date,
            data.status,
            json.dumps(data.progress_notes) if data.progress_notes else None,
            1 if data.completed else 0,
            youth_id,
            goal_name
        )
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "Personal goal updated successfully."}
    else:
        return {"message": "Personal goal not found."}

# if __name__ == "__main__":
# 	import uvicorn
# 	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)