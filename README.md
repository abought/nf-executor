# nf-executor
A command and control node for a microservice that runs multiple nextflow workflows.

This does not interact with users and should not be exposed to the public internet. It handles LAUNCHING and MONITORING of (many) separate workflow processes. It is the job of the web application to translate user inputs into the options expected by nextflow.

## Local development
### Setup
Local development occurs through Docker. If you use an IDE such as Pycharm, you can even [specify the docker compose file as project interpreter]() to take advantage of IDE features within the container.

Initial installation: build the container, then set up the database
```bash
docker-compose -f local.yml build
docker-compose -f local.yml run --rm django python manage.py migrate

# Add sample data to the database
docker-compose -f local.yml run --rm django python scripts/populate_db.py
```

### Running the dev server

Note: instead of a CLI docker command, you can alternately use IDE integrations to run django. Just specify docker-compose as the project interpreter.

`docker-compose -f local.yml up -d`

### Validating code

#### Unit tests
```bash
docker-compose -f local.yml run --rm django python manage.py test
```

### Managing database migrations
Django has the ability to automatically generate database migrations. The *local* (but not production) container will run migrations on every container start.

```bash
# Generate new DB migrations
docker-compose -f local.yml run --rm django python manage.py makemigrations
# Consolidate as many migrations as possible
docker-compose -f local.yml run --rm django python manage.py squashmigrations
```


### Interactive debugging shell
```bash
docker-compose -f local.yml run --rm django python manage.py shell
```

### Dropping the database and restarting from scratch
During early development, this can be useful for iterating the schema without too many spare migrations. Definitely do not do this once the app is "live", as we really want to preserve migration history!
```bash
docker-compose -f local.yml down -v
docker-compose -f local.yml run --rm django python manage.py makemigrations
docker-compose -f local.yml up
```
