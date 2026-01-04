import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
from datetime import datetime
from app.config import settings
from app.models import PlatformEnum, Video
import logging

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsService:
    """Service for reading/writing to Google Sheets"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Google Sheets client with service account"""
        try:
            creds = Credentials.from_service_account_file(
                settings.google_service_account_file,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {str(e)}")
            self.client = None
    
    def get_or_create_worksheet(
        self,
        sheet_id: str,
        worksheet_name: str,
        headers: List[str]
    ) -> gspread.Worksheet:
        """Get existing worksheet or create new one with headers"""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            
            # Try to get existing worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                logger.info(f"Found existing worksheet: {worksheet_name}")
            except gspread.WorksheetNotFound:
                # Create new worksheet
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,
                    cols=len(headers)
                )
                # Add headers
                worksheet.update('A1', [headers])
                # Format headers (bold)
                worksheet.format('A1:Z1', {'textFormat': {'bold': True}})
                logger.info(f"Created new worksheet: {worksheet_name}")
            
            return worksheet
            
        except Exception as e:
            logger.error(f"Failed to get/create worksheet: {str(e)}")
            raise
    
    def setup_sheet_for_user(self, sheet_id: str) -> Dict[str, bool]:
        """
        Setup sheet structure for a new user
        Creates TikTok and Instagram tabs with proper headers
        """
        headers = [
            "Date Scraped",
            "Keyword",
            "Video URL",
            "Author",
            "Description",
            "Likes",
            "Comments",
            "Shares",
            "Views",
            "Transcription",
            "Transcription Status"
        ]
        
        results = {}
        
        try:
            # Create TikTok worksheet
            self.get_or_create_worksheet(sheet_id, "TikTok", headers)
            results["tiktok"] = True
        except Exception as e:
            logger.error(f"Failed to create TikTok worksheet: {str(e)}")
            results["tiktok"] = False
        
        try:
            # Create Instagram worksheet
            self.get_or_create_worksheet(sheet_id, "Instagram", headers)
            results["instagram"] = True
        except Exception as e:
            logger.error(f"Failed to create Instagram worksheet: {str(e)}")
            results["instagram"] = False
        
        return results
    
    def add_video_to_sheet(
        self,
        sheet_id: str,
        video: Video,
        keyword: str
    ) -> bool:
        """Add a single video entry to the appropriate worksheet"""
        try:
            # Determine worksheet based on platform
            worksheet_name = video.platform.value.capitalize()
            
            spreadsheet = self.client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Prepare row data
            row = [
                video.scraped_at.strftime("%Y-%m-%d %H:%M") if video.scraped_at else "",
                keyword,
                video.video_url,
                video.author_username or "",
                (video.description[:200] + "...") if video.description and len(video.description) > 200 else (video.description or ""),
                video.likes,
                video.comments,
                video.shares,
                video.views,
                video.transcription or "",
                video.transcription_status
            ]
            
            # Append row
            worksheet.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"Added video to sheet: {video.video_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add video to sheet: {str(e)}")
            return False
    
    def update_transcription_in_sheet(
        self,
        sheet_id: str,
        video_url: str,
        platform: PlatformEnum,
        transcription: str,
        status: str = "completed"
    ) -> bool:
        """Update transcription for an existing video entry"""
        try:
            worksheet_name = platform.value.capitalize()
            spreadsheet = self.client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Find the row with this video URL (column C)
            cell = worksheet.find(video_url)
            if cell:
                row_num = cell.row
                # Update transcription (column J) and status (column K)
                worksheet.update(f'J{row_num}', [[transcription]])
                worksheet.update(f'K{row_num}', [[status]])
                logger.info(f"Updated transcription in sheet for: {video_url}")
                return True
            else:
                logger.warning(f"Video URL not found in sheet: {video_url}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update transcription in sheet: {str(e)}")
            return False
    
    def add_videos_batch(
        self,
        sheet_id: str,
        videos: List[Dict],
        platform: PlatformEnum,
        keyword: str
    ) -> int:
        """Add multiple videos to sheet in batch"""
        try:
            worksheet_name = platform.value.capitalize()
            spreadsheet = self.client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Prepare all rows
            rows = []
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            
            for video in videos:
                description = video.get("description", "") or ""
                if len(description) > 200:
                    description = description[:200] + "..."
                
                row = [
                    now,
                    keyword,
                    video.get("video_url", ""),
                    video.get("author_username", ""),
                    description,
                    video.get("likes", 0),
                    video.get("comments", 0),
                    video.get("shares", 0),
                    video.get("views", 0),
                    "",  # Transcription (empty initially)
                    "pending"  # Transcription status
                ]
                rows.append(row)
            
            # Batch append
            if rows:
                worksheet.append_rows(rows, value_input_option='USER_ENTERED')
                logger.info(f"Added {len(rows)} videos to {worksheet_name} sheet")
            
            return len(rows)
            
        except Exception as e:
            logger.error(f"Failed to batch add videos: {str(e)}")
            return 0
    
    def verify_sheet_access(self, sheet_id: str) -> Dict:
        """Verify we can access the sheet and return info"""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            return {
                "success": True,
                "title": spreadsheet.title,
                "worksheets": [ws.title for ws in spreadsheet.worksheets()]
            }
        except gspread.SpreadsheetNotFound:
            return {"success": False, "error": "Spreadsheet not found"}
        except gspread.exceptions.APIError as e:
            return {"success": False, "error": f"API Error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
sheets_service = GoogleSheetsService()
