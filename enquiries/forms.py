from django import forms
from .models import Enquiry, FollowUp
from students.models import Student


class EnquiryForm(forms.ModelForm):
    student_id_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Student ID (e.g. STU-0001)', 'id': 'id_student_id_input'}),
        label='Student ID',
    )

    class Meta:
        model = Enquiry
        fields = ['student_id_input', 'student_name', 'mobile', 'whatsapp', 'email', 'university', 'course', 'source', 'assigned_to', 'status', 'next_followup', 'notes']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit WhatsApp number starting with 6,7,8,9'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'university': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'next_followup': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        if mobile and (len(mobile) != 10 or mobile[0] not in '6789'):
            raise forms.ValidationError('Enter a valid 10 digit mobile number starting with 6, 7, 8, or 9')
        return mobile

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp', '').strip()
        if whatsapp and (len(whatsapp) != 10 or whatsapp[0] not in '6789'):
            raise forms.ValidationError('Enter a valid 10 digit WhatsApp number starting with 6, 7, 8, or 9')
        return whatsapp


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['notes', 'next_followup', 'new_status']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_followup': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'new_status': forms.Select(attrs={'class': 'form-select'}, choices=[('', '--- Keep Status ---')] + Enquiry.STATUS_CHOICES),
        }
