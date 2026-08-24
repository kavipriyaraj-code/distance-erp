from django import forms
from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['university', 'name', 'code', 'course_type', 'duration', 'eligibility', 'total_fee', 'is_active', 'description']
        widgets = {
            'university': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'course_type': forms.Select(attrs={'class': 'form-select'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'eligibility': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'total_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
