import os
import tempfile
import logging
from typing import Optional
from faster_whisper import WhisperModel
import yt_dlp

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_whisper_model: Optional[WhisperModel] = None


def get_whisper_model() -> WhisperModel:
    """Get or initialize Whisper model (singleton pattern)"""
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Faster-Whisper model...")
        # Use "base" for speed, "medium" or "large-v2" for accuracy
        # compute_type options: "int8" (fastest), "float16" (GPU), "float32" (CPU accurate)
        _whisper_model = WhisperModel(
            "base",
            device="cpu",  # Change to "cuda" if you have GPU
            compute_type="int8"
        )
        logger.info("Whisper model loaded successfully")
    return _whisper_model


class TranscriptionService:
    """Service for downloading and transcribing social media videos"""
    
    def __init__(self):
        self.model = get_whisper_model()
        
        # yt-dlp options for downloading audio
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def download_audio(self, video_url: str, output_path: str) -> str:
        """
        Download audio from video URL
        
        Returns path to downloaded audio file
        """
        try:
            ydl_opts = {
                **self.ydl_opts,
                'outtmpl': output_path,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading audio from: {video_url}")
                ydl.download([video_url])
            
            # yt-dlp adds extension
            audio_path = output_path + ".mp3"
            if os.path.exists(audio_path):
                return audio_path
            
            # Sometimes it keeps original format
            for ext in ['.mp3', '.m4a', '.webm', '.mp4']:
                potential_path = output_path + ext
                if os.path.exists(potential_path):
                    return potential_path
            
            raise FileNotFoundError(f"Downloaded audio file not found at {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to download audio from {video_url}: {str(e)}")
            raise
    
    def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio file using Faster-Whisper
        
        Returns transcription text
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")
            
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language=None,  # Auto-detect language
                vad_filter=True,  # Filter out silence
            )
            
            # Combine all segments into full transcription
            transcription = " ".join([segment.text.strip() for segment in segments])
            
            logger.info(f"Transcription complete. Detected language: {info.language}")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"Failed to transcribe {audio_path}: {str(e)}")
            raise
    
    async def transcribe_video(self, video_url: str) -> str:
        """
        Full pipeline: download video audio and transcribe
        
        Returns transcription text
        """
        temp_dir = tempfile.mkdtemp()
        audio_path = None
        
        try:
            # Download audio
            output_path = os.path.join(temp_dir, "audio")
            audio_path = self.download_audio(video_url, output_path)
            
            # Transcribe
            transcription = self.transcribe_audio(audio_path)
            
            return transcription
            
        finally:
            # Cleanup temp files
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
    
    def transcribe_video_sync(self, video_url: str) -> str:
        """
        Synchronous version for use in Celery workers
        """
        temp_dir = tempfile.mkdtemp()
        audio_path = None
        
        try:
            output_path = os.path.join(temp_dir, "audio")
            audio_path = self.download_audio(video_url, output_path)
            transcription = self.transcribe_audio(audio_path)
            return transcription
            
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except OSError:
                pass  # Directory not empty, ignore


# Singleton instance
transcription_service = TranscriptionService()
