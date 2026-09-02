from django import forms
from .models import Enquiry, FollowUp
from students.models import Student


class EnquiryForm(forms.ModelForm):
    student_id_input = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Student ID (e.g. STU-0001)', 'id': 'id_student_id_input'}),
        label='Student ID',
    )

    class Meta:
        model = Enquiry
        fields = ['student_id_input', 'student_name', 'mobile', 'whatsapp', 'email', 'university', 'course', 'assigned_to', 'status', 'next_followup', 'notes']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9', 'required': True}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit WhatsApp number starting with 6,7,8,9', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'university': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'course': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'next_followup': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = ['student_name', 'mobile', 'whatsapp', 'email', 'university', 'course']
        for f in required_fields:
            if f in self.fields:
                self.fields[f].required = True

    def clean_student_id_input(self):
        sid = self.cleaned_data.get('student_id_input', '').strip()
        if not sid:
            raise forms.ValidationError('Student ID is required.')
        return sid

    def clean_student_name(self):
        name = self.cleaned_data.get('student_name', '').strip()
        if not name:
            raise forms.ValidationError('Student name is required.')
        return name

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        if not mobile:
            raise forms.ValidationError('Mobile number is required.')
        if len(mobile) != 10 or mobile[0] not in '6789':
            raise forms.ValidationError('Enter a valid 10 digit mobile number starting with 6, 7, 8, or 9')
        return mobile

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp', '').strip()
        if not whatsapp:
            raise forms.ValidationError('WhatsApp number is required.')
        if len(whatsapp) != 10 or whatsapp[0] not in '6789':
            raise forms.ValidationError('Enter a valid 10 digit WhatsApp number starting with 6, 7, 8, or 9')
        return whatsapp

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        return email

    def clean_university(self):
        university = self.cleaned_data.get('university')
        if not university:
            raise forms.ValidationError('University is required.')
        return university

    def clean_course(self):
        course = self.cleaned_data.get('course')
        if not course:
            raise forms.ValidationError('Course is required.')
        return course


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['notes', 'next_followup', 'new_status']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_followup': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'new_status': forms.Select(attrs={'class': 'form-select'}, choices=[('', '--- Keep Status ---')] + Enquiry.STATUS_CHOICES),
        }
