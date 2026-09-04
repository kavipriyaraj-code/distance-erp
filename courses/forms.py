from django import forms
from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['university', 'name', 'code', 'course_type', 'duration', 'duration_years', 'eligibility', 'fee_per_year', 'is_active', 'description']
        widgets = {
            'university': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'course_type': forms.Select(attrs={'class': 'form-select'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_years': forms.Select(attrs={'class': 'form-select'}),
            'eligibility': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fee_per_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 64000'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
