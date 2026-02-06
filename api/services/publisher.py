"""
Publisher Service
Handles job submission, article insertion, deduplication, and Redis queue publishing
"""
import json
import os
import redis

from database.connection import DatabaseManager
from database.repositories.job_repo import JobRepository
from database.repositories.article_repo import ArticleRepository
from api.models.job import JobCreate, JobSubmitResponse, JobStatus
from api.models.article import ArticleCreate, ArticleStatus

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(REDIS_URL)


def publish_article(data, job_id):
    """
    Push single article to Redis sorted set.
    
    Args:
        data: Article dictionary containing article_id, url, source, category, priority
        job_id: Job ID this article belongs to
    """
    # Create task with job_id and article_id
    task = {
        "job_id": job_id,
        "article_id": data.get("article_id"),
        "url": data.get("url"),
        "source": data.get("source"),
        "category": data.get("category"),
        "priority": data.get("priority", 3),
        "retry_count": 0
    }
    
    message = json.dumps(task)
    priority_score = data.get("priority", 3)
    
    redis_client.zadd('articles', {message: priority_score})
    print(f"Published to Redis: {data.get('url')} for job {job_id}")


async def publish_all(data):
    """
    Parse articles, insert to MongoDB, handle deduplication, and publish to Redis queue.
    
    Args:
        data: List of ArticleBase/ArticleCreate models
        
    Returns:
        JobSubmitResponse
    """
    # Connect to database
    await DatabaseManager.connect()
    db = DatabaseManager.get_database()
    
    article_repo = ArticleRepository(db)
    
    existing_articles_count = 0
    new_articles_count = 0
    linked_article_ids = []
    articles_to_publish = []  # Articles that need scraping
    
    # Process each article
    for article in data:
        article_dict = article.model_dump()
        article_dict["url"] = str(article_dict["url"])
        
        print(f"Processing article: {article_dict['url']}")
        
        # Check if article already exists
        existing_article = await article_repo.get_by_url(article_dict["url"])
        
        if existing_article and existing_article.status == ArticleStatus.SCRAPED:
            # Article exists and is already scraped - CACHED
            print(f"  CACHED: {article_dict['url']}")
            existing_articles_count += 1
            linked_article_ids.append(str(existing_article.id))
            
            # Increment reference count (this article is being reused)
            await article_repo.increment_reference_count(str(existing_article.id))
            
        else:
            # Article needs to be scraped
            if not existing_article:
                # NEW article - INSERT to MongoDB
                print(f"  NEW: {article_dict['url']} - Inserting to MongoDB")
                
                article_create = ArticleCreate(
                    url=str(article_dict["url"]),
                    source=article_dict.get("source"),
                    category=article_dict.get("category"),
                    priority=article_dict.get("priority", 3)
                )
                
                # INSERT article to MongoDB
                article_id = await article_repo.create(article_create)
                print(f"  Inserted article to MongoDB with ID: {article_id}")
                
            else:
                # Article exists but FAILED - retry scraping
                print(f"  RETRY: {article_dict['url']} (was {existing_article.status})")
                article_id = str(existing_article.id)
                
                # Reset status to PENDING
                await article_repo.update_status(article_id, ArticleStatus.PENDING)
            
            new_articles_count += 1
            linked_article_ids.append(article_id)
            
            # Prepare for publishing to Redis
            articles_to_publish.append({
                "article_id": article_id,  # Include article_id from MongoDB
                "url": article_dict["url"],
                "source": article_dict.get("source"),
                "category": article_dict.get("category"),
                "priority": article_dict.get("priority", 3)
            })
    
    # Create job
    total_articles = len(data)
    job_id = await create_job(
        existing_articles_count,
        new_articles_count,
        linked_article_ids,
        total_articles
    )
    
    print(f"\nJob created with ID: {job_id}")
    print(f"  Total articles: {total_articles}")
    print(f"  New articles: {new_articles_count}")
    print(f"  Cached articles: {existing_articles_count}")
    
    # Publish new articles to Redis WITH job_id
    print(f"\nPublishing {len(articles_to_publish)} articles to Redis...")
    for article_data in articles_to_publish:
        publish_article(article_data, job_id)  # Pass job_id here
    
    # Update job status
    job_repo = JobRepository(db)
    if new_articles_count == 0:
        # All articles were cached - job is complete
        await job_repo.update_status(job_id, JobStatus.COMPLETED)
        status = JobStatus.COMPLETED
        print("Job status: COMPLETED (all articles cached)")
    else:
        # Some articles need scraping
        await job_repo.update_status(job_id, JobStatus.IN_PROGRESS)
        status = JobStatus.IN_PROGRESS
        print("Job status: IN_PROGRESS")
    
    # Return response
    return JobSubmitResponse(
        job_id=str(job_id),
        status=status,
        total_articles=total_articles,
        new_articles=new_articles_count,
        cached_articles=existing_articles_count,
        message="Job submitted successfully"
    )


async def create_job(existing_articles, new_articles, linked_articles, num_articles):
    """
    Create a job in the database.
    
    Args:
        existing_articles: Number of cached articles
        new_articles: Number of new articles to scrape
        linked_articles: List of all article IDs (cached + new)
        num_articles: Total number of articles
        
    Returns:
        str: Created job ID
    """
    db = DatabaseManager.get_database()
    job_repo = JobRepository(db)
    
    job_data = JobCreate(
        total_articles=num_articles,
        new_articles=new_articles,
        cached_articles=existing_articles,
        article_ids=linked_articles
    )
    
    job_id = await job_repo.create(job_data)
    return job_id