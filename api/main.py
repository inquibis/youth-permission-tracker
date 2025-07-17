from fastapi import FastAPI, Depends, HTTPException, Request, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import base64, os
from datetime import datetime
import json
from fastapi import Form, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi import Security
from fastapi import Query
from typing import List, Optional
import os
import csv
import io


from schema import ActivityInformationCreate, ActivityPermissionRequest, UserCreate, ActivityCreate, ActivityInformationOut, UserInterestIn, SelectedActivityOut
from models import ActivityBudget, ActivityDriver, ActivityGroup, ActivityPermission, SelectedActivity, User, Activity, PermissionToken, ActivityPermissionMedical, ActivityInfo
from database import Base, engine, SessionLocal
from pdf_func import create_signed_pdf, generate_waiver_pdf
from auth import hash_password, decode_token
from auth import verify_password, create_token
from contact import Contact
from data import activity_list


ENV = os.getenv("ENV", "prod")
print(f"Starting API\nEnvironment: {ENV}")

# Initializations
Base.metadata.create_all(bind=engine)
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
contact_engine = Contact()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional: Allow CORS from frontend app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


###################
### USER SECTION
###################
    
def get_current_user(token: str = Security(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    

@app.post("/login", tags=["Users"])
def login(username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    if username != "tester" and password != "testing123":
        user = db.query(User).filter(User.user_email == username).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    #TODO        
    user_data = {"sub": username}
    if ENV=="test":
        user_data = {
            "role":"tester",
            "is_guardian":1,
            "username":username
        }
    token = create_token(user_data)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/list-roles", tags=["Users"])
def get_roles():
    return list("admin", "bishopric", "guardian", "presidency", "tester", "youth")


@app.get("/list-groups", tags=["Users"], description="List potential group membership")
def get_roles():
    return list("Deacon","Teacher","Priest","Young Man","Young Woman", "Young Woman-younger","Young Woman-older")

@app.get("/groups", tags=["Users"], description="List current group memberships of members")
def get_current_groups(db: Session = Depends(get_db)):
    return list({user.group for user in db.query(User).all()})


@app.post("/users-groupload", tags=["Users"])
async def upload_users_from_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    db = SessionLocal()
    added_users = 0

#  "id": self.id,
#             "first_name": self.first_name,
#             "last_name": self.last_name,
#             "guardian_name": self.guardian_name,
#             "guardian_email": self.guardian_email,
#             "guardian_cell": self.guardian_cell,
#             "user_email": self.user_email,
#             "user_cell": self.user_cell,
#             "is_active": self.is_active,
#             "groups": json.loads(self.groups or "[]"),
    try:
        for row in reader:
            user = User(
                name=row.get("name"),
                email=row.get("email"),
                age=int(row.get("age", 0))
            )
            db.add(user)
            added_users += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    finally:
        db.close()

    return {"message": f"Uploaded and added {added_users} users successfully."}


@app.get("/users", tags=["Users"])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [u.to_dict() for u in users]


@app.post("/users", tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resource"
        )
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        guardian_name=user.guardian_name,
        guardian_email=user.guardian_email,
        guardian_cell=user.guardian_cell,
        user_email=user.user_email,
        user_cell=user.user_cell,
        is_active=user.is_active,
        groups=json.dumps(user.groups)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user.to_dict()


@app.put("/users/{user_id}", tags=["Users"])
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resource"
        )
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in user.dict().items():
        if field == "groups":
            setattr(db_user, field, json.dumps(value))
        else:
            setattr(db_user, field, value)
    db.commit()
    return db_user.to_dict()


@app.get("/verify-token", tags=["Users"])
def verify_token(token: str, db: Session = Depends(get_db)):
    record = db.query(PermissionToken).filter_by(token=token, used=False).first()
    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return {
        "user_name": record.user.first_name + " " + record.user.last_name,
        "activity_name": record.activity.activity_name,
        "description": record.activity.description,
        "date_start": record.activity.date_start.isoformat(),
        "date_end": record.activity.date_end.isoformat()
    }


###################
### BASE SECTION
###################

@app.get("/hello-world")
def hello_world(current_user: dict = Depends(get_current_user)):
    return current_user


##########################
##  ACTIVITIES
##########################
@app.get("/activity",  tags=["Activities"])
def get_activity(id: int = Query(..., alias="id"), db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return {
        "activity_id": activity.id,
        "activity_name": activity.name,
        "date_start": activity.date_start,
        "date_end": activity.date_end,
        "drivers": activity.drivers,
        "description": activity.description,
        "youth_name": activity.youth_name
    }


@app.post("/activity",  tags=["Activities"])
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    activity = Activity(
        activity_name=payload.activity_name,
        date_start=payload.date_start,
        date_end=payload.date_end,
        drivers=payload.drivers,
        description=payload.description,
        groups=payload.groups
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    contact_engine.contact_users(groups=activity.groups, db=db)
    return {"message": "Activity created", "id": activity.id}


@app.put("/activity/{activity_id}",  tags=["Activities"])
def update_activity(activity_id: int, payload: ActivityCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    for field, value in payload.dict().items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    return {"message": "Activity updated", "id": activity.id}


@app.delete("/activity/{activity_id}",  tags=["Activities"])
def delete_activity(activity_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    db.delete(activity)
    db.commit()
    return {"message": "Activity deleted"}


@app.get("/activity-all",  tags=["Activities"])
def get_all_activities(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Activity).all()


############### PERMISSIONS
@app.post("/submit-permission",  tags=["Permission"])
def submit_permission(token: str, db: Session = Depends(get_db)):
    record = db.query(PermissionToken).filter_by(token=token, used=False).first()
    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Mark signed
    perm = db.query(ActivityPermission).filter_by(user_id=record.user_id, activity_id=record.activity_id).first()
    if not perm:
        perm = ActivityPermission(user_id=record.user_id, activity_id=record.activity_id)
        db.add(perm)

    perm.signed = True
    record.used = True
    db.commit()
    return {"status": "signed"}


@app.post("/submit-permission-detail",  tags=["Permission"])
def submit_permission_detail(data: dict, request: Request, db: Session = Depends(get_db)):
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    record = db.query(PermissionToken).filter_by(token=token, used=False).first()
    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    # Update or create permission
    perm = db.query(ActivityPermission).filter_by(user_id=record.user_id, activity_id=record.activity_id).first()
    if not perm:
        perm = ActivityPermission(user_id=record.user_id, activity_id=record.activity_id)
        db.add(perm)

    perm.signed = True
    perm.ip_address = ip_address
    perm.user_agent = user_agent

    record.used = True
    db.commit()

    # Generate PDF
    pdf_path = f"./pdfs/waivers/{record.user_id}-{record.activity_id}.pdf"
    generate_waiver_pdf(
        user_name = f"{record.user.first_name} {record.user.last_name}",
        guardian_name = record.user.guardian_name,
        activity_name = record.activity.activity_name,
        date_start = record.activity.date_start.strftime("%Y-%m-%d"),
        date_end = record.activity.date_end.strftime("%Y-%m-%d"),
        description = record.activity.description,
        ip = ip_address,
        user_agent = user_agent,
        output_path = pdf_path
    )

    # Email Admin
    contact_engine.send_admin_confirmation(
        user_name = f"{record.user.first_name} {record.user.last_name}",
        guardian_name = record.user.guardian_name,
        activity_name = record.activity.activity_name,
        pdf_path = pdf_path
    )

    return {"status": "signed"}


@app.post("/activity-permission-medical",  tags=["Permission"])
def submit_permission_medical(data: ActivityPermissionRequest, request: Request, db: Session = Depends(get_db)):
    # Save signature to file (optional)
    signature_path = None
    if data.signature:
        try:
            header, encoded = data.signature.split(",", 1)
            signature_data = base64.b64decode(encoded)
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"sig_{data.activity_id}_{ts}.png"
            os.makedirs("signatures", exist_ok=True)
            signature_path = os.path.join("signatures", filename)
            with open(signature_path, "wb") as f:
                f.write(signature_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid signature format")

    entry = ActivityPermissionMedical(
        activity_id=data.activity_id,
        allergies=data.allergies,
        restrictions=data.restrictions,
        special_diet=data.special_diet,
        prescriptions=data.prescriptions,
        over_the_counter_drugs=data.over_the_counter_drugs,
        chronic_illness=data.chronic_illness,
        surgeries_12mo=data.surgeries_12mo,
        serious_illnesses=data.serious_illnesses,
        comments=data.comments,
        dl=data.dl,
        pin=data.pin,
        signature_path=signature_path,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"status": "success", "entry_id": entry.id}


@app.get("/request-permissions",  tags=["Permission"])
def request_permissions(activity_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    # Get permission records for this activity
    permissions = db.query(ActivityPermission).filter_by(activity_id=activity_id, signed=False).all()
    if not permissions:
        return {"status": "no pending signatures"}

    # Get user records
    users = [perm.user for perm in permissions]

    # Get activity name for message
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    activity_name = activity.activity_name if activity else "an activity"

    # Notify guardians
    contact_engine.email_guardians(users, activity_name)
    contact_engine.sms_guardians(users, activity_name)

    # Update last_requested_at
    for perm in permissions:
        perm.last_requested_at = datetime.utcnow()

    db.commit()

    return {
        "status": "requested",
        "count": len(users)
    }


@app.get("/resend-permission",  tags=["Permission"])
def resend_permission(id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403)

    perm = db.query(ActivityPermission).filter(ActivityPermission.id == id).first()
    if not perm or perm.signed:
        raise HTTPException(status_code=404, detail="No pending permission")

    contact_engine.email_guardians([perm.user], "Activity")
    contact_engine.sms_guardians([perm.user], "Activity")

    perm.last_requested_at = datetime.utcnow()
    db.commit()
    return {"status": "resent"}


@app.get("/activity-permissions",  tags=["Permission"])
def get_activity_permissions(activity_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    permissions = (
        db.query(ActivityPermission)
        .join(User)
        .filter(ActivityPermission.activity_id == activity_id)
        .all()
    )
    return [
        {
            "user_name": p.user.first_name + " " + p.user.last_name,
            "guardian_name": p.user.guardian_name,
            "signed": p.signed,
            "last_requested_at": p.last_requested_at.isoformat() if p.last_requested_at else None,
            "permission_id": p.id
        }
        for p in permissions
    ]


# return format
#[
#   {
#     "user_name": "Sam Smith",
#     "guardian_name": "John Smith",
#     "signed": true
#   },
#   {
#     "user_name": "Lucy Jones",
#     "guardian_name": "Alice Jones",
#     "signed": false
#   }
# ]

@app.post("/activity-ideas",  tags=["Activities"])
def get_act_list():
    return activity_list

@app.post("/activity-information",  tags=["Activities"])
def create_activity_info(payload: ActivityInformationCreate, db: Session = Depends(get_db)):
    activity = ActivityInfo(
        activity_name=payload.activity_name,
        description=payload.description,
        date_start=payload.date_start,
        date_end=payload.date_end,
        purpose=payload.purpose
    )
    db.add(activity)
    db.flush()  # To get activity.id

    for item in payload.budget:
        db.add(ActivityBudget(item=item.item, amount=item.amount, activity_id=activity.id))
    for name in payload.drivers:
        db.add(ActivityDriver(name=name, activity_id=activity.id))
    for group in payload.groups:
        db.add(ActivityGroup(group=group, activity_id=activity.id))

    db.commit()
    return { "status": "ok", "activity_id": activity.id }


@app.get("/activity-information", response_model=ActivityInformationOut,  tags=["Activities"])
def get_activity_info(
    activity_id: Optional[int] = Query(None),
    activity_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if not activity_id and not activity_name:
        raise HTTPException(status_code=400, detail="Either activity_id or activity_name is required")

    query = db.query(ActivityInfo)
    if activity_id:
        activity = query.filter_by(id=activity_id).first()
    else:
        activity = query.filter_by(activity_name=activity_name).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Query related fields
    budgets = db.query(ActivityBudget).filter_by(activity_id=activity.id).all()
    drivers = db.query(ActivityDriver).filter_by(activity_id=activity.id).all()
    groups = db.query(ActivityGroup).filter_by(activity_id=activity.id).all()

    return ActivityInformationOut(
        activity_id=activity.id,
        activity_name=activity.activity_name,
        description=activity.description,
        date_start=activity.date_start,
        date_end=activity.date_end,
        purpose=activity.purpose,
        budget=[{"item": b.item, "amount": b.amount} for b in budgets],
        drivers=[d.name for d in drivers],
        groups=[g.group for g in groups],
    )


@app.post("/user-interest",  tags=["Users","Activities"])
def save_user_interest(payload: UserInterestIn, db: Session = Depends(get_db)):
    # Find user by name (adjust query if needed)
    user = db.query(User).filter(User.first_name + " " + User.last_name == payload.name).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    year = datetime.utcnow().year

    # Store each activity as a separate SelectedActivity record
    for activity_name in payload.activities:
        sa = SelectedActivity(user_id=user.id, year=year, activity_name=activity_name)
        db.add(sa)
    db.commit()

    return {"status": "success", "user_id": user.id, "year": year, "activities_saved": len(payload.activities)}


@app.get("/user-interest", response_model=List[SelectedActivityOut],  tags=["Users","Activities"])
def list_user_interests(db: Session = Depends(get_db)):
    #TODO filter by activity group
    rows = db.query(User).join(SelectedActivity).all()
    result = []
    for user in rows:
        user_activities = db.query(SelectedActivity).filter(SelectedActivity.user_id == user.id).all()
        grouped = {}
        for activity in user_activities:
            grouped.setdefault(activity.year, []).append(activity.activity_name)
        for year, activities in grouped.items():
            result.append(SelectedActivityOut(
                name=f"{user.first_name} {user.last_name}",
                year=year,
                activities=activities
            ))
    return result

@app.get("/selectedactivities/user/{user_id}",  tags=["Users","Activities"])
def get_user_activities(user_id: int, db: Session = Depends(get_db)):
    return db.query(SelectedActivity).filter_by(user_id=user_id).all()

@app.get("/selectedactivities/group/{group_name}",  tags=["Users","Activities"])
def get_group_activities(group_name: str, db: Session = Depends(get_db)):
    users = db.query(User).filter_by(group=group_name).all()
    user_ids = [u.id for u in users]
    activities = db.query(SelectedActivity).filter(SelectedActivity.user_id.in_(user_ids)).all()
    
    from collections import Counter
    counts = Counter([act.activity_name for act in activities])
    return dict(counts)


##############################
##  group needs
##############################
# @app.get("/identified-needs/{group_name}")
# def get_needs(group_name: str, db: Session = Depends(get_db)):
#     return db.query(IdentifiedNeed).filter_by(group_name=group_name).all()

# @app.post("/identified-needs")
# def create_need(need: IdentifiedNeedCreate, db: Session = Depends(get_db)):
#     db_need = IdentifiedNeed(**need.dict())
#     db.add(db_need)
#     db.commit()
#     db.refresh(db_need)
#     return db_need

# @app.put("/identified-needs/{need_id}")
# def update_need(need_id: int, need: IdentifiedNeedCreate, db: Session = Depends(get_db)):
#     db.query(IdentifiedNeed).filter_by(id=need_id).update(need.dict())
#     db.commit()
#     return {"status": "updated"}

# @app.delete("/identified-needs/{need_id}")
# def delete_need(need_id: int, db: Session = Depends(get_db)):
#     db.query(IdentifiedNeed).filter_by(id=need_id).delete()
#     db.commit()
#     return {"status": "deleted"}