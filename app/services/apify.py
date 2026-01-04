from apify_client import ApifyClient
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.models import PlatformEnum
import logging

logger = logging.getLogger(__name__)


class ApifyService:
    """Service for scraping TikTok and Instagram using Apify actors"""
    
    def __init__(self):
        self.client = ApifyClient(settings.apify_api_token)
        
        # Apify actor IDs (these are popular, maintained actors)
        self.actors = {
            PlatformEnum.TIKTOK: "clockworks/free-tiktok-scraper",
            PlatformEnum.INSTAGRAM: "apify/instagram-scraper",
        }
    
    def _get_date_filter(self, date_filter: str) -> datetime:
        """Convert date filter string to datetime"""
        now = datetime.utcnow()
        if date_filter == "today":
            return now - timedelta(days=1)
        elif date_filter == "this_week":
            return now - timedelta(days=7)
        elif date_filter == "this_month":
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=7)  # Default to this week
    
    async def scrape_tiktok(
        self,
        keyword: str,
        max_results: int = 10,
        min_likes: int = 1000,
        date_filter: str = "this_week"
    ) -> List[Dict]:
        """
        Scrape TikTok videos by keyword
        
        Returns list of video data dictionaries
        """
        try:
            run_input = {
                "searchQueries": [keyword],
                "resultsPerPage": max_results * 2,  # Get extra to filter
                "searchSection": "video",
                "maxProfilesPerQuery": 0,
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
            }
            
            logger.info(f"Starting TikTok scrape for keyword: {keyword}")
            
            # Run the actor
            run = self.client.actor(self.actors[PlatformEnum.TIKTOK]).call(run_input=run_input)
            
            # Get results from dataset
            videos = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Filter by minimum likes
                if item.get("diggCount", 0) >= min_likes:
                    video_data = {
                        "platform": PlatformEnum.TIKTOK,
                        "video_url": item.get("webVideoUrl") or f"https://www.tiktok.com/@{item.get('authorMeta', {}).get('name')}/video/{item.get('id')}",
                        "video_id": item.get("id"),
                        "author_username": item.get("authorMeta", {}).get("name"),
                        "author_name": item.get("authorMeta", {}).get("nickName"),
                        "description": item.get("text"),
                        "likes": item.get("diggCount", 0),
                        "comments": item.get("commentCount", 0),
                        "shares": item.get("shareCount", 0),
                        "views": item.get("playCount", 0),
                        "posted_at": datetime.fromtimestamp(item.get("createTime", 0)) if item.get("createTime") else None,
                    }
                    videos.append(video_data)
            
            # Sort by likes and take top results
            videos.sort(key=lambda x: x["likes"], reverse=True)
            videos = videos[:max_results]
            
            logger.info(f"TikTok scrape complete. Found {len(videos)} videos for '{keyword}'")
            return videos
            
        except Exception as e:
            logger.error(f"TikTok scrape failed for '{keyword}': {str(e)}")
            raise
    
    async def scrape_instagram(
        self,
        keyword: str,
        max_results: int = 10,
        min_likes: int = 1000,
        date_filter: str = "this_week"
    ) -> List[Dict]:
        """
        Scrape Instagram reels/videos by hashtag
        
        Note: Instagram search is hashtag-based, so we convert keyword to hashtag
        """
        try:
            # Convert keyword to hashtag format
            hashtag = keyword.replace(" ", "").lower()
            
            run_input = {
                "hashtags": [hashtag],
                "resultsLimit": max_results * 2,
                "resultsType": "posts",
                "searchType": "hashtag",
            }
            
            logger.info(f"Starting Instagram scrape for hashtag: #{hashtag}")
            
            # Run the actor
            run = self.client.actor(self.actors[PlatformEnum.INSTAGRAM]).call(run_input=run_input)
            
            # Get results from dataset
            videos = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Only get video posts (reels)
                if item.get("type") != "Video" and item.get("videoUrl") is None:
                    continue
                    
                # Filter by minimum likes
                if item.get("likesCount", 0) >= min_likes:
                    video_data = {
                        "platform": PlatformEnum.INSTAGRAM,
                        "video_url": item.get("url") or item.get("videoUrl"),
                        "video_id": item.get("id"),
                        "author_username": item.get("ownerUsername"),
                        "author_name": item.get("ownerFullName"),
                        "description": item.get("caption"),
                        "likes": item.get("likesCount", 0),
                        "comments": item.get("commentsCount", 0),
                        "shares": 0,  # Instagram doesn't expose share count
                        "views": item.get("videoViewCount", 0),
                        "posted_at": datetime.fromisoformat(item.get("timestamp").replace("Z", "+00:00")) if item.get("timestamp") else None,
                    }
                    videos.append(video_data)
            
            # Sort by likes and take top results
            videos.sort(key=lambda x: x["likes"], reverse=True)
            videos = videos[:max_results]
            
            logger.info(f"Instagram scrape complete. Found {len(videos)} videos for '#{hashtag}'")
            return videos
            
        except Exception as e:
            logger.error(f"Instagram scrape failed for '{keyword}': {str(e)}")
            raise
    
    async def scrape_by_platform(
        self,
        platform: PlatformEnum,
        keyword: str,
        max_results: int = 10,
        min_likes: int = 1000,
        date_filter: str = "this_week"
    ) -> List[Dict]:
        """Route to correct scraper based on platform"""
        if platform == PlatformEnum.TIKTOK:
            return await self.scrape_tiktok(keyword, max_results, min_likes, date_filter)
        elif platform == PlatformEnum.INSTAGRAM:
            return await self.scrape_instagram(keyword, max_results, min_likes, date_filter)
        else:
            raise ValueError(f"Unsupported platform: {platform}")


# Singleton instance
apify_service = ApifyService()
