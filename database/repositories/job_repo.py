"""
Job Repository
CRUD operations for Jobs collection using PyMongo AsyncMongoClient
"""
from typing import Optional, List
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime

from api.models.job import (
    Job,
    JobCreate,
    JobUpdate,
    JobStatus
)

class JobRepository:
    """Repository for Job CRUD operations"""
    
    def __init__(self, db: Database):
        self.collection = db["jobs"]
    
    async def create(self, job_data: JobCreate) -> str:
        """
        Create a new job
        
        Args:
            job_data: Job creation data
            
        Returns:
            str: Created job ID
        """
        job = Job(
            total_articles=job_data.total_articles,
            new_articles=job_data.new_articles,
            cached_articles=job_data.cached_articles,
            article_ids=job_data.article_ids
        )
        
        job_dict = job.to_dict()
        
        result = await self.collection.insert_one(job_dict)
        return str(result.inserted_id)
    
    async def get_by_id(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID
        
        Args:
            job_id: Job ObjectId as string
            
        Returns:
            Job or None if not found
        """
        if not ObjectId.is_valid(job_id):
            return None
        
        doc = await self.collection.find_one({"_id": ObjectId(job_id)})
        return Job.from_mongo(doc) if doc else None
    
    async def update(self, job_id: str, update_data: JobUpdate) -> bool:
        """
        Update job fields
        
        Args:
            job_id: Job ObjectId as string
            update_data: Fields to update
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return False
        
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    async def update_status(self, job_id: str, status: JobStatus) -> bool:
        """
        Update job status
        
        Args:
            job_id: Job ObjectId as string
            status: New job status
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        # Set completed_at when job is completed
        if status == JobStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def add_article_to_job(self, job_id: str, article_id: str) -> bool:
        """
        Add article ID to job's article_ids array
        
        Args:
            job_id: Job ObjectId as string
            article_id: Article ObjectId as string
            
        Returns:
            bool: True if added, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$addToSet": {"article_ids": article_id},  # addToSet prevents duplicates
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def increment_completed(self, job_id: str) -> bool:
        """
        Increment completed_count
        
        Args:
            job_id: Job ObjectId as string
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$inc": {"completed_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def increment_failed(self, job_id: str) -> bool:
        """
        Increment failed_count
        
        Args:
            job_id: Job ObjectId as string
            
        Returns:
            bool: True if updated, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$inc": {"failed_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def check_and_complete_job(self, job_id: str) -> bool:
        """
        Check if all articles are processed and update status to COMPLETED
        
        Args:
            job_id: Job ObjectId as string
            
        Returns:
            bool: True if job was completed, False otherwise
        """
        job = await self.get_by_id(job_id)
        if not job:
            return False
        
        # Check if all articles are processed
        total_processed = job.completed_count + job.failed_count
        if total_processed >= job.total_articles:
            return await self.update_status(job_id, JobStatus.COMPLETED)
        
        return False
    
    async def delete(self, job_id: str) -> bool:
        """
        Delete job by ID
        
        Args:
            job_id: Job ObjectId as string
            
        Returns:
            bool: True if deleted, False otherwise
        """
        if not ObjectId.is_valid(job_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(job_id)})
        return result.deleted_count > 0
    
    async def list_all(self, limit: int = 100, skip: int = 0) -> List[Job]:
        """
        List all jobs with pagination
        
        Args:
            limit: Maximum number of jobs to return
            skip: Number of jobs to skip
            
        Returns:
            List of jobs
        """
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Job.from_mongo(doc) for doc in docs]
    
    async def list_by_status(self, status: JobStatus, limit: int = 100) -> List[Job]:
        """
        List jobs by status
        
        Args:
            status: Job status to filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs
        """
        cursor = self.collection.find({"status": status.value}).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Job.from_mongo(doc) for doc in docs]
    
    async def count(self) -> int:
        """
        Count total jobs
        
        Returns:
            int: Total number of jobs
        """
        return await self.collection.count_documents({})
    
    async def count_by_status(self, status: JobStatus) -> int:
        """
        Count jobs by status
        
        Args:
            status: Job status
            
        Returns:
            int: Number of jobs with given status
        """
        return await self.collection.count_documents({"status": status.value})