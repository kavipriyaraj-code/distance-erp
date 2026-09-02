import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'distance_erp.settings')
django.setup()

from universities.models import University
from courses.models import Course

universities_data = [
    {'name': 'IGNOU', 'code': 'IGNOU', 'contact_number': '011-29571000', 'email': 'ignou@ignou.ac.in'},
    {'name': 'Annamalai University', 'code': 'ANNAIMALAI', 'contact_number': '04144-232290', 'email': 'info@annamalaiuniversity.ac.in'},
    {'name': 'Sikkim Manipal University', 'code': 'SMU', 'contact_number': '03592-242801', 'email': 'info@smu.edu.in'},
    {'name': 'Lovely Professional University', 'code': 'LPU', 'contact_number': '01824-511811', 'email': 'admissions@lpu.co.in'},
    {'name': 'Chandigarh University', 'code': 'CU', 'contact_number': '0160-2532350', 'email': 'admissions@cuchd.in'},
    {'name': 'Amity University', 'code': 'AMITY', 'contact_number': '0120-4392520', 'email': 'admissions@amity.edu'},
    {'name': 'Symbiosis International University', 'code': 'SYMBIOSIS', 'contact_number': '020-28141300', 'email': 'info@symbiosis.ac.in'},
    {'name': 'Manipal University Jaipur', 'code': 'MANIPAL', 'contact_number': '0820-2571998', 'email': 'admissions@manipal.edu'},
    {'name': 'Gitam University', 'code': 'GITAM', 'contact_number': '0891-2790177', 'email': 'admissions@gitam.edu'},
    {'name': 'Vignan University', 'code': 'VIGNAN', 'contact_number': '0863-2344610', 'email': 'admissions@vignan.ac.in'},
    {'name': 'Bharathiar University', 'code': 'BHARATHIAR', 'contact_number': '0422-2422270', 'email': 'info@bharathiar.ac.in'},
    {'name': 'Karnataka State Open University', 'code': 'KSOU', 'contact_number': '0821-2542126', 'email': 'info@ksou.ac.in'},
]

created_count = 0
for data in universities_data:
    obj, created = University.objects.get_or_create(
        code=data['code'],
        defaults=data
    )
    if created:
        created_count += 1
        print(f'Created University: {data["name"]}')

print(f'\nTotal universities: {University.objects.count()} (Created {created_count} new)\n')

courses_data = [
    # IGNOU
    {'name': 'BA', 'uni': 'IGNOU', 'code': 'IGNOU-BA', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 30000},
    {'name': 'B.Com', 'uni': 'IGNOU', 'code': 'IGNOU-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 36000},
    {'name': 'BCA', 'uni': 'IGNOU', 'code': 'IGNOU-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 45000},
    {'name': 'BBA', 'uni': 'IGNOU', 'code': 'IGNOU-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 40000},
    {'name': 'MA English', 'uni': 'IGNOU', 'code': 'IGNOU-MA-ENG', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 36000},
    {'name': 'MA Hindi', 'uni': 'IGNOU', 'code': 'IGNOU-MA-HIN', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 30000},
    {'name': 'MA Tamil', 'uni': 'IGNOU', 'code': 'IGNOU-MA-TAM', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 30000},
    {'name': 'M.Com', 'uni': 'IGNOU', 'code': 'IGNOU-MCOM', 'type': 'PG', 'cat': 'Commerce', 'dur': '2 Years', 'fee': 36000},
    {'name': 'MBA', 'uni': 'IGNOU', 'code': 'IGNOU-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 60000},
    {'name': 'MCA', 'uni': 'IGNOU', 'code': 'IGNOU-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 72000},
    {'name': 'B.Sc Computer Science', 'uni': 'IGNOU', 'code': 'IGNOU-BSC-CS', 'type': 'UG', 'cat': 'Science', 'dur': '3 Years', 'fee': 45000},
    {'name': 'M.Sc Computer Science', 'uni': 'IGNOU', 'code': 'IGNOU-MSC-CS', 'type': 'PG', 'cat': 'Science', 'dur': '2 Years', 'fee': 54000},

    # Annamalai University
    {'name': 'BA Tamil', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-BA-TAM', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 18000},
    {'name': 'BA English', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-BA-ENG', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 18000},
    {'name': 'B.Com', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 24000},
    {'name': 'BBA', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 30000},
    {'name': 'BCA', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 36000},
    {'name': 'MA Tamil', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-MA-TAM', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 18000},
    {'name': 'M.Com', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-MCOM', 'type': 'PG', 'cat': 'Commerce', 'dur': '2 Years', 'fee': 24000},
    {'name': 'MBA', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 45000},
    {'name': 'MCA', 'uni': 'ANNAIMALAI', 'code': 'ANNAI-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 48000},

    # Sikkim Manipal University
    {'name': 'BCA', 'uni': 'SMU', 'code': 'SMU-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 54000},
    {'name': 'BBA', 'uni': 'SMU', 'code': 'SMU-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 48000},
    {'name': 'B.Com', 'uni': 'SMU', 'code': 'SMU-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 36000},
    {'name': 'BA', 'uni': 'SMU', 'code': 'SMU-BA', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 30000},
    {'name': 'MCA', 'uni': 'SMU', 'code': 'SMU-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 66000},
    {'name': 'MBA', 'uni': 'SMU', 'code': 'SMU-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 72000},
    {'name': 'M.Com', 'uni': 'SMU', 'code': 'SMU-MCOM', 'type': 'PG', 'cat': 'Commerce', 'dur': '2 Years', 'fee': 42000},
    {'name': 'B.Sc IT', 'uni': 'SMU', 'code': 'SMU-BSC-IT', 'type': 'UG', 'cat': 'Science', 'dur': '3 Years', 'fee': 48000},

    # Lovely Professional University
    {'name': 'BCA', 'uni': 'LPU', 'code': 'LPU-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 60000},
    {'name': 'BBA', 'uni': 'LPU', 'code': 'LPU-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 54000},
    {'name': 'B.Com (Hons)', 'uni': 'LPU', 'code': 'LPU-BCOM-H', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 48000},
    {'name': 'BA', 'uni': 'LPU', 'code': 'LPU-BA', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 36000},
    {'name': 'MCA', 'uni': 'LPU', 'code': 'LPU-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 72000},
    {'name': 'MBA', 'uni': 'LPU', 'code': 'LPU-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 84000},
    {'name': 'M.Com', 'uni': 'LPU', 'code': 'LPU-MCOM', 'type': 'PG', 'cat': 'Commerce', 'dur': '2 Years', 'fee': 42000},
    {'name': 'B.Sc Computer Science', 'uni': 'LPU', 'code': 'LPU-BSC-CS', 'type': 'UG', 'cat': 'Science', 'dur': '3 Years', 'fee': 54000},

    # Chandigarh University
    {'name': 'BCA', 'uni': 'CU', 'code': 'CU-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 54000},
    {'name': 'BBA', 'uni': 'CU', 'code': 'CU-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 48000},
    {'name': 'B.Com', 'uni': 'CU', 'code': 'CU-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 42000},
    {'name': 'MBA', 'uni': 'CU', 'code': 'CU-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 78000},
    {'name': 'MCA', 'uni': 'CU', 'code': 'CU-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 66000},
    {'name': 'BA', 'uni': 'CU', 'code': 'CU-BA', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 36000},

    # Amity University
    {'name': 'BCA', 'uni': 'AMITY', 'code': 'AMITY-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 72000},
    {'name': 'BBA', 'uni': 'AMITY', 'code': 'AMITY-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 66000},
    {'name': 'B.Com (Hons)', 'uni': 'AMITY', 'code': 'AMITY-BCOM-H', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 54000},
    {'name': 'MBA', 'uni': 'AMITY', 'code': 'AMITY-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 96000},
    {'name': 'MCA', 'uni': 'AMITY', 'code': 'AMITY-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 78000},
    {'name': 'BA (Hons)', 'uni': 'AMITY', 'code': 'AMITY-BA-H', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 48000},

    # Symbiosis
    {'name': 'BCA', 'uni': 'SYMBIOSIS', 'code': 'SYMB-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 78000},
    {'name': 'BBA', 'uni': 'SYMBIOSIS', 'code': 'SYMB-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 72000},
    {'name': 'MBA', 'uni': 'SYMBIOSIS', 'code': 'SYMB-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 120000},
    {'name': 'B.Com', 'uni': 'SYMBIOSIS', 'code': 'SYMB-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 60000},

    # Manipal University
    {'name': 'BCA', 'uni': 'MANIPAL', 'code': 'MANI-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 66000},
    {'name': 'BBA', 'uni': 'MANIPAL', 'code': 'MANI-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 60000},
    {'name': 'MBA', 'uni': 'MANIPAL', 'code': 'MANI-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 90000},
    {'name': 'MCA', 'uni': 'MANIPAL', 'code': 'MANI-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 72000},

    # Gitam University
    {'name': 'BCA', 'uni': 'GITAM', 'code': 'GITA-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 48000},
    {'name': 'BBA', 'uni': 'GITAM', 'code': 'GITA-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 42000},
    {'name': 'B.Com', 'uni': 'GITAM', 'code': 'GITA-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 36000},
    {'name': 'MBA', 'uni': 'GITAM', 'code': 'GITA-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 60000},
    {'name': 'MCA', 'uni': 'GITAM', 'code': 'GITA-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 54000},

    # Vignan University
    {'name': 'BCA', 'uni': 'VIGNAN', 'code': 'VIG-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 45000},
    {'name': 'BBA', 'uni': 'VIGNAN', 'code': 'VIG-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 40000},
    {'name': 'B.Com', 'uni': 'VIGNAN', 'code': 'VIG-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 36000},
    {'name': 'MCA', 'uni': 'VIGNAN', 'code': 'VIG-MCA', 'type': 'PG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 54000},
    {'name': 'MBA', 'uni': 'VIGNAN', 'code': 'VIG-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 50000},

    # Bharathiar University
    {'name': 'BA Tamil', 'uni': 'BHARATHIAR', 'code': 'BHAR-BA-TAM', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 15000},
    {'name': 'B.Com', 'uni': 'BHARATHIAR', 'code': 'BHAR-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 18000},
    {'name': 'BCA', 'uni': 'BHARATHIAR', 'code': 'BHAR-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 30000},
    {'name': 'MA Tamil', 'uni': 'BHARATHIAR', 'code': 'BHAR-MA-TAM', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 15000},
    {'name': 'M.Com', 'uni': 'BHARATHIAR', 'code': 'BHAR-MCOM', 'type': 'PG', 'cat': 'Commerce', 'dur': '2 Years', 'fee': 18000},
    {'name': 'MBA', 'uni': 'BHARATHIAR', 'code': 'BHAR-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 36000},

    # Karnataka State Open University
    {'name': 'BA', 'uni': 'KSOU', 'code': 'KSOU-BA', 'type': 'UG', 'cat': 'Arts', 'dur': '3 Years', 'fee': 18000},
    {'name': 'B.Com', 'uni': 'KSOU', 'code': 'KSOU-BCOM', 'type': 'UG', 'cat': 'Commerce', 'dur': '3 Years', 'fee': 21000},
    {'name': 'BCA', 'uni': 'KSOU', 'code': 'KSOU-BCA', 'type': 'UG', 'cat': 'Computer Applications', 'dur': '3 Years', 'fee': 36000},
    {'name': 'BBA', 'uni': 'KSOU', 'code': 'KSOU-BBA', 'type': 'UG', 'cat': 'Management', 'dur': '3 Years', 'fee': 30000},
    {'name': 'MBA', 'uni': 'KSOU', 'code': 'KSOU-MBA', 'type': 'PG', 'cat': 'Management', 'dur': '2 Years', 'fee': 42000},
    {'name': 'MA English', 'uni': 'KSOU', 'code': 'KSOU-MA-ENG', 'type': 'PG', 'cat': 'Arts', 'dur': '2 Years', 'fee': 18000},
]

course_created = 0
for data in courses_data:
    try:
        uni = University.objects.get(code=data['uni'])
        obj, created = Course.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'university': uni,
                'course_type': data['type'],
                'category': data['cat'],
                'duration': data['dur'],
                'total_fee': data['fee'],
                'eligibility': '10+2' if data['type'] == 'UG' else 'Graduation',
                'is_active': True,
            }
        )
        if created:
            course_created += 1
            print(f'Created: {data["name"]} - {uni.name} (Rs.{data["fee"]:,})')
    except University.DoesNotExist:
        print(f'Skipped: {data["name"]} - {data["uni"]} not found')

print(f'\nTotal courses: {Course.objects.count()} (Created {course_created} new)')
