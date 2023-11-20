from django.urls import reverse
from django.test import TestCase

from ..factories import WorkflowFactory
from abc_impute.api.models import Job


class TestJobsDetail(TestCase):
    def test_queue_lock(self):
        workflow = WorkflowFactory(is_active=False)

        url = reverse('apiv2:jobs-list')
        resp = self.client.post(url, {
            'run_id': 'atest',
            'workflow': workflow.pk,
            'params': {},
            'owner': 'tester@test.example',
        })

        self.assertTrue(resp.status_code == 423, 'queue is locked')
        self.assertEqual(
            Job.objects.filter(run_id='atest', workflow_id__lt=workflow.pk).count(),
            0,
            'Job was not created because workflow is not accepting submissions'
        )
