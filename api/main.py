from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
import base64, os
from datetime import datetime
import json
from fastapi import Form, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi import Security

from schema import ActivityPermissionRequest, UserCreate
from models import ActivityPermission, User, Activity
from database import Base, engine, SessionLocal
from pdf_func import create_signed_pdf
from auth import hash_password, decode_token
from auth import verify_password, create_token


# Initializations
Base.metadata.create_all(bind=engine)
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

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
        payload = decode_token(token)
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    

@app.post("/login")
def login(user_email: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_email == user_email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user.user_email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [u.to_dict() for u in users]


@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
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


@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
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


##########################
##  ACTIVITIES
##########################
@app.get("/activity")
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

@app.post("/activity-permission")
def submit_permission(data: ActivityPermissionRequest, request: Request, db: Session = Depends(get_db)):
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

    entry = ActivityPermission(
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
        signature_path=signature_path,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"status": "success", "entry_id": entry.id}
