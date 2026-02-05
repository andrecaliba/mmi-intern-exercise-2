from fastapi import APIRouter, status
from typing import List
from models.article import ArticleBase
from models.job import JobSubmitResponse
from services.publisher import publish_all

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
    