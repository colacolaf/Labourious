from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user, _get_db
from backend.database.models import User
from backend.notifications.models import UserNotificationPreferences

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email_enabled: bool
    sms_enabled: bool
    phone_number: Optional[str]
    notify_on_trade: bool
    notify_on_agent_pause: bool
    notify_on_drawdown: bool
    daily_digest: bool


class PreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    phone_number: Optional[str] = None
    notify_on_trade: Optional[bool] = None
    notify_on_agent_pause: Optional[bool] = None
    notify_on_drawdown: Optional[bool] = None
    daily_digest: Optional[bool] = None


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    prefs = db.query(UserNotificationPreferences).filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    prefs = db.query(UserNotificationPreferences).filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs


@router.post("/test")
def send_test_notification(current_user: User = Depends(get_current_user)):
    """Send test email + SMS to verify notification config."""
    from backend.notifications.triggers import notification_service

    results = {}
    # Test email
    if notification_service.smtp_configured:
        ok = notification_service.send_email(
            to=current_user.email,
            subject="Labourious — Test Notification",
            body="Your notification config is working.",
        )
        results["email"] = "sent" if ok else "failed"
    else:
        results["email"] = "not_configured"

    return results
