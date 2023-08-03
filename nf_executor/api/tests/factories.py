import datetime
import random

import factory
from factory.django import DjangoModelFactory

from .. import enums, models


def sem_version() -> str:
    parts = [random.randint(1, 5), random.randint(1, 9), random.randint(1, 3)]
    return '.'.join(str(i) for i in parts)


def random_job_status() -> int:
    return random.choice(list(enums.JobStatus)).value


def random_task_status() -> int:
    return random.choice(list(enums.TaskStatus)).value


class WorkflowFactory(DjangoModelFactory):
    name = factory.Faker('text', max_nb_chars=20)
    description = factory.Faker('sentence', nb_words=4)
    version = factory.LazyFunction(sem_version)
    definition_path = factory.Faker('file_path', depth=3)

    class Meta:
        model = models.Workflow


class JobFactory(DjangoModelFactory):
    run_id = factory.Faker('md5', raw_output=False)
    name = factory.Faker('text', max_nb_chars=20)

    workflow = factory.SubFactory(WorkflowFactory)

    owner = factory.Faker('email', safe=True)
    executor_id = factory.Faker('md5', raw_output=False)
    status = factory.LazyFunction(random_job_status)

    expire_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    start_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    duration = factory.LazyFunction(lambda: random.randint(1, 1000))

    succeed_count = factory.LazyFunction(lambda: random.randint(1, 10))
    retries_count = factory.LazyFunction(lambda: random.randint(1, 5))

    class Meta:
        model = models.Job


class TaskFactory(DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    name = factory.Faker('text', max_nb_chars=20)
    status = factory.LazyFunction(random_task_status)

    submitted_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    started_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    completed_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)

    class Meta:
        model = models.Task
