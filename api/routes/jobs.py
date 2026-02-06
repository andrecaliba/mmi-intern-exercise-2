from fastapi import APIRouter, HTTPException, status
from typing import List
from models.article import ArticleBase, ArticleStatus, ArticleResponse, FailedArticleResponse
from models.job import JobSubmitResponse, JobStatusResponse, JobResultsResponse
from services.publisher import publish_all
from database.connection import DatabaseManager
from database.repositories.job_repo import JobRepository
from database.repositories.article_repo import ArticleRepository

job_router = APIRouter()

@job_router.post(
    "/jobs/submit",
    status_code=status.HTTP_201_CREATED,
    response_model=JobSubmitResponse
)
async def submit_job(articles: List[ArticleBase]):
    result = await publish_all(articles)
    if result:
        return result
    raise HTTPException(status_code=400, detail="Failed to publish articles")


@job_router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get job status"
)
async def get_job_status(job_id: str):
    """
    Get current job status and progress.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        JobStatusResponse with current status and progress
    """
    try:
        db = DatabaseManager.get_database()
        job_repo = JobRepository(db)
        
        # Get the job
        job = await job_repo.get_by_id(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Return job status
        return JobStatusResponse(
            job_id=str(job.id),
            status=job.status,
            total_articles=job.total_articles,
            completed=job.completed_count,
            failed=job.failed_count,
            pending=job.pending_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@job_router.get(
    "/jobs/{job_id}/results",
    response_model=JobResultsResponse,
    summary="Get job results"
)
async def get_job_results(job_id: str):
    """
    Get complete job results with all article data.
    
    Args:
        job_id: Job ID to get results for
        
    Returns:
        JobResultsResponse with article data
    """
    try:
        db = DatabaseManager.get_database()
        job_repo = JobRepository(db)
        article_repo = ArticleRepository(db)
        
        # Get the job
        job = await job_repo.get_by_id(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Get all articles for this job
        articles = await article_repo.get_by_ids(job.article_ids)
        
        # Separate successful and failed articles
        successful_articles = []
        failed_articles = []
        
        for article in articles:
            if article.status == ArticleStatus.SCRAPED:
                # Successful article
                successful_articles.append(
                    ArticleResponse(
                        article_id=str(article.id),
                        url=str(article.url),
                        source=article.source,
                        category=article.category,
                        title=article.title,
                        content=article.content,
                        scraped_at=article.scraped_at,
                        cached=article.reference_count > 1
                    ).model_dump()
                )
            elif article.status == ArticleStatus.FAILED:
                # Failed article
                failed_articles.append(
                    FailedArticleResponse(
                        url=str(article.url),
                        error=article.error_message or "Unknown error",
                        attempted_at=article.updated_at
                    ).model_dump()
                )
        
        return JobResultsResponse(
            job_id=str(job.id),
            status=job.status,
            total_articles=job.total_articles,
            successful=len(successful_articles),
            failed=len(failed_articles),
            results=successful_articles,
            failed_articles=failed_articles
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job results: {str(e)}"
        )