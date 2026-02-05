"""
Job Model - ORM for MongoDB
Tracks job-level metadata and processing status
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, handler):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator, _handler):
        return {"type": "string"}


class JobStatus(str, Enum):
    """Job processing status"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobBase(BaseModel):
    """Base Job schema"""
    pass


class JobCreate(BaseModel):
    """Schema for creating a new job"""
    total_articles: int = Field(..., ge=1, description="Total number of articles in job")
    new_articles: int = Field(default=0, ge=0, description="Number of new articles to scrape")
    cached_articles: int = Field(default=0, ge=0, description="Number of cached articles")
    article_ids: List[str] = Field(default_factory=list, description="List of article IDs in the job")


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    status: Optional[JobStatus] = None
    completed_count: Optional[int] = Field(None, ge=0)
    failed_count: Optional[int] = Field(None, ge=0)
    article_ids: Optional[List[str]] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(use_enum_values=True)


class Job(JobBase):
    """
    Complete Job model for database storage
    Represents a job in the Jobs collection
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id", description="MongoDB ObjectId")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    total_articles: int = Field(..., ge=1, description="Total number of articles in this job")
    new_articles: int = Field(default=0, ge=0, description="Number of new articles to scrape")
    cached_articles: int = Field(default=0, ge=0, description="Number of articles reused from cache")
    completed_count: int = Field(default=0, ge=0, description="Number of articles successfully processed")
    failed_count: int = Field(default=0, ge=0, description="Number of articles that failed")
    article_ids: List[str] = Field(default_factory=list, description="List of article IDs belonging to this job")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When job was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When job was last updated")
    completed_at: Optional[datetime] = Field(None, description="When job was completed")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "status": "COMPLETED",
                "total_articles": 10,
                "new_articles": 7,
                "cached_articles": 3,
                "completed_count": 9,
                "failed_count": 1,
                "article_ids": ["art_001", "art_002", "art_003"],
                "created_at": "2024-02-04T10:30:00Z",
                "updated_at": "2024-02-04T10:35:00Z",
                "completed_at": "2024-02-04T10:35:00Z"
            }
        }
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "Job":
        """Create Job instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return cls(**data)
    
    @property
    def pending_count(self) -> int:
        """Calculate number of pending articles"""
        return self.total_articles - self.completed_count - self.failed_count


class JobInDB(Job):
    """Job model as stored in database (with guaranteed _id)"""
    id: PyObjectId = Field(..., alias="_id")


class JobSubmitResponse(BaseModel):
    """Response schema for job submission"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    total_articles: int = Field(..., description="Total articles in job")
    new_articles: int = Field(..., description="New articles to scrape")
    cached_articles: int = Field(..., description="Cached articles reused")
    message: str = Field(default="Job submitted successfully", description="Status message")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "job_id": "job_123abc",
                "status": "PENDING",
                "total_articles": 10,
                "new_articles": 7,
                "cached_articles": 3,
                "message": "Job submitted successfully"
            }
        }
    )


class JobStatusResponse(BaseModel):
    """Response schema for job status check"""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    total_articles: int = Field(..., description="Total articles")
    completed: int = Field(..., description="Completed articles")
    failed: int = Field(..., description="Failed articles")
    pending: int = Field(..., description="Pending articles")
    created_at: datetime = Field(..., description="Job creation time")
    updated_at: datetime = Field(..., description="Last update time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "job_id": "job_123abc",
                "status": "IN_PROGRESS",
                "total_articles": 10,
                "completed": 8,
                "failed": 1,
                "pending": 1,
                "created_at": "2024-02-04T10:30:00Z",
                "updated_at": "2024-02-04T10:35:00Z",
                "completed_at": None
            }
        }
    )


class JobResultsResponse(BaseModel):
    """Response schema for job results"""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    total_articles: int = Field(..., description="Total articles")
    successful: int = Field(..., description="Successfully scraped articles")
    failed: int = Field(..., description="Failed articles")
    results: List[dict] = Field(default_factory=list, description="Article results")
    failed_articles: List[dict] = Field(default_factory=list, description="Failed article details")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "job_id": "job_123abc",
                "status": "COMPLETED",
                "total_articles": 10,
                "successful": 9,
                "failed": 1,
                "results": [
                    {
                        "article_id": "art_001",
                        "url": "https://example.com/article1",
                        "source": "TechNews",
                        "category": "AI",
                        "title": "Understanding Large Language Models",
                        "content": "Full scraped article content here...",
                        "scraped_at": "2024-02-04T10:32:00Z",
                        "cached": False
                    }
                ],
                "failed_articles": [
                    {
                        "url": "https://example.com/article5",
                        "error": "404 Not Found",
                        "attempted_at": "2024-02-04T10:33:00Z"
                    }
                ]
            }
        }
    )