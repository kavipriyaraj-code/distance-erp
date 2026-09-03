from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from students.models import Student
from enquiries.models import Enquiry
from admissions.models import Admission
from universities.models import University
from courses.models import Course

User = get_user_model()


class LoginRequiredTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.counsellor = User.objects.create_user(username="coun1", password="pass123", role="counsellor")

    def test_dashboard_redirect_anonymous(self):
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 302)

    def test_students_redirect_anonymous(self):
        r = self.client.get("/students/")
        self.assertEqual(r.status_code, 302)

    def test_enquiries_redirect_anonymous(self):
        r = self.client.get("/enquiries/")
        self.assertEqual(r.status_code, 302)

    def test_admissions_redirect_anonymous(self):
        r = self.client.get("/admissions/")
        self.assertEqual(r.status_code, 302)

    def test_fees_redirect_anonymous(self):
        r = self.client.get("/fees/")
        self.assertEqual(r.status_code, 302)

    def test_reports_redirect_anonymous(self):
        r = self.client.get("/reports/")
        self.assertEqual(r.status_code, 302)

    def test_settings_redirect_anonymous(self):
        r = self.client.get("/settings/")
        self.assertEqual(r.status_code, 302)


class PublicPagesTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_landing_page(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_admission_form_page(self):
        r = self.client.get("/admission/")
        self.assertEqual(r.status_code, 200)

    def test_about_page(self):
        r = self.client.get("/about/")
        self.assertEqual(r.status_code, 200)

    def test_services_page(self):
        r = self.client.get("/services/")
        self.assertEqual(r.status_code, 200)

    def test_success_stories_page(self):
        r = self.client.get("/success-stories/")
        self.assertEqual(r.status_code, 200)

    def test_partner_universities_page(self):
        r = self.client.get("/partner-universities/")
        self.assertEqual(r.status_code, 200)

    def test_privacy_policy_page(self):
        r = self.client.get("/privacy-policy/")
        self.assertEqual(r.status_code, 200)

    def test_login_page(self):
        r = self.client.get("/login/")
        self.assertEqual(r.status_code, 200)


class DashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")

    def test_dashboard_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)

    def test_dashboard_context(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/dashboard/")
        self.assertIn("total_students", r.context)
        self.assertIn("total_admissions", r.context)
        self.assertIn("total_enquiries", r.context)


class StudentViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.student = Student.objects.create(name="Kavi", mobile="9876543210")

    def test_student_list_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/students/")
        self.assertEqual(r.status_code, 200)

    def test_student_list_search(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/students/?q=9876543210")
        self.assertEqual(r.status_code, 200)

    def test_student_profile_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get(f"/students/{self.student.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_student_create_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/students/create/")
        self.assertEqual(r.status_code, 200)

    def test_student_edit_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get(f"/students/{self.student.pk}/edit/")
        self.assertEqual(r.status_code, 200)


class EnquiryViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")

    def test_enquiry_list_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/enquiries/")
        self.assertEqual(r.status_code, 200)

    def test_enquiry_create_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/enquiries/create/")
        self.assertEqual(r.status_code, 200)

    def test_enquiry_create_post(self):
        self.client.login(username="admin1", password="pass123")
        uni = University.objects.create(name="Test Uni", code="TU")
        course = Course.objects.create(university=uni, name="Test Course", code="TC01")
        student = Student.objects.create(name="Test Student", mobile="9876543210")
        r = self.client.post("/enquiries/create/", {
            "student_id_input": student.student_id,
            "student_name": "Test Student",
            "mobile": "9876543210",
            "whatsapp": "9876543210",
            "email": "test@test.com",
            "university": uni.pk,
            "course": course.pk,
            "assigned_to": self.admin.pk,
            "status": "new",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Enquiry.objects.exists())


class AdmissionViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.uni = University.objects.create(name="SRM", code="SRM")
        self.course = Course.objects.create(university=self.uni, name="B.Sc", code="BSC01")
        self.student = Student.objects.create(name="Kavi", mobile="9876543210")

    def test_admission_list_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/admissions/")
        self.assertEqual(r.status_code, 200)

    def test_admission_create_loads(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/admissions/create/")
        self.assertEqual(r.status_code, 200)

    def test_admission_detail_loads(self):
        self.client.login(username="admin1", password="pass123")
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        r = self.client.get(f"/admissions/{a.pk}/")
        self.assertEqual(r.status_code, 200)


class LoginLogoutTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass123", role="admin")

    def test_login_success(self):
        r = self.client.post("/login/", {"username": "admin1", "password": "pass123"})
        self.assertEqual(r.status_code, 302)

    def test_login_failure(self):
        r = self.client.post("/login/", {"username": "admin1", "password": "wrong"})
        self.assertEqual(r.status_code, 200)

    def test_logout(self):
        self.client.login(username="admin1", password="pass123")
        r = self.client.get("/logout/")
        self.assertEqual(r.status_code, 302)


class CourseFilterAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.client.login(username="admin1", password="pass123")
        self.uni = University.objects.create(name="SRM", code="SRM")
        self.course = Course.objects.create(university=self.uni, name="B.Sc", code="BSC01")

    def test_courses_by_university(self):
        r = self.client.get(f"/admissions/api/courses-by-university/?university_id={self.uni.pk}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["courses"]), 1)
        self.assertEqual(data["courses"][0]["name"], "B.Sc")

    def test_courses_by_university_empty(self):
        r = self.client.get("/admissions/api/courses-by-university/?university_id=999")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["courses"]), 0)


class StudentDetailAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.client.login(username="admin1", password="pass123")
        self.student = Student.objects.create(name="Kavi", mobile="9876543210", email="kavi@test.com")

    def test_student_detail_api(self):
        r = self.client.get(f"/enquiries/api/student-detail/?student_id={self.student.student_id}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["name"], "Kavi")
        self.assertEqual(data["mobile"], "9876543210")

    def test_student_detail_api_not_found(self):
        r = self.client.get("/enquiries/api/student-detail/?student_id=999")
        self.assertEqual(r.status_code, 404)
