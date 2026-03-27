from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import models
from database import engine, get_db, SessionLocal
from manager import run_pipeline  # <--- THIS MUST MATCH

# Initialize DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/api/v1/build")
async def trigger_build(repo_url: str, branch: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create the job in 'Queued' state
    new_job = models.Job(repo_url=repo_url, branch=branch, status="Queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Start the background manager
    background_tasks.add_task(run_pipeline, new_job.id, SessionLocal)

    return {"job_id": new_job.id, "status": "Queued"}

@app.get("/api/v1/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    queued = db.query(models.Job).filter(models.Job.status == "Queued").all()
    in_progress = db.query(models.Job).filter(models.Job.status == "In-Progress").all()
    completed = db.query(models.Job).filter(models.Job.status.in_(["Completed", "Failed"])).all()

    return {
        "queued": queued,
        "in_progress": [
            {
                "id": j.id, 
                "repo": j.repo_url, 
                "stages": [{"name": s.name, "status": s.status} for s in j.stages]
            } for j in in_progress
        ],
        "completed": completed
    }