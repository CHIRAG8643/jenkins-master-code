from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base  # This fixed your error

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String)
    branch = Column(String)
    status = Column(String, default="Queued") # Queued, In-Progress, Completed, Failed
    
    stages = relationship("Stage", back_populates="job")

class Stage(Base):
    __tablename__ = "stages"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    name = Column(String)
    status = Column(String, default="Pending") # Pending, Running, Success
    
    job = relationship("Job", back_populates="stages")