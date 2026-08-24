from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'photo', 'dob', 'gender', 'mobile', 'whatsapp', 'email', 'address', 'city', 'state', 'pincode', 'aadhaar_last4', 'emergency_contact', 'university', 'course', 'registration_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit WhatsApp number starting with 6,7,8,9'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 6, 'pattern': '[0-9]{6}', 'title': 'Enter 6 digit pincode'}),
            'aadhaar_last4': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 4}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10, 'pattern': '[6-9][0-9]{9}', 'title': 'Enter valid 10 digit mobile number starting with 6,7,8,9'}),
            'university': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'registration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'status': forms.Select(attrs={'class': 'form-select'}),
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

    def clean_emergency_contact(self):
        ec = self.cleaned_data.get('emergency_contact', '').strip()
        if ec and (len(ec) != 10 or ec[0] not in '6789'):
            raise forms.ValidationError('Enter a valid 10 digit emergency contact starting with 6, 7, 8, or 9')
        return ec
