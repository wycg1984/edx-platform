from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from courseware.tests.tests import LoginEnrollmentTestCase
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from xmodule.modulestore.django import modulestore

from mock import patch


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class WikiRedirectTestCase(LoginEnrollmentTestCase):

    def setUp(self):

        # Load the toy course
        self.toy = modulestore().get_course('edX/toy/2012_Fall')

        # Create two accounts
        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)

    @patch.dict("django.conf.settings.FEATURES", {'ALLOW_WIKI_ROOT_ACCESS': True})
    def test_wiki_redirect(self):
        """
        Test that requesting wiki URLs redirect properly to or out of classes.

        An enrolled in student going from /courses/edX/toy/2012_Fall/progress
        to /wiki/some/fake/wiki/page/ will redirect to
        /courses/edX/toy/2012_Fall/wiki/some/fake/wiki/page/

        An unenrolled student going to /courses/edX/toy/2012_Fall/wiki/some/fake/wiki/page/
        will be redirected to /wiki/some/fake/wiki/page/

        """
        self.login(self.student, self.password)

        self.enroll(self.toy)

        referer = reverse("progress", kwargs={'course_id': self.toy.id})
        destination = reverse("wiki:get", kwargs={'path': 'some/fake/wiki/page/'})

        redirected_to = referer.replace("progress", "wiki/some/fake/wiki/page/")

        resp = self.client.get(destination, HTTP_REFERER=referer)
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(resp['Location'], 'http://testserver' + redirected_to)


        # Now we test that the student will be redirected away from that page if the course doesn't exist
        # We do this in the same test because we want to make sure the redirected_to is constructed correctly

        # This is a location like /courses/*/wiki/* , but with an invalid course ID
        bad_course_wiki_page = redirected_to.replace(self.toy.location.course, "bad_course")

        resp = self.client.get(bad_course_wiki_page, HTTP_REFERER=referer)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver' + destination)

    @patch.dict("django.conf.settings.FEATURES", {'ALLOW_WIKI_ROOT_ACCESS': False})
    def test_wiki_no_root_access(self):
        """
        Test to verify that normally Wiki's cannot be browsed from the /wiki/xxxx/yyy/zz URLs

        """
        self.login(self.student, self.password)

        self.enroll(self.toy)

        referer = reverse("progress", kwargs={'course_id': self.toy.id})
        destination = reverse("wiki:get", kwargs={'path': 'some/fake/wiki/page/'})

        resp = self.client.get(destination, HTTP_REFERER=referer)
        self.assertEqual(resp.status_code, 403)

    def create_course_page(self, course):
        """
        Test that loading the course wiki page creates the wiki page.
        The user must be enrolled in the course to see the page.
        """

        course_wiki_home = reverse('course_wiki', kwargs={'course_id': course.id})
        referer = reverse("progress", kwargs={'course_id': self.toy.id})

        resp = self.client.get(course_wiki_home, follow=True, HTTP_REFERER=referer)

        course_wiki_page = referer.replace('progress', 'wiki/' + self.toy.wiki_slug + "/")

        ending_location = resp.redirect_chain[-1][0]
        ending_status = resp.redirect_chain[-1][1]

        self.assertEquals(ending_location, 'http://testserver' + course_wiki_page)
        self.assertEquals(resp.status_code, 200)

        self.has_course_navigator(resp)

    def has_course_navigator(self, resp):
        """
        Ensure that the response has the course navigator.
        """
        self.assertContains(resp, "Course Info")
        self.assertContains(resp, "courseware")

    @patch.dict("django.conf.settings.FEATURES", {'ALLOW_WIKI_ROOT_ACCESS': True})
    def test_course_navigator(self):
        """"
        Test that going from a course page to a wiki page contains the course navigator.
        """

        self.login(self.student, self.password)
        self.enroll(self.toy)
        self.create_course_page(self.toy)

        course_wiki_page = reverse('wiki:get', kwargs={'path': self.toy.wiki_slug + '/'})
        referer = reverse("courseware", kwargs={'course_id': self.toy.id})

        resp = self.client.get(course_wiki_page, follow=True, HTTP_REFERER=referer)

        self.has_course_navigator(resp)

    @patch.dict("django.conf.settings.FEATURES", {'ALLOW_WIKI_ROOT_ACCESS': True})
    def test_wiki_not_accessible_when_not_enrolled(self):
        """"
        Test that going from a course page to a wiki page contains the course navigator.
        """

        self.login(self.instructor, self.password)
        self.enroll(self.toy)
        self.create_course_page(self.toy)

        self.login(self.student, self.password)
        course_wiki_page = reverse('wiki:get', kwargs={'path': self.toy.wiki_slug + '/'})
        referer = reverse("courseware", kwargs={'course_id': self.toy.id})

        resp = self.client.get(course_wiki_page, follow=True, HTTP_REFERER=referer)

        self.assertEquals(resp.status_code, 403)
