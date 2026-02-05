"""
Article Model - ORM for MongoDB
Stores scraped article content (reusable across multiple jobs)
"""
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
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


class ArticleStatus(str, Enum):
    """Article processing status"""
    PENDING = "PENDING"
    SCRAPING = "SCRAPING"
    SCRAPED = "SCRAPED"
    FAILED = "FAILED"


class ArticleBase(BaseModel):
    """Base Article schema with common fields"""
    url: HttpUrl
    source: str = Field(..., min_length=1, max_length=100, description="Source of the article (e.g., TechNews)")
    category: str = Field(..., min_length=1, max_length=50, description="Article category (e.g., AI, ML)")
    priority: str = Field(..., min_length=3, max_length=6, description="Priority level (high, medium, low)")


class ArticleCreate(ArticleBase):
    """Schema for creating a new article"""
    pass


class ArticleUpdate(BaseModel):
    """Schema for updating an article"""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    status: Optional[ArticleStatus] = None
    error_message: Optional[str] = None
    scraped_at: Optional[datetime] = None
    
    model_config = ConfigDict(use_enum_values=True)


class Article(ArticleBase):
    """
    Complete Article model for database storage
    Represents an article in the Articles collection
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id", description="MongoDB ObjectId")
    title: Optional[str] = Field(None, max_length=500, description="Article title")
    content: Optional[str] = Field(None, description="Full article content/text")
    status: ArticleStatus = Field(default=ArticleStatus.PENDING, description="Current processing status")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")
    scraped_at: Optional[datetime] = Field(None, description="Timestamp when article was successfully scraped")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when article was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when article was last updated")
    reference_count: int = Field(default=0, ge=0, description="Number of jobs referencing this article")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "url": "https://example.com/article1",
                "source": "TechNews",
                "category": "AI",
                "priority": 1,
                "title": "Understanding Large Language Models",
                "content": "Full article content here...",
                "status": "SCRAPED",
                "error_message": None,
                "scraped_at": "2024-02-04T10:32:00Z",
                "created_at": "2024-02-04T10:30:00Z",
                "updated_at": "2024-02-04T10:32:00Z",
                "reference_count": 3
            }
        }
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion"""
        data = self.model_dump(by_alias=True, exclude_unset=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "Article":
        """Create Article instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return cls(**data)


class ArticleInDB(Article):
    """Article model as stored in database (with guaranteed _id)"""
    id: PyObjectId = Field(..., alias="_id")


class ArticleResponse(BaseModel):
    """Schema for article response in API"""
    article_id: str = Field(..., description="Article ID")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="Article source")
    category: str = Field(..., description="Article category")
    title: Optional[str] = Field(None, description="Article title")
    content: Optional[str] = Field(None, description="Article content")
    scraped_at: Optional[datetime] = Field(None, description="When article was scraped")
    cached: bool = Field(..., description="Whether article was cached (reused)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "article_id": "art_001",
                "url": "https://example.com/article1",
                "source": "TechNews",
                "category": "AI",
                "title": "Understanding Large Language Models",
                "content": "Full scraped article content here...",
                "scraped_at": "2024-02-04T10:32:00Z",
                "cached": False
            }
        }
    )


class FailedArticleResponse(BaseModel):
    """Schema for failed article in API response"""
    url: str = Field(..., description="Article URL that failed")
    error: str = Field(..., description="Error message")
    attempted_at: datetime = Field(..., description="When scraping was attempted")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/article5",
                "error": "404 Not Found",
                "attempted_at": "2024-02-04T10:33:00Z"
            }
        }
    )


class ArticleTask(BaseModel):
    """Schema for article scraping task in Redis queue"""
    task_id: str = Field(..., description="Unique task identifier")
    job_id: str = Field(..., description="Parent job ID")
    article_id: str = Field(..., description="Article ID to scrape")
    url: str = Field(..., description="Article URL to scrape")
    source: str = Field(..., description="Article source")
    category: str = Field(..., description="Article category")
    priority: int = Field(default=1, ge=1, le=10, description="Task priority")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "task_001",
                "job_id": "job_123abc",
                "article_id": "art_001",
                "url": "https://example.com/article1",
                "source": "TechNews",
                "category": "AI",
                "priority": 1,
                "retry_count": 0,
                "max_retries": 3
            }
        }
    )