from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, Keyword, Video, ScrapeJob, UserSettings, PlatformEnum, JobStatusEnum
from app.schemas import JobResponse, JobCreate, VideoResponse, DashboardStats
from app.auth import get_current_user
from app.services import apify_service, transcription_service, sheets_service

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


async def run_scrape_job(
    job_id: int,
    user_id: int,
    platform: PlatformEnum = None,
    db_session_factory=None
):
    """Background task to run a scrape job"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get job and user
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not job or not user:
            return
        
        # Update job status
        job.status = JobStatusEnum.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Get keywords to process
        keywords_query = db.query(Keyword).filter(
            Keyword.user_id == user_id,
            Keyword.is_active == True
        )
        
        if platform:
            keywords_query = keywords_query.filter(Keyword.platform == platform)
        
        keywords = keywords_query.all()
        
        total_videos = 0
        
        for keyword in keywords:
            try:
                # Scrape videos
                videos_data = await apify_service.scrape_by_platform(
                    platform=keyword.platform,
                    keyword=keyword.keyword,
                    max_results=keyword.results_per_run,
                    min_likes=user_settings.min_likes if user_settings else 1000,
                    date_filter=user_settings.date_filter if user_settings else "this_week"
                )
                
                # Save videos to database
                for video_data in videos_data:
                    # Check for duplicate
                    existing = db.query(Video).filter(
                        Video.video_url == video_data["video_url"]
                    ).first()
                    
                    if existing:
                        continue
                    
                    new_video = Video(
                        user_id=user_id,
                        keyword_id=keyword.id,
                        platform=video_data["platform"],
                        video_url=video_data["video_url"],
                        video_id=video_data.get("video_id"),
                        author_username=video_data.get("author_username"),
                        author_name=video_data.get("author_name"),
                        description=video_data.get("description"),
                        likes=video_data.get("likes", 0),
                        comments=video_data.get("comments", 0),
                        shares=video_data.get("shares", 0),
                        views=video_data.get("views", 0),
                        posted_at=video_data.get("posted_at"),
                        transcription_status="pending"
                    )
                    db.add(new_video)
                    total_videos += 1
                
                # Add to Google Sheet if connected
                if user.google_sheet_id:
                    sheets_service.add_videos_batch(
                        sheet_id=user.google_sheet_id,
                        videos=videos_data,
                        platform=keyword.platform,
                        keyword=keyword.keyword
                    )
                
                job.keywords_processed += 1
                db.commit()
                
            except Exception as e:
                print(f"Error processing keyword {keyword.keyword}: {str(e)}")
                continue
        
        # Update job completion
        job.status = JobStatusEnum.COMPLETED
        job.videos_found = total_videos
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        job.status = JobStatusEnum.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
    
    finally:
        db.close()


async def run_transcription_job(video_id: int):
    """Background task to transcribe a single video"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        
        video.transcription_status = "processing"
        db.commit()
        
        # Run transcription
        transcription = await transcription_service.transcribe_video(video.video_url)
        
        video.transcription = transcription
        video.transcription_status = "completed"
        db.commit()
        
        # Update Google Sheet if user has one connected
        user = db.query(User).filter(User.id == video.user_id).first()
        if user and user.google_sheet_id:
            sheets_service.update_transcription_in_sheet(
                sheet_id=user.google_sheet_id,
                video_url=video.video_url,
                platform=video.platform,
                transcription=transcription
            )
        
    except Exception as e:
        video.transcription_status = "failed"
        db.commit()
        print(f"Transcription failed for video {video_id}: {str(e)}")
    
    finally:
        db.close()


@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent jobs for current user"""
    return db.query(ScrapeJob).filter(
        ScrapeJob.user_id == current_user.id
    ).order_by(ScrapeJob.created_at.desc()).limit(limit).all()


@router.post("/scrape", response_model=JobResponse)
async def start_scrape_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new scrape job"""
    # Check for running jobs
    running_job = db.query(ScrapeJob).filter(
        ScrapeJob.user_id == current_user.id,
        ScrapeJob.status == JobStatusEnum.RUNNING
    ).first()
    
    if running_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A job is already running. Please wait for it to complete."
        )
    
    # Create job record
    new_job = ScrapeJob(
        user_id=current_user.id,
        platform=job_data.platform,
        status=JobStatusEnum.PENDING
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Start background task
    background_tasks.add_task(
        run_scrape_job,
        job_id=new_job.id,
        user_id=current_user.id,
        platform=job_data.platform
    )
    
    return new_job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific job"""
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.post("/transcribe/{video_id}")
async def start_transcription(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start transcription for a specific video"""
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.transcription_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription already in progress"
        )
    
    background_tasks.add_task(run_transcription_job, video_id=video.id)
    
    return {"message": "Transcription started", "video_id": video.id}


@router.post("/transcribe-all")
async def transcribe_all_pending(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start transcription for all pending videos"""
    pending_videos = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.transcription_status == "pending"
    ).all()
    
    for video in pending_videos:
        background_tasks.add_task(run_transcription_job, video_id=video.id)
    
    return {"message": f"Started transcription for {len(pending_videos)} videos"}


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics"""
    from datetime import date
    
    total_keywords = db.query(Keyword).filter(
        Keyword.user_id == current_user.id,
        Keyword.is_active == True
    ).count()
    
    total_videos = db.query(Video).filter(
        Video.user_id == current_user.id
    ).count()
    
    today = date.today()
    videos_today = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.scraped_at >= today
    ).count()
    
    pending_transcriptions = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.transcription_status == "pending"
    ).count()
    
    last_job = db.query(ScrapeJob).filter(
        ScrapeJob.user_id == current_user.id
    ).order_by(ScrapeJob.created_at.desc()).first()
    
    return DashboardStats(
        total_keywords=total_keywords,
        total_videos=total_videos,
        videos_today=videos_today,
        pending_transcriptions=pending_transcriptions,
        last_job_status=last_job.status.value if last_job else None,
        last_job_time=last_job.completed_at if last_job else None
    )
