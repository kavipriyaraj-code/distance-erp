from django.core.management.base import BaseCommand
from documents.models import DocumentType


class Command(BaseCommand):
    help = 'Seed default document types'

    def handle(self, *args, **options):
        defaults = [
            'Passport Photo',
            'Aadhaar',
            '10th Certificate',
            '12th Certificate',
            'Degree Certificate',
            'Transfer Certificate',
            'Migration Certificate',
            'Other',
        ]
        for name in defaults:
            obj, created = DocumentType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created: {name}')
            else:
                self.stdout.write(f'Exists: {name}')
        self.stdout.write(self.style.SUCCESS('Done.'))
