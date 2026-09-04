from django.core.management.base import BaseCommand
from courses.models import Course
from fees.models import Semester
from datetime import date, timedelta
import decimal


class Command(BaseCommand):
    help = 'Create semesters for all courses that do not have them'

    def handle(self, *args, **options):
        count = 0
        for c in Course.objects.all():
            if c.semesters.exists():
                self.stdout.write(f'{c.name} ({c.university.name}): already has {c.semesters.count()} semesters')
                continue
            if c.fee_per_year:
                fee = c.fee_per_year / 2
                total = c.fee_per_year * c.duration_years
            elif c.total_fee:
                fee = c.total_fee / 8
                total = c.total_fee
            else:
                fee = decimal.Decimal('5000')
                total = fee * 8
            num_sems = c.duration_years * 2 if c.duration_years else 8
            for i in range(1, num_sems + 1):
                Semester.objects.create(
                    course=c, name=f'Semester {i}', semester_number=i,
                    fee_amount=fee, due_date=date(2026, 1, 1) + timedelta(days=90 * i)
                )
            count += 1
            self.stdout.write(f'{c.name} ({c.university.name}): created {num_sems} semesters (₹{fee}/sem, ₹{total} total)')
        self.stdout.write(self.style.SUCCESS(f'Done. Created semesters for {count} courses.'))
