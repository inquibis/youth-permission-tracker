from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, date
import json
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import JSON


password_hash = Column(String(255))

class ActivityPermission(Base):
    __tablename__ = "activity_permissions"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    signed = Column(Boolean, default=False)
    last_requested_at = Column(DateTime)
    user = relationship("User")
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

class ActivityPermissionMedical(Base):
    __tablename__ = "activity_permissions_medical"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String(50), nullable=False)
    allergies = Column(Text)
    restrictions = Column(Text)
    special_diet = Column(Text)
    prescriptions = Column(Text)
    over_the_counter_drugs = Column(Text)
    chronic_illness = Column(Text)
    surgeries_12mo = Column(Text)
    serious_illnesses = Column(Text)
    comments = Column(Text)
    signature_path = Column(Text)  # or store base64 string
    submitted_at = Column(DateTime, default=datetime.utcnow)
    dl_number = Column(Text)
    pin = Column(Text)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(String(255), nullable=False)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=False)
    drivers = Column(MutableList.as_mutable(JSON), default=[])
    description = Column(Text)
    youth_groups = Column(String(255))
    groups = Column(MutableList.as_mutable(JSON), default=[])


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    guardian_name = Column(String(100))
    guardian_email = Column(String(100))
    guardian_cell = Column(String(20))
    user_email = Column(String(100))
    user_cell = Column(String(20))
    is_active = Column(Boolean, default=True)
    groups = Column(Text)  # store as JSON array

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "guardian_name": self.guardian_name,
            "guardian_email": self.guardian_email,
            "guardian_cell": self.guardian_cell,
            "user_email": self.user_email,
            "user_cell": self.user_cell,
            "is_active": self.is_active,
            "groups": json.loads(self.groups or "[]"),
        }


class PermissionToken(Base):
    __tablename__ = "permission_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_id = Column(Integer, ForeignKey("activities.id"))
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)

    user = relationship("User")
    activity = relationship("Activity")

class ActivityInfo(Base):
    __tablename__ = "activity_info"

    id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(String)
    description = Column(String)
    date_start = Column(Date)
    date_end = Column(Date)
    purpose = Column(String)

    # Optional - normalize relations
    budgets = relationship("ActivityBudget", back_populates="activity", cascade="all, delete-orphan")
    drivers = relationship("ActivityDriver", back_populates="activity", cascade="all, delete-orphan")
    groups = relationship("ActivityGroup", back_populates="activity", cascade="all, delete-orphan")

class ActivityBudget(Base):
    __tablename__ = "activity_budget"
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String)
    amount = Column(Float)
    activity_id = Column(Integer, ForeignKey("activity_info.id"))
    activity = relationship("ActivityInfo", back_populates="budgets")

class ActivityDriver(Base):
    __tablename__ = "activity_driver"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    activity_id = Column(Integer, ForeignKey("activity_info.id"))
    activity = relationship("ActivityInfo", back_populates="drivers")

class ActivityGroup(Base):
    __tablename__ = "activity_group"
    id = Column(Integer, primary_key=True, index=True)
    group = Column(String)
    activity_id = Column(Integer, ForeignKey("activity_info.id"))
    activity = relationship("ActivityInfo", back_populates="groups")

class SelectedActivity(Base):
    __tablename__ = "selectedactivities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    activity_name = Column(String, nullable=False)

class IdentifiedNeed(Base):
    __tablename__ = "identifiedneeds"

    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String, nullable=False)
    need = Column(String, nullable=False)
    priority = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)