"""
Video analysis endpoints
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib
from pathlib import Path

from src.utils.database import get_db_manager
from src.utils.logger import get_logger
from src.config import settings

router = APIRouter()
logger = get_logger("analyze")

# Simple in-memory job registry for analysis tracking
# Note: This is process-local and resets on restart. Replace with DB for durability.
ANALYSIS_JOBS: Dict[str, Dict[str, Any]] = {}

# Pydantic models
class AnalyzeRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    use_cache: bool = Field(default=True, description="Use cached analysis if available")

class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    video_file: str
    analysis_result: Optional[Dict[str, Any]] = None
    from_cache: bool = False

class BatchAnalyzeRequest(BaseModel):
    video_paths: list[str] = Field(..., description="List of video file paths")
    use_cache: bool = Field(default=True, description="Use cached analysis if available")

@router.post("/video", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze a single video file
    
    This endpoint will:
    1. Check if analysis is cached
    2. If not cached, start analysis in background
    3. Return job ID for tracking
    """
    try:
        db = get_db_manager()
        
        # Generate file hash for caching
        video_path = Path(request.video_path)
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Calculate file hash
        file_hash = calculate_file_hash(str(video_path))
        
        # Check cache if enabled
        if request.use_cache:
            cached = await db.get_cached_analysis(file_hash)
            if cached:
                logger.info(f"Using cached analysis for {video_path.name}")
                return AnalyzeResponse(
                    job_id=cached['id'],
                    status="completed",
                    video_file=str(video_path),
                    analysis_result=cached['analysis_result'],
                    from_cache=True
                )
        
        # Create job ID
        import uuid
        job_id = str(uuid.uuid4())

        # Register job as processing
        ANALYSIS_JOBS[job_id] = {
            "status": "processing",
            "video_file": str(video_path),
            "file_hash": file_hash,
        }

        # Start background analysis
        background_tasks.add_task(
            perform_video_analysis,
            job_id=job_id,
            video_path=str(video_path),
            file_hash=file_hash
        )
        
        logger.info(f"Started analysis job {job_id} for {video_path.name}")
        
        return AnalyzeResponse(
            job_id=job_id,
            status="processing",
            video_file=str(video_path),
            from_cache=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}", response_model=AnalyzeResponse)
async def get_analysis_status(job_id: str):
    """Get the status of an analysis job"""
    try:
        job = ANALYSIS_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return AnalyzeResponse(
            job_id=job_id,
            status=job.get("status", "unknown"),
            video_file=job.get("video_file", "unknown"),
            analysis_result=job.get("analysis_result"),
            from_cache=job.get("from_cache", False),
        )
        
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
async def batch_analyze(request: BatchAnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze multiple videos in batch
    
    Returns job IDs for each video
    """
    try:
        jobs = []
        
        for video_path in request.video_paths:
            # Check if file exists
            path = Path(video_path)
            if not path.exists():
                jobs.append({
                    "video_path": video_path,
                    "status": "error",
                    "error": "File not found"
                })
                continue
            
            # Create job
            import uuid
            job_id = str(uuid.uuid4())
            
            # Calculate hash
            file_hash = calculate_file_hash(video_path)
            
            # Start background task
            background_tasks.add_task(
                perform_video_analysis,
                job_id=job_id,
                video_path=video_path,
                file_hash=file_hash
            )
            
            jobs.append({
                "video_path": video_path,
                "job_id": job_id,
                "status": "processing"
            })
        
        logger.info(f"Started batch analysis for {len(jobs)} videos")
        
        return {
            "total_videos": len(request.video_paths),
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def analyze_uploaded_video(
    file: UploadFile = File(...),
    use_cache: bool = True
):
    """
    Analyze an uploaded video file
    
    Saves the file temporarily and starts analysis
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(tuple(f".{ext}" for ext in settings.supported_video_formats)):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {settings.supported_video_formats}"
            )
        
        # Save uploaded file
        temp_path = settings.temp_folder_path / file.filename
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved uploaded file to {temp_path}")
        
        # Start analysis
        request = AnalyzeRequest(
            video_path=str(temp_path),
            use_cache=use_cache
        )
        
        # Use existing analyze endpoint
        from fastapi import BackgroundTasks
        background_tasks = BackgroundTasks()
        result = await analyze_video(request, background_tasks)

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing uploaded video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def perform_video_analysis(job_id: str, video_path: str, file_hash: str):
    """
    Perform actual video analysis (background task)
    
    This would integrate with Gemini Vision API
    """
    try:
        logger.info(f"Starting analysis for job {job_id}")

        # Run real analyzer (falls back to mock internally if not configured)
        from src.analyzers.video_analyzer import get_video_analyzer
        analyzer = get_video_analyzer()

        analysis = await analyzer.analyze_video(video_path)

        # Map fields to cache schema
        analysis_result = {
            "products": [p.get("name") if isinstance(p, dict) else p for p in analysis.get("products", [])],
            "category": analysis.get("category", "unknown"),
            "keywords": analysis.get("keywords", []),
            "confidence": analysis.get("confidence_score", 0.0),
            "tone": analysis.get("mood", "neutral"),
        }

        # Cache the result
        db = get_db_manager()
        await db.cache_analysis(file_hash, {
            "filename": Path(video_path).name,
            "gemini_response": analysis.get("gemini_response"),
            **analysis_result
        })
        
        # Update job registry
        ANALYSIS_JOBS[job_id].update({
            "status": "completed",
            "analysis_result": analysis,
            "from_cache": False,
        })

        logger.info(f"Completed analysis for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in background analysis: {e}")
        if job_id in ANALYSIS_JOBS:
            ANALYSIS_JOBS[job_id].update({
                "status": "failed",
                "error": str(e),
            })
