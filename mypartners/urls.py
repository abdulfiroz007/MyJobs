from django.conf.urls import patterns, url
from django.views.generic import RedirectView

urlpatterns = patterns('MyJobs.mypartners.views',
    url(r'^$', RedirectView.as_view(url='/partners/view/')),
    url(r'^view/$', 'prm', name='prm'),
    url(r'^view$', 'prm', name='prm'),
    url(r'^view/overview$', 'prm_overview', name='partner_overview'),
    url(r'^view/records$', 'prm_records', name='partner_records'),
    url(r'^view/records/edit$', 'prm_edit_records', name='partner_edit_record'),
    url(r'^view/records/retrieve_records', 'partner_get_records',
        name="partner_get_records"),
    url(r'^view/records/view$', 'prm_view_records', name='record_view'),
    url(r'^view/records/update$', 'get_records', name='get_records'),
    url(r'^view/records/contact_info$', 'get_contact_information',
        name='get_contact_information'),
    url(r'^view/searches$', 'prm_saved_searches', name='partner_searches'),
    url(r'^view/searches/edit$', 'prm_edit_saved_search',
        name='partner_edit_search'),
    url(r'^view/searches/verify-contact/$', 'verify_contact',
        name='verify_contact'),
    url(r'^view/searches/save', 'partner_savedsearch_save',
        name='partner_savedsearch_save'),
    url(r'^view/searches/feed', 'partner_view_full_feed',
        name='partner_view_full_feed'),
    url(r'^view/save$', 'save_init_partner_form',
        name='save_init_partner_form'),
    url(r'^view/details$', 'partner_details', name='partner_details'),
    url(r'^view/edit$', 'edit_item', name='create_partner'),
    url(r'^view/details/edit$', 'edit_item', name='edit_contact'),
    url(r'^view/details/save$', 'save_item', name='save_item'),
    url(r'^view/details/delete$', 'delete_prm_item', name='delete_prm_item'),
    url(r'^download/', 'get_uploaded_file', name='get_uploaded_file'),
)