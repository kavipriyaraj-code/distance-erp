from django import forms
from .models import StaffAttendance


class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendance
        fields = ['staff', 'date', 'check_in', 'check_out', 'status', 'admin_notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CheckInForm(forms.Form):
    pass


class CheckOutForm(forms.Form):
    pass
