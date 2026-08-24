from django.shortcuts import render
from universities.models import University


def about_view(request):
    return render(request, 'pages/about.html')


def success_stories_view(request):
    return render(request, 'pages/success_stories.html')


def universities_view(request):
    universities = University.objects.filter(is_active=True)
    return render(request, 'pages/universities.html', {'universities': universities})


def privacy_view(request):
    return render(request, 'pages/privacy.html')


def services_view(request):
    return render(request, 'pages/services.html')


def service_university_view(request):
    return render(request, 'pages/service_university.html')


def service_application_view(request):
    return render(request, 'pages/service_application.html')


def service_scholarship_view(request):
    return render(request, 'pages/service_scholarship.html')


def service_distance_view(request):
    return render(request, 'pages/service_distance.html')
