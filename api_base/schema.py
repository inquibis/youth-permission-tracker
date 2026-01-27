from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime

class Youth(BaseModel):
    first_name: str
    last_name: str
    birth_date: str | None = None
    gender: str | None = None
    org_group: str | None = None

class ParentGuardian(BaseModel):
    name: str
    phone: str
    email: str | None = None
    relationship: str | None = None

class MedicalInfo(BaseModel):
    conditions: str | None = None
    medications: str | None = None
    allergies: str | None = None
    dietary_restrictions: str | None = None
    limitations: str | None = None
    special_accommodations: str | None = None

class EmergencyContact(BaseModel):
    name: str
    phone: str

class Signature(BaseModel):
    signed_by: str
    signature_image_base64: str

class YouthPermissionSubmission(BaseModel):
    permission_code: str = Field(..., pattern=r"^\d{6}$")
    youth: Youth
    parent_guardian: ParentGuardian
    medical: MedicalInfo
    emergency_contact: EmergencyContact
    signature: Signature
    signed_at: str
    youth_id:str =""

####### activities #########
class budget(BaseModel):
    total_amount: float
    items: List[dict]
    budget_id: str
    actual_amount: float | None = None

class Activity(BaseModel):
    activity_id: str
    name: str
    description: str
    date: str
    location: str
    budget: budget
    drivers: List[str]
    groups: List[str]
    start_time: str | None = None
    end_time: str | None = None
    is_overnight: bool | None = None
    is_coed: bool | None = None
    requires_permission: bool = False

class FullActivity(BaseModel):
    activity_id: str
    activity_name: str
    description: str
    location: str
    budget: budget
    total_cost: float | None = None
    actual_cost: float | None = None
    participants_youth_ids: List[str] | None = None
    groups: List[str]
    drivers: List[str]
    date_start: str | None = None
    date_end: str | None = None
    is_overnight: bool | None = None
    is_coed: bool | None = None
    thoughts:str | None = None
    bishop_approval: bool | None = None
    bishop_approval_date: str | None = None
    stake_approval: bool | None = None
    stake_approval_date: str | None = None

class PermissionGiven(BaseModel):
    youth_id: str
    activity_id: str
    granted_at: datetime
    permission_code: str
    granted_ip: str

class ActivityBase(BaseModel):
    activity_name: str
    date_start: datetime
    date_end: datetime
    drivers: List[str]
    description: str
    groups: List[str]
    requires_permission: bool = False
    location: str

class AdminUser(BaseModel):
    username: str
    password: str
    role: str
    org_group:str

class UserReturnModel(BaseModel):
    user_id: str

class InterestSurvey(BaseModel):
    youth_id: str
    interests: List[str]
    org_group:str

class ConcernSurvey(BaseModel):
    concerns: List[str]
    org_group:str

class ReturnGroupActivityList(BaseModel):
    activity_id: str
    activity_name: str
    date_start: datetime
    requires_permission: bool

class YouthNameModel(BaseModel):
    youth_id: str
    first_name: str
    last_name: str

class ActivityInvitees(BaseModel):
    activity_id: str
    youth_ids: List[YouthNameModel]

class ActivityHealthReport(BaseModel):
    activity_id: str
    allergies:list
    dietary_restrictions:list
    medical_conditions:list
    medications:list
    special_notes:list

class ActivityApprovals(BaseModel):
    activity_id: str
    activity_name: str
    activity_start: datetime
    bishop_approval: bool | None = None
    bishop_approval_date: str | None = None
    stake_approval: bool | None = None
    stake_approval_date: str | None = None
    groups: List[str]
    total_youth:int
    total_youth_permission:int
    youth_approvals: List[dict] | None = None


class PersonalGoal(BaseModel):
    youth_id: str
    goal_area: Literal["physical", "social", "intellectual", "spiritual"]
    goal_name: str
    goal_description: str
    target_date: datetime
    status: Literal["Not Started", "In Progress", "Completed", "Canceled"] = "Not Started"
    progress_notes: Optional[List[str]] = None
    completed: bool = False