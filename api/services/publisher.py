import json, os, redis
from services.deduplication import exist_and_is_scraped
from database.connection import DatabaseManager
from database.repositories.job_repo import JobRepository
from api.models.job import (
    JobCreate,
    JobSubmitResponse,
    JobStatus
)

priority_map = {
    "high": 1,
    "medium": 2,
    "low": 3
}

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(REDIS_URL)

# def __parse_json(filename):
#     """
#     Load and parse articles from JSON file.
    
#     Returns:
#         dict: Parsed JSON data or empty list if error occurs
#     """
#     try:
#         with open(filename, 'r') as file:
#             data = json.load(file)
#             return data
#     except FileNotFoundError:
#         print("File not found")
#         return []
#     except json.JSONDecodeError:
#         print("Invalid JSON format")
#         return []

def publish_article(data):
    """
    Push single article to Redis sorted set.
    
    Args:
        data: Article dictionary containing url, source, category, priority
    """
    message = json.dumps(data)
    priority = data.get('priority', 'medium')
    score = priority_map.get(priority, 2)
    redis_client.zadd('articles', {message: score})

async def publish_all(data):
    """Parse JSON file and publish all articles to Redis queue."""
    existing_articles, new_articles = 0, 0
    linked_articles =[]
    for article in data:
        article_dict = article.model_dump()
        article_dict["url"] = str(article_dict["url"])
        print(f"Article: {article_dict}")
        exists_and_scraped = await exist_and_is_scraped(article_dict["url"])
        if exists_and_scraped:
            existing_articles += 1
            linked_articles.append(article_dict["id"])
            continue
        publish_article(article_dict)
        new_articles += 1
    inserted_id = await create_job(existing_articles, new_articles, linked_articles, len(data))
    print(f"inserted_id: {inserted_id}")
    if inserted_id:
        print("job inserted")
        return JobSubmitResponse(
            job_id=str(inserted_id),
            status=JobStatus.PENDING,
            total_articles=len(data),
            new_articles=new_articles,
            cached_articles=existing_articles
        )

async def create_job(existing_articles, new_articles, linked_articles, num_articles):
    await DatabaseManager.connect()
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