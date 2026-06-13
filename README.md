# LuminaLog 
**A Distributed, Event-Driven CI/CD Orchestrator with Priority Queueing and Stateless Execution.**

LuminaLog is a custom-built Continuous Integration and Continuous Deployment (CI/CD) engine. It acts as a lightweight alternative to systems like Jenkins or GitHub Actions, designed specifically to solve pipeline congestion through a **Smart Priority Scheduler** and **Dynamic Aging Algorithm**. 

By utilizing a headless API gateway and a pool of background workers, LuminaLog dynamically parses pipeline configurations on the fly and executes them in completely isolated, stateless environments.

---

##  Key Features

* **Smart Priority Scheduler:** Replaces standard FIFO queues. Critical hotfixes (`master`) automatically bypass the queue, while feature branches (`develop`, `feature/*`) are prioritized accordingly.
* **Anti-Starvation Aging Algorithm:** Mathematically guarantees that lower-priority jobs are not permanently starved by boosting their "Effective Priority" based on queue wait times.
* **Stateless Execution:** Workers generate unique timestamped workspaces, perform live Git clones, execute the pipeline, and tear down the environment upon completion—guaranteeing zero environment contamination.
* **Dynamic Pipeline Parsing:** The orchestrator reads the repository's `jenkinsfile.yaml` to dynamically build database stages, decoupling the server architecture from application-specific build steps.
* **Live Interactive Dashboard:** A decoupled HTML/JS frontend that continuously polls the API to visualize real-time pipeline progress, queue dynamics, and priority upgrades.

---

##  Architecture

LuminaLog utilizes a decoupled, distributed architecture consisting of four main pillars:

1.  **API Gateway (FastAPI):** Listens for simulated GitHub webhooks, calculates initial priorities, and manages the database state.
2.  **State Management (SQLite/PostgreSQL):** Acts as the single source of truth, tracking the exact state of every job and stage.
3.  **Worker Nodes (Python/GitPython):** Background processes that independently poll the queue, claim jobs, and execute the heavy lifting (Git clones, YAML parsing, execution simulations).
4.  **Visualization Layer:** An independent HTML frontend that tracks the living database state.

---

##  Tech Stack

* **Backend:** Python 3, FastAPI, Uvicorn
* **Database:** SQLAlchemy (SQLite for local development, scalable to PostgreSQL)
* **VCS Integration:** GitPython
* **Frontend:** HTML5, Vanilla JavaScript, CSS
* **Pipeline Config:** YAML

---
