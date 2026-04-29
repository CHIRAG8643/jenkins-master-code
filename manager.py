import os
import git
import yaml
import time
import shutil
import random
import models
import subprocess

# Requirement #6: Simulated Worker Pool
WORKER_POOL = {
    "Worker-Alpha": "python",
    "Worker-Beta": "python",
    "Worker-Gamma": "nodejs",
    "Worker-Delta": "go"
}

def run_pipeline(job_id: int, db_session_factory):
    """
    The Orchestrator logic: Handles queuing, worker assignment, 
    repo cloning, and stage execution.
    """
    db = db_session_factory()
    repo_path = f"./temp_builds/job_{job_id}"
    
    try:
        # 1. AGGRESSIVE CLEANUP (Fixes the 'Folder Already Exists' Error)
        if os.path.exists(repo_path):
            print(f"--- Cleaning up old directory for job {job_id} ---")
            shutil.rmtree(repo_path, ignore_errors=True)
            time.sleep(1) # Give Windows a second to release the lock
            
            # If shutil failed (common on Windows), try a force-delete via shell
            if os.path.exists(repo_path):
                subprocess.run(['rmdir', '/S', '/Q', repo_path.replace("/", "\\")], shell=True)

        # 2. Fetch the Job
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job: return

        # 3. QUEUE & BUSY CHECK LOGIC (Requirement #7)
        assigned_worker = None
        while assigned_worker is None:
            # Find workers that match the job's language
            compatible_workers = [w_id for w_id, lang in WORKER_POOL.items() if lang == job.language]
            
            if not compatible_workers:
                job.status = "Failed (No Worker for this Language)"
                db.commit()
                return

            # Check DB to see which workers are currently "In-Progress"
            busy_workers = db.query(models.Job.worker_id).filter(
                models.Job.status == "In-Progress",
                models.Job.worker_id.isnot(None)
            ).all()
            busy_worker_ids = [bw[0] for bw in busy_workers]

            # Find a worker that is compatible but NOT busy
            free_workers = [w for w in compatible_workers if w not in busy_worker_ids]

            if free_workers:
                assigned_worker = random.choice(free_workers)
            else:
                # Job stays 'Queued'. Wait and check again.
                print(f"--- Job #{job_id} is waiting. All {job.language} workers are busy. ---")
                time.sleep(5)
                db.refresh(job)

        # 4. Transition from Queued -> In-Progress
        job.worker_id = assigned_worker
        job.status = "In-Progress"
        db.commit()

        # 5. Clone the Repository
        print(f"--- {job.worker_id} is starting Build #{job_id} ---")
        git.Repo.clone_from(job.repo_url, repo_path, branch=job.branch)

        # 6. Parse Jenkinsfile
        jenkinsfile_path = os.path.join(repo_path, "jenkinsfile.yaml")
        if not os.path.exists(jenkinsfile_path):
            raise Exception("jenkinsfile.yaml not found in repository")

        with open(jenkinsfile_path, "r") as f:
            config = yaml.safe_load(f)
        
        stages_list = config.get('pipeline', {}).get('stages', [])
        for stage_name in stages_list:
            db.add(models.Stage(job_id=job_id, name=stage_name, status="Pending"))
        db.commit()

        # 7. Execute Stages with Randomness (Requirement #7)
        db.refresh(job)
        for stage in job.stages:
            stage.status = "Running"
            db.commit()
            
            # Simulate real-world build time variation
            time.sleep(random.randint(4, 12)) 
            
            stage.status = "Success"
            db.commit()

        job.status = "Completed"
        print(f"--- Build #{job_id} finished by {job.worker_id} ---")

    except Exception as e:
        print(f"Build Failed: {e}")
        if job: 
            job.status = "Failed"
    finally:
        db.commit()
        db.close()