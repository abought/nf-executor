FROM python:3.11-slim-bookworm

RUN pip3 install -r requirements.txt

COMMAND ["uvicorn", "src.main:app"]
