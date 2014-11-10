import datetime

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse

from myjobs.tests.setup import MyJobsBase
from myjobs.models import User
from myjobs.tests.test_views import TestClient
from mypartners.models import Contact
from mypartners.tests.factories import PartnerFactory
from myprofile.models import SecondaryEmail
from mysearches.models import SavedSearch
from registration.models import ActivationProfile


class RegistrationViewTests(MyJobsBase):
    """
    Test the registration views.

    """

    def setUp(self):
        """
        These tests use the default backend, since we know it's
        available; that needs to have ``ACCOUNT_ACTIVATION_DAYS`` set.

        """
        super(RegistrationViewTests, self).setUp()
        self.client = TestClient()
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = 7  # pragma: no cover

        self.data = {'email': 'alice@example.com',
                     'password1': 'swordfish',
                     'send_email': True}
        self.user, _ = User.objects.create_user(**self.data)

    def test_valid_activation(self):
        """
        Test that the ``activate`` view properly handles a valid
        activation (in this case, based on the default backend's
        activation window).

        """
        self.client.login_user(self.user)
        profile = ActivationProfile.objects.get(user__email=self.user.email)
        response = self.client.get(reverse('registration_activate',
                                           args=[profile.activation_key]))
        self.assertEqual(response.status_code, 200)
        self.failUnless(User.objects.get(email=self.user.email).is_active)

    def test_anonymous_activation(self):
        """
        Test that the ``activate`` view properly handles activation
        when the user to be activated is not currently logged in.
        """
        self.client.post(reverse('auth_logout'))
        profile = ActivationProfile.objects.get(user__email=self.user.email)
        response = self.client.get(reverse('registration_activate',
                                           args=[profile.activation_key]) +
                                   '?verify=%s' % self.user.user_guid)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.data['email'])

    def test_invalid_activation(self):
        """
        Test that the ``activate`` view properly handles an invalid
        activation (in this case, based on the default backend's
        activation window).

        """
        self.client.login_user(self.user)
        expired_profile = ActivationProfile.objects.get(user=self.user)
        expired_profile.sent -= datetime.timedelta(
            days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_profile.save()
        response = self.client.get(reverse('registration_activate',
                                           args=[expired_profile.activation_key]))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.context['activated'],
                            expired_profile.activation_key_expired())
        self.failIf(User.objects.get(email=self.user.email).is_verified)

    def test_resend_activation(self):
        x, created = User.objects.create_user(
            **{'email': 'alice@example.com', 'password1': 'secret'})
        self.client.login_user(x)
        self.assertEqual(len(mail.outbox), 1)
        resp = self.client.get(reverse('resend_activation'))
        self.assertEqual(resp.status_code, 200)
        # one email sent for creating a user, another one for resend
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_activation_with_secondary_emails(self):
        user, created = User.objects.create_user(
            email='alice@example.com', password1='secret',
            create_user=True)
        self.assertEqual(ActivationProfile.objects.count(), 1)

        self.client.login_user(user)
        self.client.get(reverse('resend_activation'))
        self.assertEqual(len(mail.outbox), 2)

        SecondaryEmail.objects.create(user=user, email='test@example.com')
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(ActivationProfile.objects.count(), 2)
        self.client.get(reverse('resend_activation'))
        self.assertEqual(len(mail.outbox), 4)

    def test_site_name_in_password_reset_email(self):
        mail.outbox = []
        self.user.is_active = True
        self.user.save()
        self.client.post(reverse('password_reset'),
                         data={'email': self.user.email})
        self.assertEqual(len(mail.outbox), 1,
                         [msg.subject for msg in mail.outbox])
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "Password Reset on My.jobs")
        self.assertIn("The My.jobs Team", msg.body)
        self.assertIn("user account at My.jobs.", msg.body)

    def test_inactive_user_requesting_password_reset(self):
        """
        Requesting a password reset as an inactive user should activate the
        account, allowing the password reset to proceed.
        """
        self.user.is_active = False
        self.user.save()

        self.client.post(reverse('password_reset'), {'email': self.user.email})
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.is_active)

class MergeUserTests(MyJobsBase):

    def setUp(self):
        super(MergeUserTests, self).setUp()
        self.client = TestClient()
        self.password = '12345'
        self.key = '56effea3df2bcdcfe377ca4bf30f2844be47d012'
        self.existing = User.objects.create(email="test@email.com",
                                            user_guid="a")
        self.existing.set_password(self.password)
        self.new_user = User.objects.create(email="new@email.com",
                                            user_guid="b")
        self.activation_profile = ActivationProfile.objects.create(
            user=self.new_user,
            email="ap@email.com")
        self.activation_profile.activation_key = self.key
        self.activation_profile.save()

        self.partner = PartnerFactory()
        for _ in range(0, 10):
            Contact.objects.create(user=self.new_user, partner=self.partner)
            SavedSearch.objects.create(user=self.new_user)

    def test_expired_key_doesnt_merge(self):
        expired_request = self.activation_profile
        expired_request.sent -= datetime.timedelta(
            days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_request.save()

        self.client.login_user(self.existing)
        merge_url = reverse('merge_accounts',
                            kwargs={'activation_key': self.key})
        response = self.client.get(merge_url)

        self.assertTrue(
            User.objects.filter(email=self.new_user.email).exists(),
            msg="The new user should not have been deleted.")

        self.assertEqual(response.status_code, 200,
            msg=("The page should have returned a 200 code." \
            "Instead received %s" % response.status_code))

        phrases = [
            'Something went wrong while merging your account.',
            "The activation code was wrong",
            "Your account has already been merged",
            "You waited longer than 2 weeks to activate your account"]
        for phrase in phrases:
            self.assertIn(phrase, response.content, msg=\
                "The phrase '%s' is missing from the final response" % phrase)

    def test_invalid_key_doesnt_merge(self):
        self.client.login_user(self.existing)

        key = self.key.replace('5', 'b')
        merge_url = reverse('merge_accounts', kwargs={'activation_key': key})
        response = self.client.get(merge_url)

        self.assertTrue(
            User.objects.filter(email=self.new_user.email).exists(),
            msg="The new user should not have been deleted.")

        self.assertEqual(response.status_code, 200,
            msg=("The page should have returned a 200 code." \
            "Instead received %s" % response.status_code))

        phrases = [
            'Something went wrong while merging your account.',
            "The activation code was wrong",
            "Your account has already been merged",
            "You waited longer than 2 weeks to activate your account"]
        for phrase in phrases:
            self.assertIn(phrase, response.content, msg=\
                "The phrase '%s' is missing from the final response" % phrase)

    def test_successfully_merged_account(self):
        self.client.login_user(self.existing)

        # Access the merge URL
        merge_url = reverse('merge_accounts',
                            kwargs={'activation_key': self.key})
        response = self.client.get(merge_url)

        self.assertEqual(response.status_code, 200,
            msg=("The page should have returned a 200 code." \
            "Instead received %s" % response.status_code))

        # Assert the correct text is displayed.
        phrases = [
            'Your account has been successfully merged, and you are'\
            ' now logged in.',
            "Add to your resume",
            "Manage your saved searches",
            "Manage your account"]
        for phrase in phrases:
            self.assertIn(phrase, response.content, msg=\
                "The phrase '%s' is missing from the final response" % phrase)

        # Assert the new user doesn't exist.
        self.assertFalse(
            User.objects.filter(email=self.new_user.email).exists(),
            msg="The new user should have been deleted.")

        # Assert the new email address is associated with the existing user
        self.assertTrue(
            SecondaryEmail.objects.filter(user=self.existing,
                email=self.activation_profile.email).exists(),
                msg="A secondary email should have been added "\
                "for the deleted user account")

        # Assert the contacts associated with the new user now point to the
        # existing user
        self.assertEqual(Contact.objects.all().count(), 10,
            msg="The Contacts should not have been deleted.")
        for contact in Contact.objects.all():
            self.assertEqual(contact.user, self.existing,
                msg="The contacts were not moved to the existing contact")

        # Assert the saved searches associated with the new user now point to
        # the existing user
        self.assertEqual(SavedSearch.objects.all().count(), 10,
            msg="The SavedSearches should not have been deleted.")
        for search in SavedSearch.objects.all():
            self.assertEqual(search.user, self.existing,
                msg="The contacts were not moved to the existing contact")
