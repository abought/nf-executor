# Generated by Django 4.2.3 on 2023-11-03 21:24

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import nf_executor.api.enums
import nf_executor.api.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('run_id', models.CharField(db_index=True, default=None, help_text='Unique-per-workflow run ID provided to the executor. If a job is restarted, specify a new ID.', max_length=40)),
                ('params', models.JSONField(blank=True, default=dict, help_text='User-specified params unique to this workflow', null=True)),
                ('storage_root', models.CharField(blank=True, help_text='Location (relative to storage root) for job-specific files that are retained after job is completed.', max_length=256, null=True)),
                ('owner', models.CharField(blank=True, db_index=True, help_text='eg User ID provided by an external service. Must not be mutable (username or ID, not email)', max_length=100, null=True)),
                ('callback_token', models.BinaryField(help_text='(simplistic) token that can be used for reporter callbacks (like nextflow)')),
                ('executor_id', models.CharField(help_text='Used to manually check job status (in case of message delivery failure). PID, AWS Batch arn, etc', max_length=50)),
                ('status', models.IntegerField(choices=[(10, 'started'), (40, 'completed'), (50, 'error'), (0, 'submitted'), (20, 'cancel_pending'), (25, 'unknown'), (30, 'canceled')], default=nf_executor.api.enums.JobStatus['submitted'])),
                ('expire_on', models.DateTimeField(default=nf_executor.api.models._future_date, help_text='30 days after submission OR 7 days after completion')),
                ('started_on', models.DateTimeField(null=True)),
                ('completed_on', models.DateTimeField(null=True)),
                ('duration', models.IntegerField(default=0, help_text='Run time of the job. AFAICT from nf source code, this is in ms')),
                ('succeed_count', models.IntegerField(default=0)),
                ('retries_count', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='JobHeartbeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('label', models.CharField(help_text='Identify the type of message being sent', max_length=50)),
                ('message', models.JSONField(default=dict, help_text='User-specified params unique to this workflow')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('task_id', models.CharField(help_text='ID used to link two event records for the same event, eg nextflow trace `task_id`', max_length=10)),
                ('native_id', models.CharField(blank=True, help_text='ID used by the underlying execution system. Allows debugging of dropped tasks, eg aws batch', max_length=100, null=True)),
                ('name', models.CharField(help_text='Task name as specified by NF', max_length=50)),
                ('status', models.IntegerField(choices=[(0, 'NEW'), (10, 'SUBMITTED'), (20, 'RUNNING'), (30, 'ABORTED'), (40, 'FAILED'), (50, 'COMPLETED')], default=nf_executor.api.enums.TaskStatus['SUBMITTED'])),
                ('exit_code', models.IntegerField(help_text='Exit code of the process (once completed)', null=True)),
                ('submitted_on', models.DateTimeField(help_text='Submit time from TRACE field of records', null=True)),
                ('started_on', models.DateTimeField(help_text='Run start time from TRACE field of records', null=True)),
                ('completed_on', models.DateTimeField(help_text='Run complete time from TRACE field of records', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(db_index=True, max_length=50)),
                ('description', models.CharField(help_text='Human readable description of workflow', max_length=100)),
                ('version', models.CharField(help_text='Workflow version', max_length=10)),
                ('definition_path', models.CharField(help_text='Depends on executor type. Folder location, container ARN, etc.', max_length=256)),
                ('definition_config', models.TextField(blank=True, help_text='Configuration options (such as nextflow.config) to be used by this workflow. This can override any nextflow.config that was provided in the workflow folder.')),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Does this workflow accept new jobs? (if False, existing jobs will be allowed to complete)')),
            ],
        ),
        migrations.AddConstraint(
            model_name='workflow',
            constraint=models.UniqueConstraint(fields=('name', 'version'), name='Name + version'),
        ),
        migrations.AddField(
            model_name='task',
            name='job',
            field=models.ForeignKey(help_text='The job that this task belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.job'),
        ),
        migrations.AddField(
            model_name='jobheartbeat',
            name='job',
            field=models.ForeignKey(help_text='The job that this message belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.job'),
        ),
        migrations.AddField(
            model_name='job',
            name='workflow',
            field=models.ForeignKey(help_text='The workflow that this job uses', null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.workflow'),
        ),
        migrations.AddConstraint(
            model_name='task',
            constraint=models.UniqueConstraint(fields=('job', 'task_id'), name='Task per job'),
        ),
        migrations.AddConstraint(
            model_name='job',
            constraint=models.UniqueConstraint(fields=('run_id', 'workflow'), name='IDs are unique per workflow'),
        ),
    ]
