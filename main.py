from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
from database import engine, get_db, SessionLocal
from manager import run_pipeline

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/build")
async def trigger_build(
    repo_url: str, 
    branch: str, 
    language: str, # NEW: Requirement #7
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    # Ensure language is lowercase for matching
    lang = language.lower()
    new_job = models.Job(repo_url=repo_url, branch=branch, language=lang, status="Queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    background_tasks.add_task(run_pipeline, new_job.id, SessionLocal)
    return {"job_id": new_job.id, "status": "Queued", "assigned_language": lang}

@app.get("/api/v1/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    # Include worker_id and language in the response
    jobs = db.query(models.Job).all()
    
    return {
        "queued": [j for j in jobs if j.status == "Queued"],
        "in_progress": [
            {
                "id": j.id, 
                "repo": j.repo_url, 
                "worker": j.worker_id, # Requirement #6
                "lang": j.language,    # Requirement #7
                "stages": [{"name": s.name, "status": s.status} for s in j.stages]
            } for j in jobs if j.status == "In-Progress"
        ],
        "completed": [j for j in jobs if j.status in ["Completed", "Failed"]]
    }