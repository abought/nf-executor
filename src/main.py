"""
A command and control node for a microservice that runs multiple nextflow workflows.

This does not interact with users and should not be exposed to the public internet. It handles LAUNCHING and MONITORING
 of workflows, and acts as a central place to see output from many nextflow processes, even if they are running remotely.
"""

from fastapi import (
    FastAPI,
    Request
)

from fastapi.responses import ORJSONResponse
from fastapi import Request

import orjson

app = FastAPI()

sync = []


@app.get("/", response_class=ORJSONResponse)
async def root():
    print('home')
    return {"message": "Hello World"}


@app.get("/workflows/{wf_id}/", response_class=ORJSONResponse)
async def workflow_detail(wf_id: int):
    """Report basic workflow status: running, completed, etc. These are well known NF enum values"""
    try:
        return {'accepted': True}
    except:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


@app.get("/workflows/{wf_id}/", response_class=ORJSONResponse)
async def workflow_create(wf_id: int):
    """
    Initiate a new workflow run using the application-configured workflow executor strategy.
      (fargate, local subprocess, slurm submission, etc)
    """
    try:
        return {'accepted': True}
    except:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


@app.get("/workflows/{wf_id}/status/", response_class=ORJSONResponse)
async def workflow_status(wf_id: int):
    """Report basic workflow status: running, completed, etc. These are well known NF enum values"""
    try:
        return {'accepted': True}
    except:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


@app.post("/workflows/{wf_id}/report/", response_class=ORJSONResponse)
async def workflow_callback(wf_id: str, request: Request):
    print('received request')
    """Receive task and workflow progress reports from nextflow"""
    try:
        body = await request.json()
        sync.append(body)
        return {'accepted': True}
    except Exception as e:
        # TODO add logging / anomaly detection for error report here
        return {'accepted': False}


# @app.get("/workflows/{wf_id}/flush/", response_class=ORJSONResponse)
# async def workflow_callback(wf_id: str, request: Request):
#     """Testing only functionality: capture a log stream and dump to a file"""
#     global sync
#     with open(f'report-{wf_id}.json', 'wb') as f:
#         f.write(orjson.dumps(sync, option=orjson.OPT_INDENT_2))
#     sync = []
