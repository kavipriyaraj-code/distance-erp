from django import forms
from .models import Admission
from students.models import Student


class AdmissionForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(enquiries__isnull=False).exclude(admissions__isnull=False).distinct().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Admission
        fields = ['student', 'university', 'course', 'session', 'total_fee', 'notes']
        widgets = {
            'university': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'session': forms.Select(attrs={'class': 'form-select'}),
            'total_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
