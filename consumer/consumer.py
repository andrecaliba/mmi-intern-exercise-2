"""
Consumer Service
Continuously polls Redis for scraping tasks and processes them
"""
import json
import os
import time
import redis
from datetime import datetime
from typing import Optional

from database.connection import DatabaseManager
from database.repositories.article_repo import ArticleRepository
from database.repositories.job_repo import JobRepository
from api.models.article import ArticleStatus
from api.models.job import JobStatus
from consumer.scraper import get_title, get_content

# Redis connection
redis_uri = os.getenv('REDIS_URL', 'redis://redis:6379')

redis_client = redis.from_url(redis_uri)


class Consumer:
    """Consumer service for processing article scraping tasks"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.redis_client = redis_client
        self.article_repo = None
        self.job_repo = None
        self.max_retries = 3
        
    async def initialize(self):
        """Initialize database connection and repositories"""
        await DatabaseManager.connect()
        db = DatabaseManager.get_database()
        
        self.article_repo = ArticleRepository(db)
        self.job_repo = JobRepository(db)
        
        print(f"[{self.worker_id}] Consumer initialized")
    
    async def subscribe(self):
        """
        Poll Redis queue indefinitely and process articles.
        Implements retry logic with exponential backoff and DLQ.
        """
        print(f"[{self.worker_id}] Consumer started, waiting for tasks...")
        
        while True:
            try:
                # Blocking pop from Redis sorted set (lower score = higher priority)
                result = self.redis_client.bzpopmin('articles', timeout=5)
                
                if result:
                    queue_name, message, score = result
                    task_data = json.loads(message)
                    
                    print(f"\n[{self.worker_id}] Received task: {task_data.get('url')}")
                    
                    # Process the article
                    await self.process_article(task_data, score)
                    
                else:
                    # No tasks available - idle
                    pass
                    
            except KeyboardInterrupt:
                print(f"\n[{self.worker_id}] Shutting down gracefully...")
                break
                
            except Exception as e:
                print(f"[{self.worker_id}] Critical error in main loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    async def process_article(self, task_data: dict, priority_score: float):
        """
        Process a single article scraping task.
        
        Args:
            task_data: Task containing job_id, article_id, url, source, category, priority
            priority_score: Priority score from Redis
        """
        job_id = task_data.get('job_id')
        article_id = task_data.get('article_id')
        url = task_data.get('url')
        print(f"Job ID: {job_id}")
        print(f"article ID: {article_id}")
        print(f"url: {url}")
        retry_count = task_data.get('retry_count', 0)
        
        try:
            # Step 1: Update article status to SCRAPING
            print(f"[{self.worker_id}] Scraping: {url}")
            await self.article_repo.update_status(article_id, ArticleStatus.SCRAPING)
            
            # Step 2: Scrape the article
            title, content = await self.scrape_article_content(url)
            
            if not title or not content:
                raise Exception("Failed to extract title or content")
            
            # Step 3: Update article with scraped data
            print(f"[{self.worker_id}] Successfully scraped: {title}")
            success = await self.article_repo.update_status(
                article_id=article_id,
                status=ArticleStatus.SCRAPED,
                title=title,
                content=content
            )
            
            if not success:
                raise Exception("Failed to update article in database")
            
            # Step 4: Update job progress (increment completed count)
            await self.job_repo.increment_completed(job_id)
            print(f"[{self.worker_id}] Job {job_id}: article completed")
            
            # Step 5: Check if job is complete
            await self.job_repo.check_and_complete_job(job_id)
            
        except Exception as e:
            # Scraping failed - handle retry logic
            print(f"[{self.worker_id}] Error scraping {url}: {e}")
            await self.handle_failure(task_data, priority_score, str(e))
    
    async def handle_failure(self, task_data: dict, priority_score: float, error_message: str):
        """
        Handle failed article scraping with retry logic.
        
        Args:
            task_data: Task that failed
            priority_score: Original priority score
            error_message: Error description
        """
        job_id = task_data.get('job_id')
        article_id = task_data.get('article_id')
        url = task_data.get('url')
        retry_count = task_data.get('retry_count', 0)
        
        retry_count += 1
        task_data['retry_count'] = retry_count
        
        if retry_count >= self.max_retries:
            # Max retries reached - move to DLQ and mark as FAILED
            print(f"[{self.worker_id}] Max retries reached for {url}, moving to DLQ")
            
            # Update article status to FAILED
            await self.article_repo.update_status(
                article_id=article_id,
                status=ArticleStatus.FAILED,
                error_message=error_message
            )
            
            # Increment job's failed count
            await self.job_repo.increment_failed(job_id)
            
            # Move to Dead Letter Queue
            dlq_data = {
                **task_data,
                'failed_at': datetime.utcnow().isoformat(),
                'final_error': error_message,
                'worker_id': self.worker_id
            }
            self.redis_client.lpush("failed_articles", json.dumps(dlq_data))
            
            # Check if job is complete (even with failures)
            await self.job_repo.check_and_complete_job(job_id)
            
        else:
            # Retry with exponential backoff
            backoff_time = 2 ** retry_count  # 2, 4, 8 seconds
            
            print(f"[{self.worker_id}] Retry {retry_count}/{self.max_retries} for {url} (waiting {backoff_time}s)")
            
            # Wait before re-queuing
            time.sleep(backoff_time)
            
            # Re-queue the task with same priority
            self.redis_client.zadd('articles', {json.dumps(task_data): priority_score})
    
    async def scrape_article_content(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Scrape title and content from URL.
        
        Args:
            url: Article URL to scrape
            
        Returns:
            Tuple of (title, content)
        """
        try:
            # Import your scraping logic
            # This should use BeautifulSoup or similar
            
            title = get_title(url, self.worker_id)
            content = get_content(url, self.worker_id)
            
            return title, content
            
        except Exception as e:
            print(f"[{self.worker_id}] Scraping error for {url}: {e}")
            raise


async def start_consumer(worker_id: str = "worker-1"):
    """
    Start a consumer worker.
    
    Args:
        worker_id: Unique identifier for this worker
    """
    consumer = Consumer(worker_id)
    await consumer.initialize()
    await consumer.subscribe()


if __name__ == "__main__":
    import asyncio
    import sys
    
    # Get worker ID from command line or use default
    worker_id = sys.argv[1] if len(sys.argv) > 1 else f"worker-{os.getpid()}"
    
    print(f"🚀 Starting consumer: {worker_id}")
    asyncio.run(start_consumer(worker_id))