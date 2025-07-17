from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from datetime import date

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

class BudgetItem(BaseModel):
    item: str
    amount: float

class ActivityInformationCreate(BaseModel):
    activity_name: str
    description: str
    groups: List[str]
    drivers: List[str]
    budget: List[BudgetItem]
    date_start: date
    date_end: date
    purpose: str

class ActivityInformationOut(ActivityInformationCreate):
    activity_id: int

class UserInterestIn(BaseModel):
    name: str
    activities: List[str]

class SelectedActivityOut(BaseModel):
    name: str
    year: int
    activities: List[str]

    class Config:
        from_attributes = True