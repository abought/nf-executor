"""
A command and control node for a microservice that runs multiple nextflow workflows.

This does not interact with users and should not be exposed to the public internet. It handles LAUNCHING and MONITORING
 of workflows, and acts as a central place to see output from many nextflow processes, even if run remotely.
"""

import logging

import pydantic
from fastapi import (
    exceptions as exc,
    Depends,
    FastAPI,
    Request,
)

from fastapi.responses import ORJSONResponse

from sqlalchemy.orm import Session

from src.db import models
from src.db.base import SessionLocal, engine
from src.db import crud, serializers


# TODO FUTURE switch to alembic for model creation etc.
models.Base.metadata.create_all(bind=engine)
logger = logging.getLogger("nf-executor-app")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


@app.exception_handler(pydantic.ValidationError)
async def validation_exception_handler(request, exc):
    """Human readable validation error payload"""
    return ORJSONResponse({
        'errors': [
            {'field': err['loc'], 'message': err['msg']}
            for err in exc.errors()
        ]
    }, status_code=400)


@app.get("/", response_class=ORJSONResponse)
async def root():
    """Basic status report for the system"""

    return {"running": 12}


@app.get("/workflows/", response_model=list[serializers.Workflow])
async def workflows_list(db: Session = Depends(get_db)):
    """List available workflows. TODO paginate"""
    return crud.get_workflows(db)


@app.get("/workflows/{wf_id}/", response_model=serializers.Workflow)
async def workflow_detail(wf_id: int, db: Session = Depends(get_db)):
    """Report basic workflow status: running, completed, etc. These are well known NF enum values"""
    try:
        return {'accepted': True}
    except:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


@app.post("/workflows/{wf_id}/", response_class=ORJSONResponse)
async def workflow_initiate(wf_id: int):
    """
    Initiate a new run of the specified workflow using the application-configured workflow executor strategy.
      (fargate, local subprocess, slurm submission, etc)
    """
    try:
        return {'accepted': True}
    except:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


@app.get("/jobs/{job_id}/status/", response_class=ORJSONResponse)
async def job_status(job_id: int):
    """
    Report basic job status: running, completed, etc.
      Custom query with groupBy for tasks. Caveat: counts do not reflect jobs not submitted yet!
    """
    return {
        'status': 'started',
        'tasks': {
            'pending': 3,
            'running': 6,
            'complete': 12,
        }}


@app.post("/jobs/{job_id}/report/", response_model=serializers.Job)
async def job_callback(job_id: int, request: Request):
    """
    Receive task and workflow progress reports from nextflow
    NOTE: Nextflow ignores the return value (it won't try to resend events if one gets dropped).
        The return value here is mainly to facilitate debugging.
    """
    body = await request.json()
    target = body['runName']
    if target != job_id:
        # This should never happen, unless something went very wrong with workflow creation.
        logger.error(f"Callback URL for {job_id} received nextflow events for {target}")
        raise exc.RequestValidationError('Nextflow reported job status to the wrong job.')

    return serializers.Job(
        run_name=target,
        workflow_id=12,
        status='submitted',
    )
