from django import forms
from .models import Payment, Semester


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['semester', 'amount', 'payment_date', 'payment_mode', 'transaction_ref', 'notes']
        widgets = {
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_mode': forms.Select(attrs={'class': 'form-select'}),
            'transaction_ref': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.admission = kwargs.pop('admission', None)
        super().__init__(*args, **kwargs)
        if self.admission:
            self.fields['semester'].queryset = Semester.objects.filter(course=self.admission.course)
        else:
            self.fields['semester'].queryset = Semester.objects.none()
        self.fields['semester'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('Payment amount must be greater than zero.')
        if self.admission and amount:
            balance = self.admission.balance_amount
            if amount > balance:
                raise forms.ValidationError(f'Payment of Rs. {amount} exceeds balance of Rs. {balance}.')
        return amount


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ['course', 'name', 'semester_number', 'fee_amount', 'due_date', 'description']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'semester_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'fee_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
