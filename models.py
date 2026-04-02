from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String)
    branch = Column(String)
    
    # NEW: Requirements 6 & 7 fields
    language = Column(String)  # python, nodejs, or go
    worker_id = Column(String, nullable=True)  # Which worker is assigned?
    
    status = Column(String, default="Queued")
    stages = relationship("Stage", back_populates="job")

class Stage(Base):
    __tablename__ = "stages"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    name = Column(String)
    status = Column(String, default="Pending")
    job = relationship("Job", back_populates="stages")