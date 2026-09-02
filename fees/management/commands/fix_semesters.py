from django.core.management.base import BaseCommand
from courses.models import Course
from fees.models import Semester
from admissions.models import Admission
from datetime import date, timedelta
import decimal


class Command(BaseCommand):
    help = 'Seed semesters and diagnose missing ones'

    def handle(self, *args, **options):
        admissions = Admission.objects.select_related('course', 'university', 'student').all()
        self.stdout.write(f'Total admissions: {admissions.count()}')

        for a in admissions:
            semesters = Semester.objects.filter(course=a.course)
            self.stdout.write(f'  {a.student.name} -> {a.course.name} (id={a.course.id}, uni={a.university.name}) -> {semesters.count()} semesters')

            if semesters.count() == 0:
                fee = a.course.total_fee / 8 if a.course.total_fee else decimal.Decimal('5000')
                for i in range(1, 9):
                    Semester.objects.create(
                        course=a.course, name=f'Semester {i}', semester_number=i,
                        fee_amount=fee, due_date=date(2026, 1, 1) + timedelta(days=90 * i)
                    )
                self.stdout.write(self.style.SUCCESS(f'  -> Created 8 semesters for {a.course.name} (fee each: {fee})'))

        self.stdout.write(self.style.SUCCESS('Done.'))
