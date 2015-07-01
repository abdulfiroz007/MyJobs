import imp
import os
from unittest import TestCase

from selenium import webdriver

from django.conf import settings

from functional_tests.test_mypartners import SeleniumTestCase
from myjobs.tests.factories import UserFactory
from myjobs.models import User
from seo.tests import patch_settings


class JobPostingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.OVERRIDES = {}
        cls.test_url = 'localhost:8000'
        cls.browser = webdriver.PhantomJS()
        environment = os.environ.get('SETTINGS', '').lower()
        if environment == 'qc':
            print 'Running test_posting with QC settings'
            cls.test_url = 'qc.www.my.jobs'
            qc = imp.load_source('settings.myjobs_qc',
                                 'deploy/settings.myjobs_qc.py')
            cls.OVERRIDES = vars(qc)
        elif environment == 'staging':
            print 'Running test_posting with staging settings'
            cls.test_url = 'staging.www.my.jobs'
            staging = imp.load_source('settings.myjobs_staging',
                                      'deploy/settings.myjobs_staging.py')
            cls.OVERRIDES = vars(staging)
        else:
            print 'Running test_posting with settings.py'
        super(JobPostingTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(JobPostingTests, cls).tearDownClass()

    def test_show_job_admin(self):
        with patch_settings(**self.OVERRIDES):
            print settings.ENVIRONMENT
