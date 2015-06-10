# -*- coding: utf-8 -*-
import os

from django.conf import settings

from seo_pysolr import Solr
from import_jobs import (DATA_DIR, add_company, remove_expired_jobs, update_solr, get_jobs_from_zipfile,
    filter_current_jobs)

from seo.models import BusinessUnit, Company
from seo.tests.factories import BusinessUnitFactory, CompanyFactory
from setup import DirectSEOBase


class ImportJobsTestCase(DirectSEOBase):
    fixtures = ['import_jobs_testdata.json']

    def setUp(self):
        super(ImportJobsTestCase, self).setUp()
        self.businessunit = BusinessUnitFactory(id=0)
        self.buid_id = self.businessunit.id        
        self.filepath = os.path.join(DATA_DIR, '0', 'dseo_feed_%s.xml' % self.buid_id)
        self.solr_settings = {
            'default': {'URL': 'http://127.0.0.1:8983/solr/seo'}
        }
        self.solr = Solr(settings.HAYSTACK_CONNECTIONS['default']['URL'])

    def tearDown(self):
        super(ImportJobsTestCase, self).tearDown()
        self.solr.delete(q='*:*')

    def test_solr_rm_feedfile(self):
        """
        Test that at the end of Solr parsing, the feed file is deleted.
        
        """
        update_solr(self.buid_id)
        self.assertFalse(os.access(self.filepath, os.F_OK))

    def test_subsidiary_rename(self):
        company1 = CompanyFactory()
        company1.save()
        bu1 = self.businessunit
        bu1.title = "Acme corp"
        bu2 = BusinessUnitFactory(title=bu1.title)
        bu2.save()
        self.businessunit.company_set.add(company1)

        # Test that a company was created for both business units
        add_company(bu1)
        companies = bu1.company_set.all()
        self.assertEqual(len(companies), 1)
        co = companies[0]
        self.assertEqual(co.name, bu1.title)

        # Add the 2nd business unit
        add_company(bu2)

        # Both units should be attached to that company
        self.assertEqual(bu1.company_set.all()[0], bu2.company_set.all()[0])
        self.assertEqual(bu1.company_set.all().count(), 1) 
        self.assertIn(bu1, co.job_source_ids.all())
        self.assertIn(bu2, co.job_source_ids.all())
        self.assertEqual(co.name, bu1.title)
        self.assertEqual(co.name, bu2.title)

        bu2.title = "New company name"
        add_company(bu1)
        add_company(bu2)
        self.assertEqual(len(co.job_source_ids.all()), 1)
        self.assertNotEqual(bu1.company_set.all(), bu2.company_set.all())
        self.assertEqual(co.name, bu1.title)
        self.assertEqual(len(bu2.company_set.all()), 1)
        co2 = bu2.company_set.all()[0]
        self.assertEqual(co2.name, bu2.title)
        self.assertNotEqual(co2.name, bu1.title)
        self.assertNotEqual(co.name, bu2.title)

    def test_duplicate_company(self):
        company1 = CompanyFactory()
        company1.save()
        company2 = CompanyFactory(name="Acme corp")
        company2.save()
        self.businessunit.company_set.add(company1)
        self.businessunit.title = "Acme corp"
        add_company(self.businessunit)
        self.assertEqual(self.businessunit.company_set.all()[0], company2)

    def test_set_bu_title(self):
        """
        Ensure that if a feedfile for a BusinessUnit comes through, and
        the `title` attribute for that BusinessUnit is not set, that
        `helpers.update_solr` sets the `title` attribute properly.

        """
        bu = BusinessUnit.objects.get(id=self.buid_id)
        bu.title = None
        bu.save()
        # Since the BusinessUnit title is None, the intent is that update_solr
        # will set its title to match the company name found in the feed file.
        results = update_solr(self.buid_id)
        # We have to get the updated state of the BusinessUnit instance, since
        # changes to the database won't be reflected by our in-memory version of
        # the data.
        bu = BusinessUnit.objects.get(id=self.buid_id)
        # The title attribute should now equal the initial value established in
        # the setUp method.
        self.assertEquals(self.businessunit.title, bu.title)

    def test_add_company(self):
        """
        Create environment to test for every possible case--
        
         - Existing relationship but the name is different                 pk=10
         - No existing relationship, but the company exists in the database (as
           established by the BusinessUnit title matching a company name)  pk=11
         - No relationship and the company is not in the database          pk=12
          
        Start with  2 Company objects and 3 BusinessUnit objects
        End up with 3 Company objects and 3 BusinessUnit objects

        """

        for i in range(10, 4):
            add_company(BusinessUnit.get(id=i))

            # The names of the BU and the Co should be the same
            self.assertEquals(BusinessUnit.get(id=i).title,
                              Company.get(id=i).name,
                              msg="Company names do not match")

            # ensure the relationship was formed
            self.assertIn(Company.objects.get(id=i),
                          BusinessUnit.objects.get(id=i).company_set.all(),
                          msg="Company is not related to job feed")

    def test_remove_expired_jobs(self):
        buid = 12345
        active_jobs = [{'id': 'seo.%s' % i, 'buid': buid} for i in range(4)]
        old_jobs = [{'id': 'seo.%s' % i, 'buid': buid} for i in range(2, 10)]

        with self.settings(HAYSTACK_CONNECTIONS=self.solr_settings):
            self.solr.add(old_jobs)
            self.solr.commit()

            removed = remove_expired_jobs(buid, active_jobs)
            self.assertEqual(len(removed), 6, "Removed jobs %s" % removed)
            ids = [d['id'] for d in self.solr.search('*:*').docs]
            self.assertTrue([5, 6, 7, 8, 9, 10] not in ids)

    def test_remove_jobs_from_etl(self):
        etl_jobs = [{'id': 'seo.%s' % i, 'buid': self.buid_id} for i in range(2, 10)]
        self.solr.add(etl_jobs)
        self.solr.commit()
        
        update_solr(self.buid_id)
        
        etl_ids = set([d['id'] for d in etl_jobs])
        ids = set([d['id'] for d in self.solr.search('*:*').docs])
        self.assertGreater(len(ids), 0, "No jobs were found for the business unit.")
        self.assertEqual(len(etl_ids & ids), 0, "Jobs without uids are not being removed.")


class LoadETLTestCase(DirectSEOBase):
    def setUp(self):
        
        self.zipfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'data',
                                    'ActiveDirectory_ce2ca701-eeca-4c13-96ba-e6bde9cb7060.zip') 
        
        with open(self.zipfile) as zf:
            self.jobs = list(get_jobs_from_zipfile(zf, "ce2ca701-eeca-4c13-96ba-e6bde9cb7060"))
            
        self.businessunit = BusinessUnitFactory(id=0)
    
    def tearDown(self):
        pass
    
    def test_filtering_on_includeinindex_bit(self):
        """Test that filtering on the include_in_index bit works"""
        
        #Prove we have the expected number of jobs in the zipfile itself.
        self.assertEqual(len(self.jobs), 39, 
                         "Expected to find 0 jobs in the test zipfile, instead found %s" % len(self.jobs))
        
        # Prove that filtering works.
        filtered_jobs = list(filter_current_jobs(self.jobs, self.businessunit))
        self.assertEqual(len(filtered_jobs), 38,
                         "filter_current_jobs should rmeove jobs with the includeinindex bit set, "
                         "it's expected to return %s.  Instead it returned %s" % (38, len(filtered_jobs)))
        
    
    def test_businessunit_ignore_includeinindex(self):
        """Test that filtering on the include_in_index bit can be overridden on a per business unit basis."""
        # Set ignore_includeinindex on the test BusinessUnit
        self.businessunit.ignore_includeinindex = True
        self.businessunit.save()
        
        #Prove we have the expected number of jobs in the zipfile itself.
        self.assertEqual(len(self.jobs), 39, 
                         "Expected to find 0 jobs in the test zipfile, instead found %s" % len(self.jobs))
        
        # Prove that filtering works.
        filtered_jobs = list(filter_current_jobs(self.jobs, self.businessunit))
        self.assertEqual(len(filtered_jobs), 39,
                         "filter_current_jobs should ignore the includeinindex bit, returning 39 jobs.  "
                         "Instead returned %s." % len(filtered_jobs))
