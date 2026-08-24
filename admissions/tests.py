from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from .models import Admission, AcademicSession
from students.models import Student
from universities.models import University
from courses.models import Course

User = get_user_model()


class AdmissionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="admin1", password="pass123", role="admin")
        self.uni = University.objects.create(name="SRM", code="SRM")
        self.course = Course.objects.create(university=self.uni, name="B.Sc Data Science", code="BSC01", total_fee=95000)
        self.student = Student.objects.create(name="Soundar", mobile="9876543210")

    def test_create_admission(self):
        a = Admission.objects.create(
            student=self.student, university=self.uni, course=self.course,
            total_fee=95000, counsellor=self.user
        )
        self.assertEqual(a.student, self.student)
        self.assertEqual(a.status, "application")

    def test_admission_number_auto_generate(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        self.assertIn(str(date.today().year), a.admission_number)
        self.assertTrue(a.admission_number.startswith("RENIC-"))

    def test_admission_number_unique(self):
        s2 = Student.objects.create(name="Kavi", mobile="1111111111")
        a1 = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        a2 = Admission.objects.create(student=s2, university=self.uni, course=self.course)
        self.assertNotEqual(a1.admission_number, a2.admission_number)

    def test_admission_str(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        self.assertIn("Soundar", str(a))
        self.assertIn("RENIC-", str(a))

    def test_admission_default_fee_from_course(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        self.assertEqual(a.total_fee, 95000)

    def test_admission_custom_fee(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course, total_fee=50000)
        self.assertEqual(a.total_fee, 50000)

    def test_admission_status_choices(self):
        for status, _ in Admission.STATUS_CHOICES:
            a = Admission.objects.create(student=self.student, university=self.uni, course=self.course, status=status)
            self.assertEqual(a.status, status)

    def test_admission_paid_amount_no_payments(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course, total_fee=95000)
        self.assertEqual(a.paid_amount, 0)

    def test_admission_balance_amount(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course, total_fee=95000)
        self.assertEqual(a.balance_amount, 95000)

    def test_admission_balance_never_negative(self):
        course_free = Course.objects.create(university=self.uni, name="Free Course", code="FC01", total_fee=0)
        a = Admission.objects.create(student=self.student, university=self.uni, course=course_free)
        self.assertEqual(a.total_fee, 0)
        self.assertEqual(a.balance_amount, 0)

    def test_academic_session(self):
        s = AcademicSession.objects.create(name="2025-26", is_active=True)
        self.assertEqual(str(s), "2025-26")
        self.assertTrue(s.is_active)

    def test_student_has_admissions_reverse(self):
        a = Admission.objects.create(student=self.student, university=self.uni, course=self.course)
        self.assertIn(a, self.student.admissions.all())
