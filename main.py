from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
from database import engine, get_db, SessionLocal
from manager import run_pipeline

# 1. Initialize Database Tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. CORS MIDDLEWARE 
# Allows your browser's index.html to communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/build")
async def trigger_build(
    repo_url: str, 
    branch: str, 
    language: str, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Endpoint to trigger a new build.
    Saves the job to Postgres and starts the background worker manager.
    """
    lang = language.lower()
    new_job = models.Job(repo_url=repo_url, branch=branch, language=lang, status="Queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Start the orchestrator logic in the background
    background_tasks.add_task(run_pipeline, new_job.id, SessionLocal)

    return {"job_id": new_job.id, "status": "Queued", "worker_type": lang}

@app.get("/api/v1/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Endpoint for the Dashboard to fetch all job statuses.
    """
    jobs = db.query(models.Job).all()
    
    return {
        "queued": [j for j in jobs if j.status == "Queued"],
        "in_progress": [
            {
                "id": j.id, 
                "repo": j.repo_url, 
                "worker": j.worker_id,
                "lang": j.language,
                "stages": [{"name": s.name, "status": s.status} for s in j.stages]
            } for j in jobs if j.status == "In-Progress"
        ],
        "completed": [j for j in jobs if j.status in ["Completed", "Failed"]]
    }

@app.post("/api/v1/reset")
async def reset_dashboard(db: Session = Depends(get_db)):
    """
    The 'Panic Button': Clears all data and resets build counter to #1.
    """
    try:
        # TRUNCATE removes all data and RESTART IDENTITY resets the ID counter to 1
        db.execute(text("TRUNCATE TABLE stages, jobs RESTART IDENTITY CASCADE;"))
        db.commit()
        return {"message": "Database cleared and Build counter reset to #1"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}