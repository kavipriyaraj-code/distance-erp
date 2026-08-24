from django.shortcuts import render, redirect
from django.contrib import messages
from students.models import Student
from students.forms import StudentForm
from universities.models import University
from courses.models import Course


def public_admission(request):
    universities = University.objects.filter(is_active=True)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile', '').strip()
            if mobile:
                existing = Student.objects.filter(mobile=mobile).first()
                if existing:
                    messages.warning(request, f'A student with mobile {mobile} already exists: {existing.student_id} - {existing.name}.')
                    return redirect('/')
            student = form.save()
            messages.success(request, f'Registration successful! Your Student ID: {student.student_id}. Our team will contact you shortly.')
            return redirect('/')
        else:
            for field, errors in form.errors.items():
                label = form.fields[field].label or field
                messages.error(request, f'{label}: {errors[0]}')
    else:
        form = StudentForm(initial={'status': 'prospect', 'registration_date': __import__('datetime').date.today()})
    return render(request, 'public_admission.html', {
        'form': form,
        'universities': universities,
    })


def admission_success(request, pk):
    student = Student.objects.get(pk=pk)
    return render(request, 'admission_success.html', {'student': student})
