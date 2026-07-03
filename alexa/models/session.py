"""
Session state models for Alexa skill
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ChildInfo:
    """Information about a youth that a parent manages"""
    child_id: str
    child_name: str
    org_group: str
    permission_code: str = ""


@dataclass
class SessionState:
    """Manages session state across Alexa interactions"""
    user_type: Optional[str] = None  # "parent" or "youth"
    permission_code: Optional[str] = None
    jwt_token: Optional[str] = None
    token_expiry: Optional[str] = None  # ISO format datetime string
    pin: Optional[str] = None  # 4-digit PIN for permission grants (parent only)
    selected_child: Optional[ChildInfo] = None  # Currently selected child (parent only)
    children: List[ChildInfo] = field(default_factory=list)  # Available children (parent only)
    org_group: Optional[str] = None
    setup_step: str = "awaiting_user_type"  # Setup progression: awaiting_user_type -> awaiting_permission_code -> awaiting_pin -> complete
    recent_activities: Optional[List[Dict[str, Any]]] = None  # Cache of last activity query
    session_id: Optional[str] = None  # Alexa session ID

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Alexa session attributes"""
        data = {
            "user_type": self.user_type,
            "permission_code": self.permission_code,
            "jwt_token": self.jwt_token,
            "token_expiry": self.token_expiry,
            "pin": self.pin,
            "org_group": self.org_group,
            "setup_step": self.setup_step,
            "recent_activities": self.recent_activities,
            "session_id": self.session_id,
        }
        
        if self.selected_child:
            data["selected_child"] = {
                "child_id": self.selected_child.child_id,
                "child_name": self.selected_child.child_name,
                "org_group": self.selected_child.org_group,
                "permission_code": self.selected_child.permission_code,
            }
        
        if self.children:
            data["children"] = [
                {
                    "child_id": child.child_id,
                    "child_name": child.child_name,
                    "org_group": child.org_group,
                    "permission_code": child.permission_code,
                }
                for child in self.children
            ]
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Reconstruct from Alexa session attributes"""
        selected_child_data = data.get("selected_child")
        selected_child = None
        if selected_child_data:
            selected_child = ChildInfo(**selected_child_data)
        
        children_data = data.get("children", [])
        children = [ChildInfo(**child) for child in children_data]
        
        return cls(
            user_type=data.get("user_type"),
            permission_code=data.get("permission_code"),
            jwt_token=data.get("jwt_token"),
            token_expiry=data.get("token_expiry"),
            pin=data.get("pin"),
            selected_child=selected_child,
            children=children,
            org_group=data.get("org_group"),
            setup_step=data.get("setup_step", "awaiting_user_type"),
            recent_activities=data.get("recent_activities"),
            session_id=data.get("session_id"),
        )

    def is_token_expired(self) -> bool:
        """Check if JWT token is expired or about to expire"""
        if not self.token_expiry:
            return True
        try:
            expiry = datetime.fromisoformat(self.token_expiry)
            return datetime.now() >= expiry
        except (ValueError, TypeError):
            return True

    def is_setup_complete(self) -> bool:
        """Check if user has completed setup"""
        return self.setup_step == "complete"

    def is_parent(self) -> bool:
        """Check if user is a parent"""
        return self.user_type == "parent"

    def is_youth(self) -> bool:
        """Check if user is a youth"""
        return self.user_type == "youth"
