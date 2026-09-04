from django.db import migrations
from datetime import date


def seed_sessions(apps, schema_editor):
    AcademicSession = apps.get_model('admissions', 'AcademicSession')
    year = date.today().year
    for name in [f'{year}-{year+1}', f'{year+1}-{year+2}']:
        AcademicSession.objects.get_or_create(name=name)


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0003_alter_admission_course_alter_admission_session_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_sessions, reverse_seed),
    ]
