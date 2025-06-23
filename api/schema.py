from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ActivityPermissionRequest(BaseModel):
    activity_id: str

    allergies: Optional[str] = None
    restrictions: Optional[str] = None
    special_diet: Optional[str] = None
    prescriptions: Optional[str] = None
    over_the_counter_drugs: Optional[str] = None
    chronic_illness: Optional[str] = None
    surgeries_12mo: Optional[str] = None
    serious_illnesses: Optional[str] = None
    comments: Optional[str] = None
    dl: Optional[str] = None
    pin: Optional[str] = None
    signature: Optional[str] = None  # base64 PNG data

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    guardian_name: str
    guardian_email: str
    guardian_cell: str
    user_email: str
    user_cell: str
    is_active: Optional[bool] = True
    groups: List[str]
    guardian_password: str

class ActivityCreate(BaseModel):
    activity_name: str
    date_start: datetime
    date_end: datetime
    drivers: List[str]
    description: str = ""
    groups: List[str]