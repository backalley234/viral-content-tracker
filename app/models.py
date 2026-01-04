from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class PlatformEnum(str, enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class JobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Google Sheets connection
    google_sheet_id = Column(String(255), nullable=True)
    
    # Relationships
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("ScrapeJob", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    results_per_run = Column(Integer, default=10)  # How many videos to fetch per keyword
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="keywords")
    videos = relationship("Video", back_populates="keyword", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    
    # Video info
    platform = Column(Enum(PlatformEnum), nullable=False)
    video_url = Column(String(500), nullable=False, unique=True)
    video_id = Column(String(255), nullable=True)  # Platform-specific ID
    author_username = Column(String(255), nullable=True)
    author_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views = Column(Integer, default=0)
    
    # Transcription
    transcription = Column(Text, nullable=True)
    transcription_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Metadata
    posted_at = Column(DateTime(timezone=True), nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="videos")
    keyword = relationship("Keyword", back_populates="videos")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(Enum(JobStatusEnum), default=JobStatusEnum.PENDING)
    platform = Column(Enum(PlatformEnum), nullable=True)  # Null means all platforms
    
    # Job details
    keywords_processed = Column(Integer, default=0)
    videos_found = Column(Integer, default=0)
    videos_transcribed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jobs")


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Scraping settings
    auto_scrape_enabled = Column(Boolean, default=True)
    scrape_frequency = Column(String(50), default="daily")  # daily, weekly
    scrape_time = Column(String(10), default="09:00")  # HH:MM format
    
    # Filter settings
    min_likes = Column(Integer, default=1000)
    min_views = Column(Integer, default=5000)
    date_filter = Column(String(50), default="this_week")  # this_week, this_month
    
    # Notification settings
    email_notifications = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
