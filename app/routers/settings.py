from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserSettings
from app.schemas import UserSettingsUpdate, UserSettingsResponse, GoogleSheetConnect
from app.auth import get_current_user
from app.services import sheets_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("/", response_model=UserSettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Create default settings
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    # Update fields
    update_data = settings_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/connect-sheet")
async def connect_google_sheet(
    sheet_data: GoogleSheetConnect,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Connect a Google Sheet to user account"""
    # Verify we can access the sheet
    result = sheets_service.verify_sheet_access(sheet_data.sheet_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot access sheet: {result.get('error', 'Unknown error')}"
        )
    
    # Setup sheet structure
    setup_result = sheets_service.setup_sheet_for_user(sheet_data.sheet_id)
    
    # Save sheet ID to user
    current_user.google_sheet_id = sheet_data.sheet_id
    db.commit()
    
    return {
        "message": "Google Sheet connected successfully",
        "sheet_title": result.get("title"),
        "worksheets_created": setup_result
    }


@router.delete("/disconnect-sheet")
async def disconnect_google_sheet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect Google Sheet from user account"""
    current_user.google_sheet_id = None
    db.commit()
    
    return {"message": "Google Sheet disconnected"}


@router.get("/sheet-status")
async def get_sheet_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get connected Google Sheet status"""
    if not current_user.google_sheet_id:
        return {
            "connected": False,
            "sheet_id": None,
            "sheet_info": None
        }
    
    # Verify sheet is still accessible
    result = sheets_service.verify_sheet_access(current_user.google_sheet_id)
    
    return {
        "connected": result["success"],
        "sheet_id": current_user.google_sheet_id,
        "sheet_info": result if result["success"] else None,
        "error": result.get("error") if not result["success"] else None
    }
