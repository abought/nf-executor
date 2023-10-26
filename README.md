# nf-executor
A command and control node for a microservice that runs multiple nextflow workflows.

This does not interact with users and should not be exposed to the public internet. It handles LAUNCHING and MONITORING of (many) separate workflow processes. It is the job of the web application to translate user inputs into the options expected by nextflow.

## Setup (for local development)

Initial installation
```bash
python3 -mvenv .venv
pip3 install -r requirements/local.txt 
```

Then run the database migrations to create the DB and schema:
```bash
python manage.py migrate --settings=config.settings.local
```

For local development, you will need Nextflow installed. This demo was written using Nextflow version > 23.04.2 and Python 3.11.

In the initial prototype, you may need to explicitly edit some settings in `config.settings` (local and base). Particularly referencing file locations.

## Running
Currently, only a basic development mode is implemented (for prototyping purposes). In the future, local and production containers will be provided.
```bash
python manage.py runserver --settings=config.settings.local
```

## Run unit tests
 ```bash
 python manage.py test --settings=config.settings.local
 ```

## Management commands
Database migrations:
```bash
python manage.py makemigrations --settings=config.settings.local
python manage.py migrate --settings=config.settings.local
```

Interactive debugging shell:
```bash
python manage.py shell --settings=config.settings.local
```
