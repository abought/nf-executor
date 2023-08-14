import datetime
from pathlib import Path
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


def get_mock_workflow() -> models.Workflow:
    """
    Less factory, more a fixture representing a workflow provided with the repo. Used to test executor functionality

    This is not a factory trait because we only want to create it once.
    """
    w, _ = models.Workflow.objects.get_or_create(
        name='Mock workflow',
        version='1.0.0',
        description='An example nextflow workflow based on Hello World Tutorial',
        definition_path=Path(__file__).parents[3] / 'mock_workflow' / 'hello.nf'
    )
    w.save()
    return w


class WorkflowFactory(DjangoModelFactory):
    name = factory.Faker('text', max_nb_chars=20)
    description = factory.Faker('sentence', nb_words=4)
    version = factory.LazyFunction(sem_version)
    definition_path = factory.Faker('file_path', depth=3)

    class Meta:
        model = models.Workflow


class JobFactory(DjangoModelFactory):
    run_id = factory.Faker('md5', raw_output=False)

    workflow = factory.SubFactory(WorkflowFactory)

    params = factory.LazyFunction(dict)

    owner = factory.Faker('email', safe=True)
    executor_id = factory.Faker('md5', raw_output=False)
    status = factory.LazyFunction(random_job_status)

    expire_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    started_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    completed_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)

    duration = factory.Faker('random_int', min=0, max=1000)

    succeed_count = factory.Faker('random_int', min=1, max=10)
    retries_count = factory.Faker('random_int', min=0, max=2)

    class Meta:
        model = models.Job

    class Params:
        is_submitted = factory.Trait(
            status=enums.JobStatus.submitted.value,
            started_on=None,
            completed_on=None,
            executor_id='',
            duration=0,
            succeed_count=0,
            retries_count=0
        )

        is_started = factory.Trait(
            status=enums.JobStatus.started.value,
            completed_on=None,
            executor_id='42',
            duration=0,
            succeed_count=0,
            retries_count=0
        )

        is_completed = factory.Trait(
            status=enums.JobStatus.started.value,
            executor_id='42',
            duration=1000,
            succeed_count=5,
            retries_count=1
        )

        is_error = factory.Trait(
            #  TODO capture error records, then write error trait
            status=enums.JobStatus.error.value,
        )

        is_canceled = factory.Trait(
            # Not a NF event, therefore fields depend on us
            status=enums.JobStatus.error.canceled.value,
            expire_on=datetime.datetime.utcnow(),  # if canceled, records flagged for immediate removal
            duration=1000  # start -> now
        )


class TaskFactory(DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    name = factory.Faker('text', max_nb_chars=20)

    task_id = factory.Sequence(lambda n: n + 1)
    native_id = factory.Sequence(lambda n: n + 1)

    status = factory.LazyFunction(random_task_status)
    exit_code = factory.Faker('random_int', min=0, max=2)

    submitted_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    started_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)
    completed_on = factory.Faker('date_time', tzinfo=datetime.timezone.utc)

    class Meta:
        model = models.Task

    class Params:
        is_submitted = factory.Trait(
            started_on=None,
            completed_on=None,
            status=enums.TaskStatus.process_submitted.value,
            native_id=None,
            exit_code=None,
        )

        is_started = factory.Trait(
            status=enums.TaskStatus.process_started.value,
            native_id="abc12",
            exit_code=None,
            completed_on=None,
        )

        is_completed = factory.Trait(
            status=enums.TaskStatus.process_completed.value,
        )

        # is_error = factory.Trait()  # Does NF ever communicate this about tasks?
