from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Dashboard Schemas ---

class DashboardStats(BaseModel):
    total_case: int
    total_exposed: int
    total_detected: int
    total_death: int
    total_injured: int
    total_incident: int
    total_location: int
    total_dalam: int
    jur_labels: List[str]
    jur_counts: List[int]
    loc_labels: List[str] = []
    loc_counts: List[int] = []
    month_labels: List[str]
    month_counts: List[int]
    week_labels: List[str] = []
    week_counts: List[int] = []

# --- Master CRUD Schemas ---

class MasterItemBase(BaseModel):
    name: str

class MasterItemResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# --- User Management Schemas ---

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    designation_id: Optional[int] = None
    post_id: Optional[int] = None
    permission_edit: int = 0
    permission_delete: int = 0

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    first_name: Optional[str]
    designation: Optional[str]
    post: Optional[str]
    mobile: Optional[str]
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class UserPasswordReset(BaseModel):
    new_password: str

# --- SP Authority Schemas ---

class SPAuthorityBase(BaseModel):
    s_name: str
    s_numbers: str
    s_designation: str
    s_email: str

class SPAuthorityCreate(SPAuthorityBase):
    s_password: str

class SPAuthorityResponse(SPAuthorityBase):
    id: int
    s_datetime: datetime

    class Config:
        from_attributes = True

# --- Location Management Schemas ---

class LocationUpdate(BaseModel):
    location_id: int
    locations_value: str

class LocationDelete(BaseModel):
    location_id: int
