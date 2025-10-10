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
    guardian_name: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_cell: Optional[str] = None
    user_email: str
    user_cell: str
    is_active: Optional[bool] = True
    groups: List[str]
    role: str
    guardian_password: Optional[str] = None

class ActivityCreate(BaseModel):
    activity_name: str
    date_start: datetime
    date_end: datetime
    drivers: List[str]
    description: str = ""
    groups: List[str]

class contact_request(BaseModel):
    activity_id:int
    guardians:List[str] #list of youth ids

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

class SignatureContact(BaseModel):
    text_number: int
    lvl: int
    name: str

class SelectedActivityOut(BaseModel):
    name: str
    year: int
    activities: List[str]

    class Config:
        from_attributes = True


class BudgetItemOut(BaseModel):
    name: str
    cost: float

class ActivityReviewOut(BaseModel):
    attendees: List[str]
    budget: float
    budget_items: List[BudgetItemOut]
    description: str

class ActivityReviewIn(BaseModel):
    activity_id: int
    general_thoughts: str
    what_went_well: str
    what_did_not_go_well: str
    actual_costs: float


class NeedBase(BaseModel):
    group_name: str
    need: str
    priority: int
    created_by: int

class NeedCreate(NeedBase):
    pass

class NeedUpdate(NeedBase):
    id: int

class NeedInDB(NeedBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True