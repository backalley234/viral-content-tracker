from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Keyword, PlatformEnum
from app.schemas import KeywordCreate, KeywordUpdate, KeywordResponse, KeywordBulkCreate
from app.auth import get_current_user

router = APIRouter(prefix="/api/keywords", tags=["Keywords"])


@router.get("/", response_model=List[KeywordResponse])
async def get_keywords(
    platform: PlatformEnum = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all keywords for current user"""
    query = db.query(Keyword).filter(Keyword.user_id == current_user.id)
    
    if platform:
        query = query.filter(Keyword.platform == platform)
    
    if active_only:
        query = query.filter(Keyword.is_active == True)
    
    return query.all()


@router.post("/", response_model=KeywordResponse)
async def create_keyword(
    keyword_data: KeywordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new keyword to track"""
    # Check for duplicate
    existing = db.query(Keyword).filter(
        Keyword.user_id == current_user.id,
        Keyword.keyword == keyword_data.keyword,
        Keyword.platform == keyword_data.platform
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keyword already exists for this platform"
        )
    
    new_keyword = Keyword(
        user_id=current_user.id,
        keyword=keyword_data.keyword,
        platform=keyword_data.platform,
        results_per_run=keyword_data.results_per_run
    )
    db.add(new_keyword)
    db.commit()
    db.refresh(new_keyword)
    
    return new_keyword


@router.post("/bulk", response_model=List[KeywordResponse])
async def create_keywords_bulk(
    bulk_data: KeywordBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple keywords at once"""
    created = []
    
    for kw in bulk_data.keywords:
        # Skip duplicates
        existing = db.query(Keyword).filter(
            Keyword.user_id == current_user.id,
            Keyword.keyword == kw,
            Keyword.platform == bulk_data.platform
        ).first()
        
        if existing:
            continue
        
        new_keyword = Keyword(
            user_id=current_user.id,
            keyword=kw,
            platform=bulk_data.platform,
            results_per_run=bulk_data.results_per_run
        )
        db.add(new_keyword)
        created.append(new_keyword)
    
    db.commit()
    
    for kw in created:
        db.refresh(kw)
    
    return created


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific keyword"""
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )
    
    return keyword


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    keyword_data: KeywordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a keyword"""
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )
    
    if keyword_data.keyword is not None:
        keyword.keyword = keyword_data.keyword
    if keyword_data.platform is not None:
        keyword.platform = keyword_data.platform
    if keyword_data.is_active is not None:
        keyword.is_active = keyword_data.is_active
    if keyword_data.results_per_run is not None:
        keyword.results_per_run = keyword_data.results_per_run
    
    db.commit()
    db.refresh(keyword)
    
    return keyword


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a keyword"""
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )
    
    db.delete(keyword)
    db.commit()
    
    return {"message": "Keyword deleted"}


# Preset keywords for common industries
PRESET_KEYWORDS = {
    "ai_automation": [
        "AI", "AI Tools", "AI for business", "AI Automation", "AI Workflow",
        "AI Agent", "ChatGPT", "Claude", "N8N", "Vibecoding", "Vibecode",
        "Gemini", "Google AI Studio", "Deepseek", "Manus", "LLM", "Artificial Intelligence"
    ],
    "ecommerce": [
        "dropshipping", "ecommerce", "shopify", "amazon fba", "online store",
        "product sourcing", "retail arbitrage", "print on demand"
    ],
    "real_estate": [
        "real estate investing", "house flipping", "rental property",
        "real estate agent", "property investment", "wholesale real estate"
    ],
    "fitness": [
        "workout", "fitness tips", "gym motivation", "weight loss",
        "muscle building", "home workout", "nutrition tips"
    ],
    "finance": [
        "investing", "stock market", "crypto", "passive income",
        "side hustle", "make money online", "financial freedom"
    ]
}


@router.get("/presets/list")
async def get_preset_industries():
    """Get available preset keyword industries"""
    return {
        "industries": list(PRESET_KEYWORDS.keys()),
        "descriptions": {
            "ai_automation": "AI tools, automation, and coding",
            "ecommerce": "Online selling and dropshipping",
            "real_estate": "Property and real estate investing",
            "fitness": "Health, fitness, and wellness",
            "finance": "Investing and making money"
        }
    }


@router.post("/presets/{industry}", response_model=List[KeywordResponse])
async def load_preset_keywords(
    industry: str,
    platform: PlatformEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Load preset keywords for an industry"""
    if industry not in PRESET_KEYWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown industry. Available: {list(PRESET_KEYWORDS.keys())}"
        )
    
    keywords = PRESET_KEYWORDS[industry]
    created = []
    
    for kw in keywords:
        existing = db.query(Keyword).filter(
            Keyword.user_id == current_user.id,
            Keyword.keyword == kw,
            Keyword.platform == platform
        ).first()
        
        if existing:
            continue
        
        new_keyword = Keyword(
            user_id=current_user.id,
            keyword=kw,
            platform=platform,
            results_per_run=10
        )
        db.add(new_keyword)
        created.append(new_keyword)
    
    db.commit()
    
    for kw in created:
        db.refresh(kw)
    
    return created
