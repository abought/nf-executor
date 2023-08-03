"""
Populate the database with sample data

python3 scripts/populate_db.py
"""
import argparse
import os
from pathlib import Path
import sys
import typing

import django

# Must configure standalone django usage before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.append(str(Path(__file__).parents[1].resolve()))
django.setup()


from nf_executor.api.tests import factories


def parse_args():
    parser = argparse.ArgumentParser(description='Populate the database')
    parser.add_argument('-w', '--n_workflows', dest='n_workflows',
                        type=int, default=2,
                        help='Number of workflows to create')

    parser.add_argument('-j', '--n_jobs', dest='n_jobs',
                        type=int, default=2,
                        help='# jobs to create')

    parser.add_argument('-t', '--n_tasks', dest='n_tasks',
                        type=int, default=10,
                        help='# tasks to create')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    for _ in range(args.n_workflows):
        w = factories.WorkflowFactory()

        for __ in range(args.n_jobs):
            j = factories.JobFactory(workflow=w)
            for ___ in range(args.n_tasks):
                factories.TaskFactory(job=j)
    print("Database populated successfully")
