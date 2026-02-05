from fastapi import APIRouter
from typing import List
from models.article import ArticleBase
from models.job import JobSubmitResponse

job_router = APIRouter()

@job_router.post("/jobs/submit")
async def submit_job(articles: List[ArticleBase]) -> JobSubmitResponse:
    
