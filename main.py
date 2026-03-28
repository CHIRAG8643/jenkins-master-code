from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
from database import engine, get_db, SessionLocal
from manager import run_pipeline

# 1. Initialize Database Tables
# This creates 'jobs' and 'stages' tables in Postgres if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. CORS MIDDLEWARE (The Fix for the Frontend)
# This allows your index.html to fetch data from this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all websites/files to access the API
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, etc.
    allow_headers=["*"],  # Allows all headers
)

@app.post("/api/v1/build")
async def trigger_build(repo_url: str, branch: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Endpoint to trigger a new build. 
    It saves the job to the DB and starts the background 'manager' task.
    """
    new_job = models.Job(repo_url=repo_url, branch=branch, status="Queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # background_tasks.add_task runs the 'run_pipeline' function in a separate thread
    # so the API can respond immediately without waiting for the clone/build to finish.
    background_tasks.add_task(run_pipeline, new_job.id, SessionLocal)

    return {"job_id": new_job.id, "status": "Queued"}

@app.get("/api/v1/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Endpoint for the Frontend (index.html) to get the latest status of all jobs.
    """
    queued = db.query(models.Job).filter(models.Job.status == "Queued").all()
    
    # We fetch jobs with 'In-Progress' status and include their nested stages
    in_progress_jobs = db.query(models.Job).filter(models.Job.status == "In-Progress").all()
    
    completed = db.query(models.Job).filter(models.Job.status.in_(["Completed", "Failed"])).all()

    return {
        "queued": queued,
        "in_progress": [
            {
                "id": j.id, 
                "repo": j.repo_url, 
                "stages": [{"name": s.name, "status": s.status} for s in j.stages]
            } for j in in_progress_jobs
        ],
        "completed": completed
    }