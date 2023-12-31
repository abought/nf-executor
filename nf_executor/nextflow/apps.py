"""Nextflow-specific infrastructure"""

from django.apps import AppConfig


class NextflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nf_executor.nextflow'
