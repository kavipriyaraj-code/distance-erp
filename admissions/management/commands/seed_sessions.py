from django.core.management.base import BaseCommand
from admissions.models import AcademicSession


class Command(BaseCommand):
    help = 'Seed default academic sessions'

    def handle(self, *args, **options):
        from datetime import date
        year = date.today().year
        sessions = [f'{year}-{year+1}', f'{year+1}-{year+2}']
        for name in sessions:
            obj, created = AcademicSession.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created: {name}')
            else:
                self.stdout.write(f'Exists: {name}')
        self.stdout.write(self.style.SUCCESS('Done.'))
