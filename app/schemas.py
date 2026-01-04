from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import PlatformEnum, JobStatusEnum


# ============ Auth Schemas ============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    company_name: Optional[str]
    is_active: bool
    is_admin: bool
    google_sheet_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ============ Keyword Schemas ============

class KeywordCreate(BaseModel):
    keyword: str
    platform: PlatformEnum
    results_per_run: int = 10


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    platform: Optional[PlatformEnum] = None
    is_active: Optional[bool] = None
    results_per_run: Optional[int] = None


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    platform: PlatformEnum
    is_active: bool
    results_per_run: int
    created_at: datetime

    class Config:
        from_attributes = True


class KeywordBulkCreate(BaseModel):
    keywords: List[str]
    platform: PlatformEnum
    results_per_run: int = 10


# ============ Video Schemas ============

class VideoResponse(BaseModel):
    id: int
    platform: PlatformEnum
    video_url: str
    video_id: Optional[str]
    author_username: Optional[str]
    author_name: Optional[str]
    description: Optional[str]
    likes: int
    comments: int
    shares: int
    views: int
    transcription: Optional[str]
    transcription_status: str
    posted_at: Optional[datetime]
    scraped_at: datetime

    class Config:
        from_attributes = True


class VideoWithKeyword(VideoResponse):
    keyword: KeywordResponse


# ============ Job Schemas ============

class JobResponse(BaseModel):
    id: int
    status: JobStatusEnum
    platform: Optional[PlatformEnum]
    keywords_processed: int
    videos_found: int
    videos_transcribed: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    platform: Optional[PlatformEnum] = None  # None = all platforms


# ============ Settings Schemas ============

class UserSettingsUpdate(BaseModel):
    auto_scrape_enabled: Optional[bool] = None
    scrape_frequency: Optional[str] = None
    scrape_time: Optional[str] = None
    min_likes: Optional[int] = None
    min_views: Optional[int] = None
    date_filter: Optional[str] = None
    email_notifications: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    auto_scrape_enabled: bool
    scrape_frequency: str
    scrape_time: str
    min_likes: int
    min_views: int
    date_filter: str
    email_notifications: bool

    class Config:
        from_attributes = True


class GoogleSheetConnect(BaseModel):
    sheet_id: str  # The Google Sheet ID from the URL


# ============ Dashboard Schemas ============

class DashboardStats(BaseModel):
    total_keywords: int
    total_videos: int
    videos_today: int
    pending_transcriptions: int
    last_job_status: Optional[str]
    last_job_time: Optional[datetime]
