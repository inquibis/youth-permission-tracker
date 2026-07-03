from typing import Dict, List, Union, Optional, Any
from fastapi import FastAPI, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query, Response
from fastapi.responses import JSONResponse
from fastapi import Request
from io import BytesIO
from fastapi.params import Depends
from fastapi import HTTPException, status, Depends as fastapiDepends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import qrcode
from pathlib import Path as PathlibPath
from schema import ActivityApprovals, ActivityBase, ActivityHealthReport, ActivityInvitees, AdminUser, ConcernSurvey, FullActivity, InterestSurvey, UserActivityInterests, ResetInterestSurveyRequest, PermissionGiven, PersonalGoal, ReturnGroupActivityList, UserReturnModel, YouthPermissionSubmission, YouthCreationRequest, LoginRequest, Activity, ParentGuardian, MedicalInfo, EmergencyContact, Signature, AdminSQLQuery, AdminQueryResult
import sqlite3
import os
import json
import time
import re
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta, timezone
import uuid
from contact_engine import ContactEngine
from jose import jwt, JWTError
from passlib.context import CryptContext
from db import DatabaseEngine

app = FastAPI()
contact_engine = ContactEngine()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Allow CORS from web frontend origins
# MUST be added before other middleware that might modify responses
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://brookhurst.centervillenorthstake.com",
		"https://brookhurst.centervillenorthstake.com",
		"http://bh.centervillenorthstake.com",
		"https://bh.centervillenorthstake.com",
		"http://api-youth.centervillenorthstake.com",
		"https://api-youth.centervillenorthstake.com",
		"http://localhost:80",
		"http://localhost:3000",
        "http://localhost:8000",
		"http://localhost:443",
		"https://localhost",
	],
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
	allow_headers=["*"],
	expose_headers=["*"],
	max_age=3600,
)

DB_PATH = os.getenv("DB_PATH", "/data/data.sqlite3")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DB = DatabaseEngine(DB_PATH)


# Middleware to log all requests for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
	print(f"[REQUEST] {request.method} {request.url.path}")
	print(f"[ORIGIN] {request.headers.get('origin', 'NO ORIGIN HEADER')}")
	print(f"[HOST] {request.headers.get('host', 'NO HOST HEADER')}")
	response = await call_next(request)
	print(f"[RESPONSE] {response.status_code}")
	return response


# Global exception handler to ensure CORS headers on error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	"""Handle HTTP exceptions with proper CORS headers"""
	return JSONResponse(
		status_code=exc.status_code,
		content={"detail": exc.detail},
		headers={
			"Access-Control-Allow-Origin": request.headers.get("origin", "*"),
			"Access-Control-Allow-Credentials": "true",
		}
	)

# def get_db():
# 	return app.state._db


@app.on_event("startup")
def startup():
    DB.startup(app)



@app.on_event("shutdown")
def shutdown():
	# Connection is closed per-request in get_db()
	pass


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

        if role != "all":
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
    db,  # Database connection (passed explicitly, not through Depends)
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    success: bool = True,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Logs an audit event to the audit_log table.
    Args:
        request (Request): FastAPI request object to extract client info
        actor_username (Optional[str]): Username of the actor performing the action
        actor_role (Optional[str]): Role of the actor
        action (str): Action being performed
        db: Database connection (passed explicitly)
        resource_type (Optional[str]): Type of resource being acted upon
        resource_id (Optional[str]): Identifier of the resource
        success (bool): Whether the action was successful
        details (Optional[dict[str, Any]]): Additional details about the event
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

@app.get("/", description="Root endpoint", summary="Get API root and visit count")
async def read_root(db=Depends(DB.get_db))->dict:
	db.execute("INSERT INTO visits (created_at) VALUES (datetime('now'))")
	db.commit()
	cur = db.execute("SELECT COUNT(*) FROM visits")
	count = cur.fetchone()[0]
	return {"message": "Hello, world!", "visits": count}


@app.get("/health", tags=["health"], description="Health check endpoint", summary="Check API health status")
async def health(db=Depends(DB.get_db))->dict:
    db.execute("SELECT 1")
    return {"status": "ok"}


#####################################
##### User Management Endpoints #####
#####################################
@app.post("/token", tags=["auth"], description="Authenticate admin user and get JWT token", summary="Login for access token")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = fastapiDepends(),
    db=Depends(DB.get_db),
):
    cursor = db.cursor()
    cursor.execute(
        'SELECT username, password, role, org_group FROM admin_users WHERE username = ?',
        (form_data.username,),
    )
    user_row = cursor.fetchone()

    if not user_row:
        audit_log_event(
            request=request,
            actor_username=form_data.username,
            actor_role=None,
            action="LOGIN",
            resource_type="auth",
            resource_id=form_data.username,
            success=False,
            details={"reason": "user_not_found"},
            db=db,
        )
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    
    username, stored_password, role, org_group = user_row[0], user_row[1], user_row[2], user_row[3]
    
    try:
        password_valid = pwd_context.verify(form_data.password, stored_password)
    except ValueError:
        password_valid = False

    if not password_valid:
        audit_log_event(
            request=request,
            actor_username=form_data.username,
            actor_role=None,
            action="LOGIN",
            resource_type="auth",
            resource_id=form_data.username,
            success=False,
            details={"reason": "bad_credentials"},
            db=db,
        )
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token = create_access_token(
        {"sub": username, "role": role, "org_group": org_group}
    )

    audit_log_event(
        request=request,
        actor_username=username,
        actor_role=role,
        action="LOGIN",
        resource_type="auth",
        resource_id=username,
        success=True,
        details={},
        db=db,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login", tags=["admin-users","auth"], description="Admin user login", summary="Authenticate admin user")
def login(request:Request, data: LoginRequest, db=Depends(DB.get_db)):
    cursor = db.cursor()
    
    cursor.execute(
        "SELECT username, role, org_group FROM admin_users WHERE username = ?",
        (data.username,)
    )
    user_row = cursor.fetchone()
    
    if not user_row:
        # User not found
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid username or password"}
        )
    
    username, role, org_group = user_row[0], user_row[1], user_row[2]
    
    # For testing purposes, accept any password for test_admin user
    # In production, implement proper password hashing comparison
    if data.username == "test_admin" and data.password == "password123":
        access_token = create_access_token(
            {"sub": username, "role": role, "org_group": org_group}
        )
        
        audit_log_event(
            request=request,
            actor_username=username,
            actor_role=role,
            action="LOGIN",
            resource_type="auth",
            resource_id=username,
            success=True,
            details={},
            db=db,
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        # Invalid password
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid username or password"}
        )


def guid():
    """Generate a unique GUID/UUID string"""
    return str(uuid.uuid4())
    

@app.post("/youth", tags=["users"], description="Create a new youth user",summary="Create youth user account.  Happens via parent medical form creation")
def create_youth_account(youth_data: YouthCreationRequest, db=Depends(DB.get_db))->UserReturnModel:
    """
    Create a new youth user account.
    Generates username from first_name_last_name and stores in admin_users table.
    """
    try:
        cursor = db.cursor()
        user_id = guid()
        # Generate username from first and last name (lowercase, with underscore)
        username = f"{youth_data.first_name.lower()}_{youth_data.last_name.lower()}"
        # Use first name as default password (in production, consider generating a random one)
        password = youth_data.first_name
        
        # Check if username already exists
        cursor.execute("SELECT user_id FROM admin_users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"Youth user '{username}' already exists. Please use different first/last name or contact admin."
            )
        
        cursor.execute(
            "INSERT INTO admin_users (username, password, role, org_group, user_id) VALUES (?, ?, ?, ?, ?)",
            (username, password, "youth", youth_data.group, user_id)
        )
        db.commit()
        return UserReturnModel(user_id=user_id)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except sqlite3.IntegrityError as e:
        print(f"Database integrity error: {str(e)}")
        raise HTTPException(status_code=409, detail=f"User already exists or duplicate constraint: {str(e)}")
    except sqlite3.OperationalError as e:
        print(f"Database operational error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Database temporarily unavailable: {str(e)}")
    except Exception as e:
        print(f"Unexpected error creating youth account: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create youth account: {str(e)}")


@app.post("/users", tags=["users"], description="Create a new user", summary="Create new user with medical info")
async def create_user(user_data: YouthPermissionSubmission, db=Depends(DB.get_db)):
    try:
        cursor = db.cursor()
        sql = """
        INSERT INTO youth_medical 
                (youth_id, permission_code, youth, parent_guardian, medical, emergency_contact, signature, signed_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
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
    except HTTPException:
        raise
    except sqlite3.IntegrityError as e:
        print(f"Database integrity error: {str(e)}")
        raise HTTPException(status_code=409, detail=f"User already exists: {str(e)}")
    except sqlite3.OperationalError as e:
        print(f"Database operational error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Database temporarily unavailable: {str(e)}")
    except Exception as e:
        print(f"Unexpected error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@app.get("/users/{youth_id}",tags=["users"],description="Get user by youth ID", summary="Retrieve user information")
async def get_user(youth_id: str, db=Depends(DB.get_db))->Union[YouthPermissionSubmission,dict]:
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
	
	
@app.delete("/users/{youth_id}",tags=["users"],description="Delete user by youth ID", summary="Delete user account")
async def delete_user(youth_id: str,db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM youth_medical WHERE youth_id = ?", (youth_id.lower(),)
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "User deleted successfully."}
    else:
        return {"message": "User not found."}


@app.put("/users/{youth_id}", tags=["users"], description="Update user by youth ID", summary="Update user information")
async def update_user(youth_id: str, user_data: YouthPermissionSubmission, db=Depends(DB.get_db))->Dict[str, str]:
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
    

@app.get("/users-health", tags=["users"], description="Get health information of all users of an activity", summary="Retrieve health information for activity participants")
async def get_users_health(request: Request, activity_id: str, user=Depends(require_role({"advisor", "admin", "ecc_admin"})), db=Depends(DB.get_db))->List[MedicalInfo]:
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
        db=db,
    )
    return medical_infos


@app.get("/users-emergency-contacts", tags=["users"], description="Get emergency contacts of all users of an activity", summary="Retrieve emergency contacts for activity participants")
async def get_users_emergency_contacts(activity_id: str,  user=Depends(require_role({"advisor", "admin", "ecc_admin"})), db=Depends(DB.get_db))->List[EmergencyContact]:
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


@app.post("/user-activities", tags=["users"], description="Submit user activity interests", summary="Store activity interests for a youth")
async def submit_user_activities(data: UserActivityInterests, db=Depends(DB.get_db)):
    """
    Store which activities a youth is interested in.
    Looks up the user_id from username and stores the activities.
    """
    cursor = db.cursor()
    
    # Look up user_id from username
    cursor.execute(
        "SELECT user_id, org_group FROM admin_users WHERE username = ?",
        (data.username,)
    )
    user_row = cursor.fetchone()
    
    if not user_row:
        raise HTTPException(status_code=404, detail=f"User '{data.username}' not found")
    
    user_id, org_group = user_row
    
    # Check if already submitted this year
    cursor.execute(
        "SELECT COUNT(*) FROM interest_survey WHERE youth_id = ? AND strftime('%Y', submitted_at) = strftime('%Y', 'now')",
        (user_id,)
    )
    existing = cursor.fetchone()
    if existing and existing[0] > 0:
        return {"message": "Activity interests already submitted for this year", "user_id": user_id}
    
    # Store the activity interests
    cursor.execute(
        """INSERT INTO interest_survey (youth_id, interests, org_group, submitted_at)
           VALUES (?, ?, ?, ?)""",
        (user_id, json.dumps(data.activity_ids), org_group, datetime.now().isoformat())
    )
    db.commit()
    
    return {"message": "Activity interests submitted successfully", "user_id": user_id, "activities_count": len(data.activity_ids)}


#######################################
######  Interests and Concerns
######################################
@app.post("/interest-survey", tags=["interest-survey"], description="Submit interest survey", summary="Submit youth interest survey")
async def submit_interest_survey(data:InterestSurvey,db=Depends(DB.get_db)):
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


@app.post("/interest-survey-reset", tags=["interest-survey"], description="Reset interest survey for youth", summary="Reset youth interest survey")
async def reset_interest_survey(data: ResetInterestSurveyRequest, db=Depends(DB.get_db)):
    """
    Reset (delete) the interest survey for a youth.
    Takes username in request body and looks up the associated user_id.
    """
    cursor = db.cursor()
    
    # Look up user_id from username
    cursor.execute(
        "SELECT user_id FROM admin_users WHERE username = ?",
        (data.username,)
    )
    user_row = cursor.fetchone()
    
    if not user_row:
        raise HTTPException(status_code=404, detail=f"User '{data.username}' not found")
    
    youth_id = user_row[0]
    
    # Delete the interest survey
    cursor.execute(
        "DELETE FROM interest_survey WHERE youth_id = ?", (youth_id,)
    )
    db.commit()
    
    return {"message": "Interest survey reset successfully.", "user_id": youth_id}


@app.get("/interest-survey/{group}", tags=["interest-survey"], description="Get interest survey responses for a group", summary="Retrieve group interest surveys")
async def get_interest_survey(group: str, db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute('SELECT interests FROM interest_survey WHERE "group" = ?', (group,))
    rows = cursor.fetchall()
    return [json.loads(r[0]) for r in rows]


@app.get("/group-concerns/{group}", tags=["interest-survey"], description="Get concern survey responses for a group", summary="Retrieve group concern surveys")
async def get_concern_survey(group: str, db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute('SELECT concerns FROM concern_survey WHERE "org_group" = ?', (group,))
    rows = cursor.fetchall()
    return [json.loads(r[0]) for r in rows]



@app.post("/group-concerns", tags=["interest-survey"], description="Submit concern survey for a group", summary="Submit group concern survey")
async def submit_concern_survey(data:ConcernSurvey, db=Depends(DB.get_db)):
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
@app.get("/group-participants/{group}", tags=["activities"], description="Get list of participants for a group", summary="List group participants")
def list_group_participants(group:str, db=Depends(DB.get_db))->list:
    # get list of user ids in the group
    cursor = db.cursor()
    cursor.execute(
        "SELECT youth_id, youth FROM youth_medical WHERE json_extract(youth, '$.org_group') = ?", (group,)
    )
    rows = cursor.fetchall()
    return rows


@app.post("/activities", tags=["activities"], description="Create a new activity", summary="Create new activity")
async def create_activity(activity_data: Activity, db=Depends(DB.get_db)):
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
        participants = list_group_participants(group, db)
        all_users.extend(participants)
    cursor = db.cursor()

    # generate an activity identifier and store the payload as JSON
    activity_id = str(uuid.uuid4())
    
    # Serialize complex fields as JSON
    budget_json = json.dumps(activity_data.budget) if hasattr(activity_data, 'budget') and activity_data.budget else None
    groups_json = json.dumps(activity_data.groups) if hasattr(activity_data, 'groups') and activity_data.groups else None
    drivers_json = json.dumps(activity_data.drivers) if hasattr(activity_data, 'drivers') and activity_data.drivers else None
    participants_json = json.dumps(all_users) if all_users else None

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
            participants_json,
            groups_json,
            drivers_json,
            1 if is_overnighter else 0,
            1 if coed else 0,
            1 if activity_data.requires_permission else 0
        )
    )
    db.commit()
    return {"message": "Activity created successfully.", "activity_id": activity_id}


@app.get("/activities/{activity_id}", tags=["activities"], description="Get activity by ID", summary="Retrieve activity details")
async def get_activity(activity_id: str, db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups, requires_permission, bishop_approval, stake_approval FROM activities WHERE activity_id = ?",
        (activity_id,)
    )
    row = cursor.fetchone()
    if row:
        return {
            "activity_id": row[0],
            "activity_name": row[1],
            "date_start": row[2],
            "date_end": row[3],
            "drivers": row[4],
            "description": row[5],
            "groups": row[6],
            "requires_permission": row[7],
            "bishop_approval": row[8],
            "stake_approval": row[9]
        }
    else:
        return {"message": "Activity not found."}


@app.delete("/activities/{activity_id}", tags=["activities"], description="Delete activity by ID", summary="Delete activity")
async def delete_activity(activity_id: str, db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM activities WHERE activity_id = ?", (activity_id,)
    )
    db.commit()
    return {"message": "Activity deleted successfully."}


@app.put("/activities/{activity_id}", tags=["activities"], description="Update activity by ID", summary="Update activity details")
async def update_activity(activity_id: str, activity_data: Activity, db=Depends(DB.get_db)):
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
    groups_json = json.dumps(activity_data.groups) if hasattr(activity_data, 'groups') and activity_data.groups else None
    drivers_json = json.dumps(activity_data.drivers) if hasattr(activity_data, 'drivers') and activity_data.drivers else None
    
    # Get all users for updated groups
    all_users = []
    for group in activity_data.groups:
        participants = list_group_participants(group, db)
        all_users.extend(participants)
    participants_json = json.dumps(all_users) if all_users else None
    
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
            participants_json,
            groups_json,
            drivers_json,
            1 if is_overnighter else 0,
            1 if coed else 0,
            1 if activity_data.requires_permission else 0,
            activity_id
        )
    )
    db.commit()
    return {"message": "Activity updated successfully."}



@app.get("/participants/{activity_id}", tags=["activities"], description="Get participants for activity by ID", summary="Retrieve activity participants")
async def get_activity_participants(activity_id: str, db=Depends(DB.get_db))->List[ActivityInvitees]:
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


@app.get("/group-membership/{group}", tags=["activities"], description="Get participants for a group", summary="Retrieve group membership")
async def get_group_membership(group: str, db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT participants_youth_ids FROM activities WHERE groups LIKE ?", (f"%{group}%",)
    )
    rows = cursor.fetchall()
    all_participants = []
    for row in rows:
        all_participants.extend(json.loads(row[0]))
    return {"participants": all_participants}


@app.get("/activities/permission-info/{activity_id}",tags=["activities"],description="Get permission info for activity by ID", summary="Retrieve activity permission information")
async def get_activity_permission_info(activity_id: str, db=Depends(DB.get_db))->ActivityBase:
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


@app.post("/activity-permissions", tags=["activity-permissions"], description="Assign permission to activity", summary="Record activity permission")
async def assign_permission_to_activity(permission_data: PermissionGiven, db=Depends(DB.get_db)):
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


@app.get("/activity-groups", tags=["activities"], description="Get all group activities", summary="Retrieve group activities")
def get_activity_groups(db=Depends(DB.get_db),user=Depends(require_role({"advisor", "admin", "ecc_admin", "president"})))->List[ReturnGroupActivityList]:
    group = user.get("org_group")
    cursor = db.cursor()
    cursor.execute(
        "SELECT activity_id, activity_name, date_start, requires_permission FROM activities WHERE groups LIKE ?", (f"%{group}%",)
    )
    rows = cursor.fetchall()
    return [ReturnGroupActivityList(**row) for row in rows]


@app.get("/activity-health-reports/{activity_id}", tags=["activities"], description="Get health reports for activity by ID", summary="Retrieve activity health reports")
def get_activity_health_reports(activity_id: str, db=Depends(DB.get_db), users=Depends(require_role({"advisor", "admin", "ecc_admin", "president"})))->ActivityHealthReport:
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


@app.get("/activities-all-parents", tags=["activities"], description="Get all activities with parent details", summary="Retrieve activities for parent")
def get_all_activities_with_parents(parent_code:str = Query(..., description="Parent permission code"), db=Depends(DB.get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT activity_id, activity_name, date_start, date_end, drivers, description, groups, requires_permission FROM activities WHERE activity_id IN (SELECT activity_id FROM permission_given WHERE permission_code = ?)", (parent_code,)
    )
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        activities.append(ActivityBase(**row))
    return {"activities": activities}


@app.get("/activities-all", tags=["activities"], description="Get all activities", summary="Retrieve all activities")
def get_all_activities(include_past: bool = Query(False, description="Include past activities"), db=Depends(DB.get_db) )->Dict[str, List[ActivityBase]]:
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


@app.get("/activities-pending-approval", tags=["activities"], description="Get all activities pending approval", summary="Retrieve pending activity approvals")
def get_activities_pending_approval(db=Depends(DB.get_db))->List[ActivityApprovals]:
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
@app.post("/admin-users", tags=["admin-users","auth"], description="Create a new admin user", summary="Create admin user account")
async def create_admin_user(
    user: AdminUser, 
    user_info: dict = Depends(require_role({"admin"})),
    db=Depends(DB.get_db)
):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE admin_users SET username = ?, password = ?, role = ? WHERE org_group = ?",
        (user.username, user.password, user.role, user.org_group)
    )
    db.commit()
    return {"message": "Admin user created successfully."}





@app.post("/login-verify", tags=["admin-users","auth"], description="Verify admin user token", summary="Verify authentication token")
def verify_login(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"message": "Token is valid", "payload": payload}
    except JWTError:
        return {"message": "Invalid token"}


@app.post("/admin/query", tags=["admin"], description="Execute SQL query (admin only)", summary="Run custom SQL query")
def execute_admin_query(
    request: Request,
    query_request: AdminSQLQuery,
    user_info: dict = Depends(require_role({"all", "admin"})),
    db=Depends(DB.get_db)
) -> AdminQueryResult:
    """
    Execute custom SQL queries with restrictions and logging.
    - Supports SELECT, INSERT, UPDATE, DELETE
    - Queries are validated and logged
    - All queries logged to audit trail
    """
    try:
        query = query_request.query.strip()
        
        # Validate query - only allow SELECT, INSERT, UPDATE, DELETE
        allowed_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        query_upper = query.upper()
        
        if not any(query_upper.startswith(kw) for kw in allowed_keywords):
            audit_log_event(
                request=request,
                actor_username=user_info.get("sub"),
                actor_role=user_info.get("role"),
                action="ADMIN_QUERY",
                resource_type="database",
                resource_id="query_execution",
                success=False,
                details={"reason": "invalid_query_type", "query": query[:100]},
                db=db,
            )
            raise HTTPException(
                status_code=400,
                detail="Only SELECT, INSERT, UPDATE, DELETE queries are allowed"
            )
        
        # Prevent dangerous patterns
        dangerous_patterns = [
            r"DROP\s",
            r"TRUNCATE\s",
            r"ALTER\s+TABLE",
            r"PRAGMA\s+",
            r"VACUUM",
            r"DETACH",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                audit_log_event(
                    request=request,
                    actor_username=user_info.get("sub"),
                    actor_role=user_info.get("role"),
                    action="ADMIN_QUERY",
                    resource_type="database",
                    resource_id="query_execution",
                    success=False,
                    details={"reason": "dangerous_pattern_detected", "pattern": pattern},
                    db=db,
                )
                pattern_name = pattern.replace(r'\s', ' ').strip()
                raise HTTPException(
                    status_code=400,
                    detail=f"Query contains forbidden operation: {pattern_name}"
                )
        
        # Execute query with timeout
        cursor = db.cursor()
        start_time = time.time()
        
        try:
            cursor.execute(query)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Handle different query types
            if query_upper.startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                row_count = len(rows)
                
                # Convert rows to dictionaries
                rows_data = []
                for row in rows:
                    if isinstance(row, dict):
                        rows_data.append(row)
                    else:
                        row_dict = {}
                        if cursor.description:
                            for i, col in enumerate(cursor.description):
                                row_dict[col[0]] = row[i]
                        rows_data.append(row_dict)
                
                result = AdminQueryResult(
                    success=True,
                    message=f"Query executed successfully. Retrieved {row_count} rows.",
                    query=query,
                    execution_time_ms=execution_time_ms,
                    row_count=row_count,
                    columns=columns,
                    rows=rows_data
                )
            else:
                # For INSERT, UPDATE, DELETE
                db.commit()
                row_count = cursor.rowcount
                
                result = AdminQueryResult(
                    success=True,
                    message=f"Query executed successfully. {row_count} rows affected.",
                    query=query,
                    execution_time_ms=execution_time_ms,
                    row_count=row_count,
                    columns=None,
                    rows=None
                )
            
            # Log successful query
            audit_log_event(
                request=request,
                actor_username=user_info.get("sub"),
                actor_role=user_info.get("role"),
                action="ADMIN_QUERY",
                resource_type="database",
                resource_id="query_execution",
                success=True,
                details={
                    "query": query[:200],
                    "row_count": row_count,
                    "execution_time_ms": execution_time_ms
                },
                db=db,
            )
            
            return result
            
        except sqlite3.Error as db_error:
            execution_time_ms = (time.time() - start_time) * 1000
            
            audit_log_event(
                request=request,
                actor_username=user_info.get("sub"),
                actor_role=user_info.get("role"),
                action="ADMIN_QUERY",
                resource_type="database",
                resource_id="query_execution",
                success=False,
                details={"error": str(db_error), "query": query[:100]},
                db=db,
            )
            
            return AdminQueryResult(
                success=False,
                message="Query execution failed",
                query=query,
                execution_time_ms=execution_time_ms,
                row_count=0,
                columns=None,
                rows=None,
                error=str(db_error)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        audit_log_event(
            request=request,
            actor_username=user_info.get("sub"),
            actor_role=user_info.get("role"),
            action="ADMIN_QUERY",
            resource_type="database",
            resource_id="query_execution",
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/activity-permission-ecclesiastical", tags=["admin-users","activities"], description="Get activity permission details for Bishop/Stake President", summary="Get ecclesiastical approvals")
def get_activity_permission_ecclesiastical(is_bishop: bool = Query(..., description="Is the requester a bishop?"), is_stake_president: bool = Query(..., description="Is the requester a stake president"), db=Depends(DB.get_db))->List[FullActivity]:
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
    tags=["admin-users","activities"],
    description="Approve activity permission for Bishop/Stake President",
    summary="Approve activity permission"
)
def approve_activity_permission_ecclesiastical(
    activity_id: str = Path(..., description="The ID of the activity"),
    is_bishop: bool = Query(..., description="Is the requester a bishop?"),
    is_stake_president: bool = Query(..., description="Is the requester a stake president?"),
    db=Depends(DB.get_db),
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
    tags=["tools","activities"],
    description="Generate SMS content for activity permission",
    summary="Generate SMS message for activity permission request"
)
def sms_activity_permission(
    activity_id: str = Path(..., description="The ID of the activity"),
    db=Depends(DB.get_db),
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
    tags=["tools","activities"],
    description="Generate email content for activity permission",
    summary="Generate email message for activity permission request"
)
def email_activity_permission(
    activity_id: str = Path(..., description="The ID of the activity"),
    db=Depends(DB.get_db),
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


@app.post("/sms-activity-permission", tags=["tools","activities"], description="Send SMS to activity participants for permission", summary="Send permission SMS for activity")
async def send_activity_permission_sms(request: Request, activity_id: str = Query(...), db=Depends(DB.get_db)):
    """
    Send SMS messages to parents/guardians of activity participants requesting permission.
    Queries the activity participants and retrieves parent contact info from youth_medical table.
    """
    try:
        cursor = db.cursor()
        
        # Get activity details
        cursor.execute(
            "SELECT activity_id, activity_name, date_start, participants_youth_ids FROM activities WHERE activity_id = ?",
            (activity_id,)
        )
        activity_row = cursor.fetchone()
        if not activity_row:
            raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found")
        
        act_id, act_name, date_start, participants_json = activity_row
        participants = json.loads(participants_json) if participants_json else []
        
        # Get base URL from environment
        base_url = os.getenv("BaseActivitySiteURL", "http://localhost:8000")
        permission_link = f"{base_url}/activity-permission/{activity_id}"
        
        # Prepare SMS message
        sms_message = f"""Activity Permission Request: {act_name}

Date: {date_start}
Your youth has been invited to participate.
Please review and grant permission here:
{permission_link}

Thank you!"""
        
        # Collect all parent phone numbers
        sent_count = 0
        failed_count = 0
        parent_phones = []
        
        for youth_id in participants:
            cursor.execute(
                "SELECT parent_guardian FROM youth_medical WHERE youth_id = ?",
                (youth_id,)
            )
            med_row = cursor.fetchone()
            if med_row:
                try:
                    parent_data = json.loads(med_row[0])
                    if isinstance(parent_data, dict) and 'phone' in parent_data:
                        parent_phones.append(parent_data['phone'])
                    elif isinstance(parent_data, list):
                        for parent in parent_data:
                            if isinstance(parent, dict) and 'phone' in parent:
                                parent_phones.append(parent['phone'])
                except json.JSONDecodeError:
                    pass
        
        # Send SMS to each parent (via ContactEngine if available)
        contact_engine = ContactEngine()
        for phone in parent_phones:
            try:
                contact_engine.send_sms(sms_message, phone)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send SMS to {phone}: {str(e)}")
                failed_count += 1
        
        # Audit log
        audit_log_event(
            request=request,
            actor_username="system",
            actor_role="system",
            action="send_activity_permission_sms",
            resource_type="activity",
            resource_id=activity_id,
            success=True,
            details={"participants": len(participants), "sms_sent": sent_count, "sms_failed": failed_count},
            db=db,
        )
        
        return {
            "message": f"SMS sent to {sent_count} parents, {failed_count} failed",
            "activity_id": activity_id,
            "participants_count": len(participants),
            "sms_sent": sent_count,
            "sms_failed": failed_count
        }
    
    except Exception as e:
        print(f"Error sending activity permission SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@app.get("/activity-qrcode", tags=["tools","activities"], description="Generate QR code for activity permission link", summary="Generate QR for the activity")
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


@app.get("/activity-calendar",tags=["tools","activities"], description="Generate calendar invite for activity event", summary="Generate calendar invite for the activity")
def invite(activity_id: str = Query(..., description="The ID of the activity"), db=Depends(DB.get_db)):
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
@app.post("/activities/reconcile", tags=["activities"], description="Reconcile activities", summary="Reconcile activity details")
async def reconcile_activities(data:FullActivity, db=Depends(DB.get_db)):
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


@app.get("/activities/reconcile/{activity_id}", tags=["activities"], description="Get activity for reconciliation by ID", summary="Retrieve activity for reconciliation")
def get_activity_for_reconciliation(activity_id: str, db=Depends(DB.get_db))->FullActivity:
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM activities WHERE activity_id = ?", (activity_id,)
    )
    row = cursor.fetchone()
    if not row:
        return Response(content="Activity not found.", status_code=404)
    activity_data = FullActivity(**row)
    return activity_data


@app.put("/activities/reconcile/{activity_id}", tags=["activities"], description="Update activity for reconciliation by ID", summary="Update reconciled activity")
def update_activity_for_reconciliation(activity_id: str, data: FullActivity, db=Depends(DB.get_db)):
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

@app.post("/goals", tags=["goals"], description="Set personal goal", summary="Create personal goal")
def set_personal_goal(data: PersonalGoal, db=Depends(DB.get_db), user=Depends(require_role("youth"))):
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO personal_goals (youth_id, goal_area, goal_name, goal_description,  target_date, status, progress_notes, visibility_level)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.youth_id,
            data.goal_area,
            data.goal_name,
            data.goal_description,
            data.target_date,
            data.status,
            json.dumps(data.progress_notes) if data.progress_notes else None,
            data.visibility_level
        )
    )
    db.commit()
    return {"message": "Personal goal set successfully."}

@app.get("/goals/{youth_id}", tags=["goals"], description="Get personal goals for youth", summary="Retrieve youth personal goals")
def get_personal_goals(youth_id: str, db=Depends(DB.get_db), user=Depends(require_role("youth")))->List[PersonalGoal]:
    cursor = db.cursor()
    cursor.execute(
        "SELECT youth_id, goal_area, goal_name, goal_description, target_date, status, progress_notes, completed, visibility_level FROM personal_goals WHERE youth_id = ? group by goal_area", (youth_id,)
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
            completed=bool(row["completed"]),
            visibility_level=row["visibility_level"]
        )
        goals.append(goal)
    return goals


@app.put("/goals/{youth_id}/{goal_name}", tags=["goals"], description="Update personal goal for youth", summary="Update personal goal")
def update_personal_goal(youth_id: str, goal_name: str, data: PersonalGoal, db=Depends(DB.get_db), user=Depends(require_role("youth"))):
    cursor = db.cursor()
    cursor.execute(
        """UPDATE personal_goals 
           SET goal_area = ?, goal_description = ?, target_date = ?, status = ?, progress_notes = ?, completed = ?, visibility_level = ?
           WHERE youth_id = ? AND goal_name = ?""",
        (
            data.goal_area,
            data.goal_description,
            data.target_date,
            data.status,
            json.dumps(data.progress_notes) if data.progress_notes else None,
            1 if data.completed else 0,
            youth_id,
            goal_name,
            data.visibility_level
        )
    )
    db.commit()
    if cursor.rowcount > 0:
        return {"message": "Personal goal updated successfully."}
    else:
        return {"message": "Personal goal not found."}


@app.get("/goal-view", tags=["goals"], description="View goals", summary="Allows viewing of goals based on visibility level")
def view_youth_goals(db=Depends(DB.get_db), user=Depends(require_role("all")))->List[PersonalGoal]:
    cursor = db.cursor()
    if user.role =="ecc_admin":
        where_clause = " WHERE visibility_level IN ('public','ecclesiastical') "
    elif user.role =="advisor":
        where_clause = " WHERE visibility_level IN ('public','advisor') "
    elif user.role == "youth": #TODO change so only show goals of same group
        where_clause = " WHERE visibility_level IN ('public','group') AND group_"
    elif user.role == "parent":
        where_clause = " WHERE visibility_level IN ('public','parent') AND youth_id IN (SELECT youth_id FROM youth_parent WHERE parent_code = ? )"
    cursor.execute(
        "SELECT youth_id, goal_area, goal_name, goal_description, target_date, status, progress_notes, completed, visibility_level FROM personal_goals GROUP BY goal_area " + where_clause
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
            completed=bool(row["completed"]),
            visibility_level=row["visibility_level"]
        )
        goals.append(goal)
    return goals

# ===== Youth Data Editor Endpoint =====
@app.get("/api/youth/data", tags=["youth-editor"], description="Get youth data for editor", summary="Retrieve youth data JSON")
def get_youth_data():
    """
    Retrieve the complete youth_data.json for the web editor.
    Returns all youth records with their current information.
    """
    try:
        youth_data_path = PathlibPath(__file__).parent.parent / "file_load" / "youth_data.json"
        
        if not youth_data_path.exists():
            raise HTTPException(status_code=404, detail="Youth data file not found")
        
        with open(youth_data_path, 'r') as f:
            all_youth = json.load(f)
        
        return all_youth
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading youth data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load youth data: {str(e)}")

@app.post("/api/youth/save", tags=["youth-editor"], description="Save updated youth data from editor", summary="Save youth data changes")
def save_youth_data(youth_data: Dict[str, Any]):
    """
    Save updated youth data from the web editor back to youth_data.json.
    Expects the complete youth record with all fields.
    """
    try:
        # Path to the youth data JSON file
        youth_data_path = PathlibPath(__file__).parent.parent / "file_load" / "youth_data.json"
        
        if not youth_data_path.exists():
            raise HTTPException(status_code=404, detail="Youth data file not found")
        
        # Load current data
        with open(youth_data_path, 'r') as f:
            all_youth = json.load(f)
        
        # Find the matching youth entry
        first_name = youth_data.get('first_name')
        last_name = youth_data.get('last_name')
        permission_code = youth_data.get('permission_code')
        
        youth_index = None
        for idx, youth in enumerate(all_youth):
            if (youth.get('first_name') == first_name and 
                youth.get('last_name') == last_name and 
                youth.get('permission_code') == permission_code):
                youth_index = idx
                break
        
        if youth_index is None:
            raise HTTPException(status_code=404, detail="Youth not found in database")
        
        # Update the youth record, preserving original fields
        updated_youth = all_youth[youth_index].copy()
        updated_youth.update(youth_data)
        all_youth[youth_index] = updated_youth
        
        # Save back to file
        with open(youth_data_path, 'w') as f:
            json.dump(all_youth, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Youth {first_name} {last_name} updated successfully",
            "updated_fields": list(youth_data.keys())
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving youth data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save youth data: {str(e)}")

# if __name__ == "__main__":
# 	import uvicorn
# 	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)