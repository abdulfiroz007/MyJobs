import datetime
from urlparse import urlparse
from urllib import unquote

from django.core import serializers
from django.db import IntegrityError
from django.conf.urls import patterns, url
from django.contrib.auth import authenticate, login

from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication
from tastypie.exceptions import BadRequest, ImmediateHttpResponse
from tastypie.http import HttpBadRequest, HttpResponse
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer
from tastypie.utils import trailing_slash
from tastypie.validation import Validation

from myjobs.models import User
from mysearches.forms import SavedSearchForm
from mysearches.helpers import validate_dotjobs_url
from mysearches.models import SavedSearch
from registration import signals as custom_signals

        
class UserResource(ModelResource):
    searches = fields.ToManyField('myjobs.api.SavedSearchResource',
                                  'savedsearch_set')
    class Meta:
        filtering = {"email": "exact"}
        queryset = User.objects.all()
        resource_name = 'user'
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        authentication = ApiKeyAuthentication()
        always_return_data = True
        serializer = Serializer(formats=['json', 'jsonp'],
                                content_types={'json':'application/json', 'jsonp': 'text/javascript'})

    def create_response(self, request, data, response_class=HttpResponse, **response_kwargs):
        """
        Intercepts the default create_reponse(). Checks for existing user
        and creates a new user if one matching the email doesn't exist.

        Creates new JSON formatted "data" based on the success, failure, 
        or error in suer creation. Returns new data to the default 
        create_response(). 

        """
        email = request.GET.get('email', '')
        if not email:
            data = {'email': 'No email provided'}
            return super(UserResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)  

        try:
            kwargs = {'email': email,
                      'password1': request.GET.get('password', '')}
            user, created = User.objects.create_inactive_user(**kwargs)

            data = {
                'user_created': created,
                'email': email
                }
        except IntegrityError:
            data = {'email': 'That username already exists'}

        return super(UserResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)


    def obj_create(self, bundle, **kwargs):
        email = User.objects.normalize_email(bundle.data.get('email'))
        if not email:
            error = {'email': 'No email provided'}
            raise ImmediateHttpResponse(self.error_response(
                                            bundle.request,
                                            error,
                                            response_class=HttpBadRequest))
        try:
            kwargs = {'email': email,
                      'password1': bundle.data.get('password')}
            user, created = User.objects.create_inactive_user(**kwargs)

            bundle.obj = user
            bundle.data = {
                'user_created': created,
                'email': bundle.data.get('email')
                }
            return bundle
        except IntegrityError:
            error = {'email': 'That username already exists'}
            raise ImmediateHttpResponse(self.error_response(
                                            bundle.request,
                                            error,
                                            response_class=HttpBadRequest))

class CustomSearchValidation(Validation):
    def is_valid(self, bundle, request):
        if not bundle.data:
            return {'__all__':'No information provided'}

        errors = {}

        email = bundle.data.get('email')
        if not email:
            errors['email'] = 'No email provided'
        else:
            user = User.objects.get_email_owner(email=email)
            if not user:
                errors['email'] = 'No user with email %s exists' % email

        url = bundle.data.get('url', '')
        url = unquote(url)
        if not url:
            errors['url'] = 'No .JOBS feed provided'
        else:
            label, feed = validate_dotjobs_url(url)
            if not (label and feed):
                errors['url'] = 'This is not a valid .JOBS feed'
            else:
                bundle.data['label'] = label
                bundle.data['feed'] = feed
        
        frequency = bundle.data.get('frequency')
        day_of_month = bundle.data.get('day_of_month')
        day_of_week = bundle.data.get('day_of_week')
        if not frequency:
            bundle.data['frequency'] = 'D'
        elif frequency == 'W':
            if not day_of_week:
                errors['day_of_week'] = 'Must supply day_of_week'
            elif day_of_week not in map(str, range(1,8)):
                errors['day_of_week'] = 'day_of_week %s outside range ' \
                                        '"1".."7"' % day_of_week
        elif frequency == 'M':
            if not day_of_month:
                errors['day_of_month'] = 'Must supply day_of_month'
            elif day_of_month not in range(1,31):
                errors['day_of_month'] = 'day_of_month %s outside range ' \
                                        '1..30' % day_of_month
        return errors

class SavedSearchResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    class Meta:
        filtering = {"email": "exact", "url": "exact"}
        queryset = SavedSearch.objects.all()
        resource_name = 'savedsearch'
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        authentication = ApiKeyAuthentication()
        always_return_data = True
        serializer = Serializer(formats=['json', 'jsonp'],
                                content_types={'json':'application/json', 'jsonp': 'text/javascript'})
        validation = CustomSearchValidation()

    def create_response(self, request, data, response_class=HttpResponse, **response_kwargs):
        """
        Intercepts the default create_reponse(). Checks for existing saved
        search matching the user and url. If one doesn't exist, it creates
        a new saved search with daily email and the date/time created in
        the notes. 

        Creates new JSON formatted "data" based on the success, failure, or 
        error in saved search creation. Returns this data to the default 
        create_response(). 

        """

        # Confirm email was provided, and that the user exists
        email = request.GET.get('email', '')        
        if not email:
            data = {'email': 'No email provided'}
            return super(SavedSearchResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)
        else:
            user = User.objects.get_email_owner(email=email)
            if not user:
                data = {'email': 'No user with email %s exists' % email}
                return super(SavedSearchResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)

        # Confirm that url was provided, and that it's a valid .jobs search
        url = request.GET.get('url', '')
        url = unquote(url)
        if not url:
            data = {'url': 'No .JOBS feed provided'}
            return super(SavedSearchResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)
        else:
            label, feed = validate_dotjobs_url(url)
            if not (label and feed):
                data = {'url': 'This is not a valid .JOBS feed'}
                return super(SavedSearchResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)

        # Create notes field noting that it was created as current date/time
        now = datetime.datetime.now().strftime('%A, %B %d, %Y %l:%M %p')
        notes = 'Saved on ' + now
        if url.find('//') == -1:
            url = 'http://' + url
        netloc = urlparse(url).netloc
        notes += ' from ' + netloc

        search_args = {'url': url,
                       'label': label,
                       'feed': feed,
                       'user': user,
                       'email': email,
                       'frequency': 'D',
                       'day_of_week': None,
                       'day_of_month': None,
                       'notes': notes}
        new_search = False

        # if there's no search for that email/user, create it
        try:
            search = SavedSearch.objects.get(user=search_args['user'],
                                             email__iexact=search_args['email'],
                                             url=search_args['url'])
        except SavedSearch.DoesNotExist:
            search = SavedSearch(**search_args)
            search.save()
            new_search = True

        data = {'email': email,
                'frequency': 'D',
                'new_search': new_search}

        return super(SavedSearchResource, self).create_response(request, data, response_class=HttpResponse, **response_kwargs)

    def obj_create(self, bundle, **kwargs):
        """
        Overrides object create method. Runs validation, sets timestamp in
        note field and either gets the existing object or creates it.

        Returns JSON with the email, frequency, and the new_search boolean
        indicating if the search was created or not. A 400 error is
        raised if the URL has been used by the user already.
        """
        self.is_valid(bundle)
        email = User.objects.normalize_email(bundle.data.get('email'))
        if bundle.errors:
            raise ImmediateHttpResponse(self.error_response(
                                            bundle.request,
                                            bundle.errors['savedsearch'],
                                            response_class=HttpBadRequest))
        user = User.objects.get_email_owner(email)
        notes = bundle.data.get('notes', '')
        if not notes:
            # Monday, April 29, 2013 10:26 AM
            now = datetime.datetime.now().strftime('%A, %B %d, %Y %l:%M %p')
            notes += 'Saved on ' + now
            if bundle.request:
                url = bundle.data.get('url')
                if url.find('//') == -1:
                    url = 'http://' + url
                netloc = urlparse(url).netloc
                notes += ' from ' + netloc
            bundle.data['notes'] = notes

        search_args = {'url': url,
                       'label': bundle.data.get('label'),
                       'feed': bundle.data.get('feed'),
                       'user': user,
                       'email': email,
                       'frequency': bundle.data.get('frequency'),
                       'day_of_week': bundle.data.get('day_of_week'),
                       'day_of_month': bundle.data.get('day_of_month'),
                       'notes': notes}

        new_search = False
        try:
            search = SavedSearch.objects.get(user=search_args['user'],
                                             email__iexact=search_args['email'],
                                             url=search_args['url'])
        except SavedSearch.DoesNotExist:
            search = SavedSearch(**search_args)
            search.save()
            new_search = True

        bundle.obj = search
        bundle.data = {'email': bundle.data.get('email'),
                       'frequency': bundle.data.get('frequency', 'D'),
                       'new_search': new_search}
        return bundle

