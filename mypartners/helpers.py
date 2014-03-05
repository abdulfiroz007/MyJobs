from django.contrib.admin.models import CHANGE
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils.safestring import mark_safe
from django.utils.text import get_text_list, force_unicode, force_text
from django.utils.translation import ugettext

from datetime import datetime, time
from urlparse import urlparse, parse_qsl, urlunparse
from urllib import urlencode

from mydashboard.models import Company
from mypartners.models import ContactLogEntry, ContactRecord
from mysearches.models import PartnerSavedSearch


def prm_worthy(request):
    """
    Makes sure the User is worthy enough to use PRM.

    """
    company_id = request.REQUEST.get('company')
    company = get_object_or_404(Company, id=company_id)

    user = request.user
    if not user in company.admins.all():
        raise Http404

    partner_id = int(request.REQUEST.get('partner'))
    partner = get_object_or_404(company.partner_set, id=partner_id)

    return company, partner, user


def add_extra_params(url, extra_urls):
    """
    Adds extra parameters to a url

    Inputs:
    :url: Url that parameters will be added to
    :extra_urls: Extra parameters to be added

    Outputs:
    :url: Input url with parameters added
    """
    extra_urls = extra_urls.lstrip('?&')
    new_queries = dict(parse_qsl(extra_urls, keep_blank_values=True))

    # By default, extra parameters besides vs are discarded by the redirect
    # server. We can get around this by adding &z=1 to the url, which enables
    # custom query parameter overrides.
    new_queries['z'] = '1'

    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4], keep_blank_values=True))
    query.update(new_queries)
    parts[4] = urlencode(query)
    return urlunparse(parts)


def add_extra_params_to_jobs(items, extra_urls):
    """
    Adds extra parameters to all jobs in a list

    Inputs:
    :items: List of jobs to which extra parameters should be added
    :extra_urls: Extra parameters to be added

    Modifies:
    :items: List is mutable and is modified in-place
    """
    for item in items:
        item['link'] = add_extra_params(item['link'], extra_urls)


def log_change(obj, form, user, partner, contact_identifier,
               action_type=CHANGE):
    change_msg = get_change_message(form) if action_type == CHANGE else ''

    ContactLogEntry.objects.create(
        action_flag=action_type,
        change_message=change_msg,
        contact_identifier=contact_identifier,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        object_repr=force_text(obj)[:200],
        partner=partner,
        user=user,
    )


def get_change_message(form):
    change_message = []
    if form.changed_data:
        change_message = (ugettext('Changed %s.') %
                          get_text_list(form.changed_data, ugettext('and')))
    return change_message or ugettext('No fields changed.')


def get_searches_for_partner(partner):
    company = partner.owner
    partner_contacts = partner.contacts.all().values_list('user__id', flat=True)
    saved_searches = PartnerSavedSearch.objects.filter(
        provider=company, user__in=partner_contacts).order_by('-created_on')
    return saved_searches


def get_logs_for_partner(partner, content_type_id=None, num_items=10):
    logs = ContactLogEntry.objects.filter(partner=partner)
    if content_type_id:
        logs = logs.filter(content_type_id=content_type_id)
    return logs.order_by('-action_time')[:num_items]


def get_contact_records_for_partner(partner, contact_name=None,
                                    record_type=None, date_time_range=[],
                                    offset=None, limit=None):
    records = ContactRecord.objects.filter(partner=partner)
    if contact_name:
        records = records.filter(contact_name=contact_name)
    if date_time_range:
        records = records.filter(date_time__range=date_time_range)
    if record_type:
        records = records.filter(contact_type=record_type)
    return records[offset:limit]


def get_attachment_link(company_id, partner_id, attachment_id, attachment_name):
    url = '/prm/download?company=%s&partner=%s&id=%s' % (company_id,
                                                         partner_id,
                                                         attachment_id)

    html = "<a href='{url}' target='_blank'>{attachment_name}</a>"
    return mark_safe(html.format(url=url, attachment_name=attachment_name))

def retrieve_fields(model):
    fields = [field for field in model._meta.get_all_field_names()
              if unicode(field) not in [u'id', u'prmattachment']]
    return fields


def contact_record_val_to_str(value):
    return (value.strftime('%b %d, %Y %I:%M %p') if type(value)
            is datetime else value.strftime('%H hours %M minutes')
            if type(value) is time else force_unicode(value))