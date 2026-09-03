from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from .models import Payment
from admissions.models import Admission
from students.models import Student
from universities.models import University
from courses.models import Course

User = get_user_model()


class PaymentModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="admin1", password="pass123", role="accountant")
        self.uni = University.objects.create(name="SRM", code="SRM")
        self.course = Course.objects.create(university=self.uni, name="B.Sc", code="BSC01", total_fee=95000)
        self.student = Student.objects.create(name="Kavi", mobile="9876543210")
        self.admission = Admission.objects.create(
            student=self.student, university=self.uni, course=self.course, total_fee=95000
        )

    def test_create_payment(self):
        p = Payment.objects.create(
            admission=self.admission, amount=50000, payment_date=date.today(),
            payment_mode="upi", received_by=self.user
        )
        self.assertEqual(p.amount, 50000)
        self.assertFalse(p.is_voided)

    def test_receipt_number_auto_generate(self):
        p1 = Payment.objects.create(admission=self.admission, amount=10000, payment_date=date.today())
        p2 = Payment.objects.create(admission=self.admission, amount=20000, payment_date=date.today())
        self.assertTrue(p1.receipt_number.startswith("RCP-"))
        self.assertTrue(p2.receipt_number.startswith("RCP-"))
        self.assertNotEqual(p1.receipt_number, p2.receipt_number)
        self.assertGreater(int(p2.receipt_number.split("-")[1]), int(p1.receipt_number.split("-")[1]))

    def test_receipt_number_unique(self):
        p1 = Payment.objects.create(admission=self.admission, amount=10000, payment_date=date.today())
        p2 = Payment.objects.create(admission=self.admission, amount=20000, payment_date=date.today())
        self.assertNotEqual(p1.receipt_number, p2.receipt_number)

    def test_payment_str(self):
        p = Payment.objects.create(admission=self.admission, amount=50000, payment_date=date.today())
        self.assertIn("RCP-", str(p))
        self.assertIn("50000", str(p))

    def test_payment_mode_choices(self):
        for mode, _ in Payment.MODE_CHOICES:
            p = Payment.objects.create(admission=self.admission, amount=1000, payment_date=date.today(), payment_mode=mode)
            self.assertEqual(p.payment_mode, mode)

    def test_void_payment(self):
        p = Payment.objects.create(admission=self.admission, amount=50000, payment_date=date.today())
        p.is_voided = True
        p.voided_reason = "Duplicate entry"
        p.save()
        self.assertTrue(p.is_voided)
        self.assertEqual(p.voided_reason, "Duplicate entry")

    def test_admission_paid_amount_with_payments(self):
        Payment.objects.create(admission=self.admission, amount=30000, payment_date=date.today())
        Payment.objects.create(admission=self.admission, amount=20000, payment_date=date.today())
        self.admission.refresh_from_db()
        self.assertEqual(self.admission.paid_amount, 50000)

    def test_admission_paid_amount_excludes_voided(self):
        p1 = Payment.objects.create(admission=self.admission, amount=30000, payment_date=date.today())
        p2 = Payment.objects.create(admission=self.admission, amount=20000, payment_date=date.today(), is_voided=True)
        self.admission.refresh_from_db()
        self.assertEqual(self.admission.paid_amount, 30000)

    def test_admission_balance_after_payment(self):
        Payment.objects.create(admission=self.admission, amount=40000, payment_date=date.today())
        self.admission.refresh_from_db()
        self.assertEqual(self.admission.balance_amount, 55000)

    def test_payment_ordering(self):
        p1 = Payment.objects.create(admission=self.admission, amount=10000, payment_date=date(2025, 1, 1))
        p2 = Payment.objects.create(admission=self.admission, amount=20000, payment_date=date(2025, 6, 1))
        payments = list(Payment.objects.all())
        self.assertEqual(payments[0], p2)
        self.assertEqual(payments[1], p1)
