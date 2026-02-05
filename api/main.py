from fastapi import FastAPI
from .routes.jobs import job_router

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(job_router)