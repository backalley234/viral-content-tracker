from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, Video, Keyword, PlatformEnum
from app.schemas import VideoResponse, VideoWithKeyword
from app.auth import get_current_user

router = APIRouter(prefix="/api/videos", tags=["Videos"])


@router.get("/", response_model=List[VideoResponse])
async def get_videos(
    platform: Optional[PlatformEnum] = None,
    keyword_id: Optional[int] = None,
    transcription_status: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get videos with optional filters"""
    query = db.query(Video).filter(Video.user_id == current_user.id)
    
    if platform:
        query = query.filter(Video.platform == platform)
    
    if keyword_id:
        query = query.filter(Video.keyword_id == keyword_id)
    
    if transcription_status:
        query = query.filter(Video.transcription_status == transcription_status)
    
    # Filter by date
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(Video.scraped_at >= since)
    
    # Order by engagement (likes)
    query = query.order_by(Video.likes.desc())
    
    return query.offset(offset).limit(limit).all()


@router.get("/recent", response_model=List[VideoResponse])
async def get_recent_videos(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get most recently scraped videos"""
    return db.query(Video).filter(
        Video.user_id == current_user.id
    ).order_by(Video.scraped_at.desc()).limit(limit).all()


@router.get("/top", response_model=List[VideoResponse])
async def get_top_videos(
    platform: Optional[PlatformEnum] = None,
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top performing videos by engagement"""
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.scraped_at >= since
    )
    
    if platform:
        query = query.filter(Video.platform == platform)
    
    return query.order_by(Video.likes.desc()).limit(limit).all()


@router.get("/by-keyword/{keyword_id}", response_model=List[VideoResponse])
async def get_videos_by_keyword(
    keyword_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all videos for a specific keyword"""
    # Verify keyword belongs to user
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )
    
    return db.query(Video).filter(
        Video.keyword_id == keyword_id
    ).order_by(Video.likes.desc()).limit(limit).all()


@router.get("/pending-transcription", response_model=List[VideoResponse])
async def get_pending_transcriptions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get videos pending transcription"""
    return db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.transcription_status == "pending"
    ).order_by(Video.scraped_at.desc()).limit(limit).all()


@router.get("/search", response_model=List[VideoResponse])
async def search_videos(
    q: str = Query(..., min_length=2),
    search_transcripts: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search videos by description or transcription"""
    query = db.query(Video).filter(Video.user_id == current_user.id)
    
    search_term = f"%{q}%"
    
    if search_transcripts:
        query = query.filter(
            (Video.description.ilike(search_term)) |
            (Video.transcription.ilike(search_term))
        )
    else:
        query = query.filter(Video.description.ilike(search_term))
    
    return query.order_by(Video.likes.desc()).limit(limit).all()


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific video"""
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return video


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a video"""
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    db.delete(video)
    db.commit()
    
    return {"message": "Video deleted"}


@router.get("/stats/by-platform")
async def get_stats_by_platform(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get video statistics grouped by platform"""
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    stats = db.query(
        Video.platform,
        func.count(Video.id).label("total_videos"),
        func.sum(Video.likes).label("total_likes"),
        func.avg(Video.likes).label("avg_likes"),
        func.sum(Video.views).label("total_views")
    ).filter(
        Video.user_id == current_user.id,
        Video.scraped_at >= since
    ).group_by(Video.platform).all()
    
    return [
        {
            "platform": stat.platform.value,
            "total_videos": stat.total_videos,
            "total_likes": int(stat.total_likes or 0),
            "avg_likes": int(stat.avg_likes or 0),
            "total_views": int(stat.total_views or 0)
        }
        for stat in stats
    ]


@router.get("/stats/by-keyword")
async def get_stats_by_keyword(
    platform: Optional[PlatformEnum] = None,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get video statistics grouped by keyword"""
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(
        Keyword.keyword,
        Keyword.platform,
        func.count(Video.id).label("total_videos"),
        func.sum(Video.likes).label("total_likes"),
        func.avg(Video.likes).label("avg_likes")
    ).join(Video).filter(
        Keyword.user_id == current_user.id,
        Video.scraped_at >= since
    )
    
    if platform:
        query = query.filter(Keyword.platform == platform)
    
    stats = query.group_by(Keyword.id).order_by(func.sum(Video.likes).desc()).all()
    
    return [
        {
            "keyword": stat.keyword,
            "platform": stat.platform.value,
            "total_videos": stat.total_videos,
            "total_likes": int(stat.total_likes or 0),
            "avg_likes": int(stat.avg_likes or 0)
        }
        for stat in stats
    ]
