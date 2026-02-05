from fastapi import FastAPI
from routes import job_router

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_route(job_router)