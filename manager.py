import os
import git
import yaml
import time
import shutil
from sqlalchemy.orm import Session
import models

# ENSURE THIS NAME IS EXACTLY 'run_pipeline'
def run_pipeline(job_id: int, db_session_factory):
    # We create a fresh database session for the background thread
    db = db_session_factory()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return
            
        job.status = "In-Progress"
        db.commit()

        # 1. Setup path and Clone
        repo_path = f"./temp_builds/job_{job_id}"
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
        
        git.Repo.clone_from(job.repo_url, repo_path, branch=job.branch)

        # 2. Parse the jenkinsfile.yaml
        jenkins_file = os.path.join(repo_path, "jenkinsfile.yaml")
        if not os.path.exists(jenkins_file):
            raise Exception("jenkinsfile.yaml not found in repository root")

        with open(jenkins_file, "r") as f:
            config = yaml.safe_load(f)
        
        # 3. Create the stages in DB
        stages_data = config.get('pipeline', {}).get('stages', [])
        for s_name in stages_data:
            new_stage = models.Stage(job_id=job_id, name=s_name, status="Pending")
            db.add(new_stage)
        db.commit()

        # 4. Simulated "In-Progress" Loop
        db.refresh(job)
        for stage in job.stages:
            stage.status = "Running"
            db.commit()
            
            time.sleep(5) # Simulate the worker doing a task
            
            stage.status = "Success"
            db.commit()

        job.status = "Completed"
        
    except Exception as e:
        print(f"!!! Pipeline Error: {e}")
        if job:
            job.status = "Failed"
    finally:
        db.commit()
        db.close()
    shutil.rmtree(repo_path, ignore_errors=True)