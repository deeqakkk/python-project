from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    STAFF = 'staff'
    SUPERVISOR = 'supervisor'
    ADMIN = 'admin'

from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50) # type: ignore
    email: EmailStr

class UserCreate(UserBase):
    password: constr(min_length=8) # type: ignore

class UserInDB(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attribute = True  # Updated from from_attributes in newer Pydantic
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RoleBase(BaseModel):
    name: UserRole
    description: Optional[str] = None

class RoleInDB(RoleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PermissionBase(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None

class PermissionInDB(PermissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }