from default_settings import *
import datetime
import os

DEBUG = True

DATABASES = {
    'default': {
        'NAME': 'myjobs.db',
        'ENGINE': 'django.db.backends.sqlite3',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

TEST_RUNNER = 'testrunner.SilentTestRunner'

SOLR = {
    'default': '127.0.0.1:8983/solr/myjobs-test/',
}
