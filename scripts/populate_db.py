"""
Populate the database with sample data

python3 scripts/populate_db.py
"""
import argparse
import os
from pathlib import Path
import sys

import django
import faker

# Must configure standalone django usage before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.append(str(Path(__file__).parents[1].resolve()))
django.setup()


from nf_executor.api import enums, models
from nf_executor.api.tests import factories


def parse_args():
    parser = argparse.ArgumentParser(description='Populate the database')
    parser.add_argument('-j', '--n_jobs', dest='n_jobs',
                        type=int, default=2,
                        help='# jobs to create')

    parser.add_argument('-t', '--n_tasks', dest='n_tasks',
                        type=int, default=10,
                        help='# tasks to create')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    # We need a real workflow, not dummy data from a factory, to test executor functionality
    # w = factories.WorkflowFactory()
    w, _ = models.Workflow.objects.get_or_create(
        name='Mock workflow',
        version='1.0.0',
        description='An example nextflow workflow based on Hello World Tutorial',
        definition_path=Path(__file__).parent / 'mock_workflow' / 'hello.nf'
    )
    w.save()

    # Note: This will create job models, but not execute them against the workflow.
    fake = faker.Faker()
    for i in range(args.n_jobs):
        this_name = fake.name()
        # These are fake data, which is to say that all fields are populated even if job status is not yet started
        # We may improve the factories in future
        mock_workflow_params = {'greeting': f'Hello, {this_name}'}
        job = factories.JobFactory(
            workflow=w,
            params=mock_workflow_params,
        )
        for j in range(args.n_tasks):
            task_id = str(j)
            factories.TaskFactory(job=job, task_id=task_id, native_id=task_id)
    print("Database populated successfully")
