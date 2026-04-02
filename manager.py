import os
import git
import yaml
import time
import shutil
import random
import models

# Requirement #6: Simulated Worker Pool
# We have 2 Python workers, 1 Node worker, and 1 Go worker.
WORKER_POOL = {
    "Worker-Alpha": "python",
    "Worker-Beta": "python",
    "Worker-Gamma": "nodejs",
    "Worker-Delta": "go"
}

def run_pipeline(job_id: int, db_session_factory):
    db = db_session_factory()
    repo_path = f"./temp_builds/job_{job_id}"
    
    try:
        # 1. Fetch the Job
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job: return

        # 2. QUEUE & BUSY CHECK LOGIC (Requirement #7)
        assigned_worker = None
        while assigned_worker is None:
            # Find all workers that match the job's language
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
                # If no worker is free, the job stays 'Queued'. 
                # We wait 5 seconds before checking again.
                print(f"--- Job #{job_id} is waiting. All {job.language} workers are busy. ---")
                time.sleep(5)
                db.refresh(job)

        # 3. Transition from Queued -> In-Progress
        job.worker_id = assigned_worker
        job.status = "In-Progress"
        db.commit()

        # 4. Cleanup & Clone
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
            time.sleep(1)

        print(f"--- {job.worker_id} is starting Build #{job_id} ---")
        git.Repo.clone_from(job.repo_url, repo_path, branch=job.branch)

        # 5. Parse Jenkinsfile
        jenkinsfile_path = os.path.join(repo_path, "jenkinsfile.yaml")
        with open(jenkinsfile_path, "r") as f:
            config = yaml.safe_load(f)
        
        stages_list = config.get('pipeline', {}).get('stages', [])
        for stage_name in stages_list:
            db.add(models.Stage(job_id=job_id, name=stage_name, status="Pending"))
        db.commit()

        # 6. Execute Stages with Randomness (Requirement #7)
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
        if job: job.status = "Failed"
    finally:
        db.commit()
        db.close()