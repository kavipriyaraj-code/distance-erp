from django import forms
from .models import Admission
from students.models import Student


class AdmissionForm(forms.ModelForm):
    student_id_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Student ID (e.g. STU-0001)', 'id': 'id_student_id_input'}),
        label='Student ID',
    )

    class Meta:
        model = Admission
        fields = ['university', 'course', 'session', 'total_fee', 'incentive', 'notes']
        widgets = {
            'university': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'session': forms.Select(attrs={'class': 'form-select'}),
            'total_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'incentive': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
