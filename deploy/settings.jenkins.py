from default_settings import *
import datetime
import os


DEBUG = True


DATABASES = {
    'default': {
        'NAME': 'redirect',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'de_dbuser',
        'PASSWORD': PROD_DB_PASSWD,
        'HOST': 'db-redirectstaging.c9shuxvtcmer.us-east-1.rds.amazonaws.com',
        'PORT': '3306',
    },
}
SOLR = {
    'default': 'http://ec2-23-20-67-65.compute-1.amazonaws.com:8983/solr/myjobs_test/',
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


JENKINS_TEST_RUNNER = 'testrunner.SilentTestRunner'
TEST_SOLR_INSTANCE = SOLR['default']
CELERY_ALWAYS_EAGER = True