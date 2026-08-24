from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Enquiry, FollowUp
from students.models import Student

User = get_user_model()


class EnquiryModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="admin1", password="pass123", role="admin")

    def test_create_enquiry(self):
        e = Enquiry.objects.create(
            student_name="Soundar", mobile="9876543210",
            source="website", assigned_to=self.user
        )
        self.assertEqual(e.student_name, "Soundar")
        self.assertEqual(e.status, "new")

    def test_enquiry_number_auto_generate(self):
        e1 = Enquiry.objects.create(student_name="A", mobile="1111111111")
        e2 = Enquiry.objects.create(student_name="B", mobile="2222222222")
        self.assertEqual(e1.enquiry_number, "ENQ-000001")
        self.assertEqual(e2.enquiry_number, "ENQ-000002")

    def test_enquiry_str(self):
        e = Enquiry.objects.create(student_name="Kavi", mobile="9876543210")
        self.assertEqual(str(e), "ENQ-000001 - Kavi")

    def test_enquiry_status_choices(self):
        for status, _ in Enquiry.STATUS_CHOICES:
            e = Enquiry.objects.create(student_name=f"Test {status}", mobile="1111111111", status=status)
            self.assertEqual(e.status, status)

    def test_enquiry_source_choices(self):
        for source, _ in Enquiry.SOURCE_CHOICES:
            e = Enquiry.objects.create(student_name=f"Test {source}", mobile="1111111111", source=source)
            self.assertEqual(e.source, source)

    def test_enquiry_with_student(self):
        s = Student.objects.create(name="Kavi", mobile="9876543210")
        e = Enquiry.objects.create(student=s, student_name="Kavi", mobile="9876543210")
        self.assertEqual(e.student, s)

    def test_enquiry_followup(self):
        e = Enquiry.objects.create(student_name="Test", mobile="1111111111")
        fu = FollowUp.objects.create(enquiry=e, counsellor=self.user, notes="Called student")
        self.assertEqual(fu.enquiry, e)
        self.assertEqual(fu.counsellor, self.user)
        self.assertEqual(str(fu), "Follow-up: ENQ-000001")

    def test_enquiry_ordering(self):
        e1 = Enquiry.objects.create(student_name="First", mobile="1111111111")
        e2 = Enquiry.objects.create(student_name="Second", mobile="2222222222")
        enquiries = list(Enquiry.objects.all())
        self.assertEqual(enquiries[0], e2)
        self.assertEqual(enquiries[1], e1)
