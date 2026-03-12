from app.extensions import db 
from datetime import datetime, timezone

# from sqlalchemy import Enum as SAEnum 
# from sqlalchemy import Boolean
from enum import Enum

class Status(Enum):
     ACTIVE = "active"
     DISABLED = "disabled"
     LOCKED = "locked"

class UserType(Enum):
     GUEST = "guest"
     PERMANENT = "permanent"

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.String(40), primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default= lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default= lambda: datetime.now(timezone.utc), onupdate= lambda: datetime.now(timezone.utc))
    status = db.Column(db.Enum(Status,name="status_enum"), nullable=False, default = Status("active"))
    mfa_enabled = db.Column(db.Boolean,default=False,nullable = False)
    guest_user_session_id = db.Column(db.String(40), unique=True,nullable=False)
#     user_type = db.Column(db.Enum())


