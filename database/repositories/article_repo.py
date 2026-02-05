"""
Article Repository
CRUD operations for Articles collection using PyMongo AsyncMongoClient
"""
from typing import Optional, List
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from api.models.article import (
    Article, 
    ArticleCreate, 
    ArticleUpdate, 
    ArticleStatus
)


class ArticleRepository:
    """Repository for Article CRUD operations"""
    
    def __init__(self, db: Database):
        self.collection = db["articles"]
    
    async def create(self, article_data: ArticleCreate) -> str:
        """
        Create a new article
        
        Args:
            article_data: Article creation data
            
        Returns:
            str: Created article ID
            
        Raises:
            DuplicateKeyError: If URL already exists
        """
        article = Article(**article_data.model_dump())
        article_dict = article.to_dict()
        
        try:
            result = await self.collection.insert_one(article_dict)
            return str(result.inserted_id)
        except DuplicateKeyError:
            raise ValueError(f"Article with URL {article_data.url} already exists")
    
    async def get_by_id(self, article_id: str) -> Optional[Article]:
        """
        Get article by ID
        
        Args:
            article_id: Article ObjectId as string
            
        Returns:
            Article or None if not found
        """
        if not ObjectId.is_valid(article_id):
            return None
            
        doc = await self.collection.find_one({"_id": ObjectId(article_id)})
        return Article.from_mongo(doc) if doc else None
    
    async def get_by_url(self, url: str) -> Optional[Article]:
        """
        Get article by URL (for deduplication check)
        
        Args:
            url: Article URL
            
        Returns:
            Article or None if not found
        """
        doc = await self.collection.find_one({"url": url})
        return Article.from_mongo(doc) if doc else None
    
    async def get_by_urls(self, urls: List[str]) -> List[Article]:
        """
        Get multiple articles by URLs (batch deduplication)
        
        Args:
            urls: List of article URLs
            
        Returns:
            List of found articles
        """
        cursor = self.collection.find({"url": {"$in": urls}})
        docs = await cursor.to_list(length=None)
        return [Article.from_mongo(doc) for doc in docs]
    
    async def get_by_ids(self, article_ids: List[str]) -> List[Article]:
        """
        Get multiple articles by IDs
        
        Args:
            article_ids: List of article ObjectIds as strings
            
        Returns:
            List of found articles
        """
        valid_ids = [ObjectId(aid) for aid in article_ids if ObjectId.is_valid(aid)]
        cursor = self.collection.find({"_id": {"$in": valid_ids}})
        docs = await cursor.to_list(length=None)
        return [Article.from_mongo(doc) for doc in docs]
    
    async def update(self, article_id: str, update_data: ArticleUpdate) -> bool:
        """
        Update article fields
        
        Args:
            article_id: Article ObjectId as string
            update_data: Fields to update
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(article_id):
            return False
        
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return False
            
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    async def update_status(
        self, 
        article_id: str, 
        status: ArticleStatus,
        title: Optional[str] = None,
        content: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update article status and optional fields
        
        Args:
            article_id: Article ObjectId as string
            status: New status
            title: Article title (if scraped)
            content: Article content (if scraped)
            error_message: Error message (if failed)
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(article_id):
            return False
        
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        # Set scraped_at timestamp when status is SCRAPED
        if status == ArticleStatus.SCRAPED:
            update_data["scraped_at"] = datetime.utcnow()
        
        # Add optional fields if provided
        if title:
            update_data["title"] = title
        if content:
            update_data["content"] = content
        if error_message:
            update_data["error_message"] = error_message
        
        result = await self.collection.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def increment_reference_count(self, article_id: str) -> bool:
        """
        Increment reference count (when article is reused by another job)
        
        Args:
            article_id: Article ObjectId as string
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(article_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(article_id)},
            {
                "$inc": {"reference_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def delete(self, article_id: str) -> bool:
        """
        Delete article by ID
        
        Args:
            article_id: Article ObjectId as string
            
        Returns:
            bool: True if deleted, False otherwise
        """
        if not ObjectId.is_valid(article_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(article_id)})
        return result.deleted_count > 0
    
    async def list_all(self, limit: int = 100, skip: int = 0) -> List[Article]:
        """
        List all articles with pagination
        
        Args:
            limit: Maximum number of articles to return
            skip: Number of articles to skip
            
        Returns:
            List of articles
        """
        cursor = self.collection.find().skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Article.from_mongo(doc) for doc in docs]
    
    async def count(self) -> int:
        """
        Count total articles
        
        Returns:
            int: Total number of articles
        """
        return await self.collection.count_documents({})
    
    async def count_by_status(self, status: ArticleStatus) -> int:
        """
        Count articles by status
        
        Args:
            status: Article status
            
        Returns:
            int: Number of articles with given status
        """
        return await self.collection.count_documents({"status": status.value})