# nf-executor
A command and control node for a microservice that runs multiple nextflow workflows.

This does not interact with users and should not be exposed to the public internet. It handles LAUNCHING and MONITORING of (many) separate workflow processes. It is the job of the web application to translate user inputs into the options expected by nextflow.

## Running 
```bash
$ uvicorn src.main:app --reload
```
