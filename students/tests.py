from django.test import TestCase
from .models import Student


class StudentModelTest(TestCase):

    def test_create_student(self):
        s = Student.objects.create(name="Kavi", mobile="9876543210")
        self.assertEqual(s.name, "Kavi")
        self.assertEqual(s.mobile, "9876543210")
        self.assertEqual(s.status, "prospect")

    def test_student_id_auto_generate(self):
        s1 = Student.objects.create(name="First", mobile="1111111111")
        s2 = Student.objects.create(name="Second", mobile="2222222222")
        self.assertEqual(s1.student_id, "STU-000001")
        self.assertEqual(s2.student_id, "STU-000002")

    def test_student_id_unique(self):
        s1 = Student.objects.create(name="A", mobile="1111111111")
        s2 = Student.objects.create(name="B", mobile="2222222222")
        self.assertNotEqual(s1.student_id, s2.student_id)

    def test_student_str(self):
        s = Student.objects.create(name="Kavi", mobile="9876543210")
        self.assertEqual(str(s), "STU-000001 - Kavi")

    def test_student_default_status(self):
        s = Student.objects.create(name="Test", mobile="1111111111")
        self.assertEqual(s.status, "prospect")

    def test_student_status_choices(self):
        for status, _ in Student.STATUS_CHOICES:
            s = Student.objects.create(name=f"Test {status}", mobile="1111111111", status=status)
            self.assertEqual(s.status, status)

    def test_student_optional_fields_blank(self):
        s = Student.objects.create(name="Minimal", mobile="1111111111")
        self.assertEqual(s.whatsapp, "")
        self.assertEqual(s.email, "")
        self.assertEqual(s.address, "")
        self.assertEqual(s.city, "")
        self.assertEqual(s.state, "")
        self.assertEqual(s.pincode, "")
        self.assertEqual(s.aadhaar_number, "")
        self.assertEqual(s.emergency_contact, "")

    def test_student_ordering(self):
        s1 = Student.objects.create(name="First", mobile="1111111111")
        s2 = Student.objects.create(name="Second", mobile="2222222222")
        students = list(Student.objects.all())
        self.assertEqual(students[0], s2)
        self.assertEqual(students[1], s1)

    def test_student_with_university_and_course(self):
        from universities.models import University
        from courses.models import Course
        uni = University.objects.create(name="SRM", code="SRM")
        course = Course.objects.create(university=uni, name="B.Sc", code="BSC01")
        s = Student.objects.create(name="Test", mobile="1111111111", university=uni, course=course)
        self.assertEqual(s.university, uni)
        self.assertEqual(s.course, course)
