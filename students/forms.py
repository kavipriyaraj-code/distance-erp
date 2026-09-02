from django import forms
from django.utils import timezone
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'photo', 'dob', 'gender', 'mobile', 'whatsapp', 'email', 'address', 'city', 'state', 'pincode', 'aadhaar_number', 'emergency_contact', 'university', 'course', 'registration_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}, format='%Y-%m-%d'),
            'gender': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9', 'required': True}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit WhatsApp number starting with 6,7,8,9', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 6, 'pattern': '[0-9]{6}', 'title': 'Enter 6 digit pincode', 'required': True}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 12, 'pattern': '[0-9]{12}', 'title': 'Enter exactly 12 digit Aadhaar number', 'required': True}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9'}),
            'university': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'course': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'registration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'readonly': True}, format='%Y-%m-%d'),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['registration_date'].initial = timezone.localdate()
        required_fields = ['dob', 'gender', 'mobile', 'email', 'address', 'city', 'state', 'pincode', 'aadhaar_number', 'university', 'course', 'whatsapp']
        for f in required_fields:
            if f in self.fields:
                self.fields[f].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Full Name is required.')
        return name

    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise forms.ValidationError('Date of Birth is required.')
        return dob

    def clean_gender(self):
        gender = self.cleaned_data.get('gender', '').strip()
        if not gender:
            raise forms.ValidationError('Gender is required.')
        return gender

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        if not mobile:
            raise forms.ValidationError('Mobile number is required.')
        if len(mobile) != 10 or mobile[0] not in '6789':
            raise forms.ValidationError('Enter a valid 10 digit mobile number starting with 6, 7, 8, or 9')
        return mobile

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if not address:
            raise forms.ValidationError('Address is required.')
        return address

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise forms.ValidationError('City is required.')
        return city

    def clean_state(self):
        state = self.cleaned_data.get('state', '').strip()
        if not state:
            raise forms.ValidationError('State is required.')
        return state

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '').strip()
        if not pincode:
            raise forms.ValidationError('Pincode is required.')
        if len(pincode) != 6 or not pincode.isdigit():
            raise forms.ValidationError('Enter exactly 6 digits.')
        return pincode

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        return email

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp', '').strip()
        if not whatsapp:
            raise forms.ValidationError('WhatsApp number is required.')
        if len(whatsapp) != 10 or whatsapp[0] not in '6789':
            raise forms.ValidationError('Enter a valid 10 digit WhatsApp number starting with 6, 7, 8, or 9')
        return whatsapp

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number', '').strip()
        if not aadhaar:
            raise forms.ValidationError('Aadhaar Number is required.')
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            raise forms.ValidationError('Enter exactly 12 digits.')
        return aadhaar

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

    def clean_emergency_contact(self):
        ec = self.cleaned_data.get('emergency_contact', '').strip()
        if ec and (len(ec) != 10 or ec[0] not in '6789'):
            raise forms.ValidationError('Enter a valid 10 digit emergency contact starting with 6, 7, 8, or 9')
        return ec
