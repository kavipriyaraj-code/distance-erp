from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


def generate_voucher_no(prefix):
    from django.db.models import Max
    today = timezone.localdate()
    year = today.year
    last_voucher = FinanceTransaction.objects.filter(
        voucher_no__startswith=f'{prefix}-{year}'
    ).aggregate(max_voucher=Max('voucher_no'))['max_voucher']
    if last_voucher:
        try:
            num = int(last_voucher.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f'{prefix}-{year}-{num:06d}'


class Branch(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_branches')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class CostCentre(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='cost_centres')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Cost Centres'

    def __str__(self):
        return f'{self.name} ({self.code})'


class FinanceAccount(models.Model):
    ACCOUNT_TYPES = [
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('upi', 'UPI'),
        ('payment_gateway', 'Payment Gateway'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opening_balance_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['account_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_account_type_display()})'

    @property
    def current_balance(self):
        from django.db.models import Sum
        today = timezone.localdate()
        closing = DayClosing.objects.filter(closing_date=today).first()
        if closing and closing.status == 'closed':
            if self.account_type == 'cash':
                return closing.expected_cash
            elif self.account_type == 'bank':
                return closing.expected_bank
        txns = FinanceTransaction.objects.filter(
            account=self, status='posted', transaction_date__lte=today
        )
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        return self.opening_balance + money_in - money_out


class ExpenseCategory(models.Model):
    CATEGORY_TYPES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
        ('transfer', 'Transfer'),
    ]
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='expense')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'
        ordering = ['category_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_category_type_display()})'


class FinanceTransaction(models.Model):
    VOUCHER_TYPES = [
        ('RV', 'Receipt Voucher'),
        ('PV', 'Payment Voucher'),
        ('TRF', 'Transfer'),
        ('OPEN', 'Opening Balance'),
        ('ADJ', 'Adjustment'),
    ]
    DIRECTION_CHOICES = [
        ('in', 'Money In'),
        ('out', 'Money Out'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
        ('reversed', 'Reversed'),
    ]
    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
        ('imps', 'IMPS'),
        ('cheque', 'Cheque'),
        ('dd', 'Demand Draft'),
        ('card', 'Card'),
        ('payment_gateway', 'Payment Gateway'),
        ('other', 'Other'),
    ]

    voucher_no = models.CharField(max_length=30, unique=True)
    voucher_type = models.CharField(max_length=10, choices=VOUCHER_TYPES)
    transaction_date = models.DateField()
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, related_name='transactions')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='cash')
    reference_no = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='finance_transactions')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_approvals')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f'{self.voucher_no} - {self.description} ({self.amount})'

    def save(self, *args, **kwargs):
        if not self.voucher_no:
            self.voucher_no = generate_voucher_no(self.voucher_type)
        super().save(*args, **kwargs)


class ExpenseEntry(models.Model):
    EXPENSE_STATUS = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_MODES = FinanceTransaction.PAYMENT_MODES

    expense_date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='cash')
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, null=True, blank=True)
    invoice_no = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    attachment = models.FileField(upload_to='finance/expenses/', blank=True)
    department = models.CharField(max_length=100, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_entries')
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_entries')
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    voucher_no = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=EXPENSE_STATUS, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_approvals')
    finance_transaction = models.ForeignKey(FinanceTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f'{self.voucher_no} - {self.category} - {self.amount}'

    def save(self, *args, **kwargs):
        if not self.voucher_no:
            self.voucher_no = generate_voucher_no('PV')
        super().save(*args, **kwargs)


class OpeningBalance(models.Model):
    financial_year = models.CharField(max_length=10)
    opening_date = models.DateField()
    cash_opening = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_opening = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='openingbalance_created')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='openingbalance_approved')
    created_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-opening_date']

    def __str__(self):
        return f'{self.financial_year} - Cash: {self.cash_opening}, Bank: {self.bank_opening}'


class DayClosing(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('submitted', 'Submitted for Closing'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ]
    closing_date = models.DateField(unique=True)
    opening_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cash_in = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cash_out = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    physical_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cash_difference = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opening_bank = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_in = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_out = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_bank = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    difference_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dayclosing_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-closing_date']

    def __str__(self):
        return f'Day Closing {self.closing_date} ({self.get_status_display()})'


class UniversityAccount(models.Model):
    university = models.OneToOneField('universities.University', on_delete=models.CASCADE, related_name='finance_account')
    account_name = models.CharField(max_length=200, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    upi_id = models.CharField(max_length=100, blank=True)
    payment_terms = models.TextField(blank=True, help_text='e.g., Pay within 30 days of admission')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Commission % institute retains')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'University Accounts'

    def __str__(self):
        return f'{self.university.name} Account'

    @property
    def total_payable(self):
        from django.db.models import Sum
        return UniversityTransaction.objects.filter(
            university=self.university, transaction_type='payable', status='posted'
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    @property
    def total_receivable(self):
        from django.db.models import Sum
        return UniversityTransaction.objects.filter(
            university=self.university, transaction_type='receivable', status='posted'
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')


class UniversityTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('payable', 'Payable (Institute owes University)'),
        ('receivable', 'Receivable (University owes Institute)'),
    ]
    FEE_TYPES = [
        ('registration', 'Registration Fee'),
        ('examination', 'Examination Fee'),
        ('revaluation', 'Revaluation Fee'),
        ('certificate', 'Certificate Fee'),
        ('migration', 'Migration Fee'),
        ('convocation', 'Convocation Fee'),
        ('processing', 'Student Processing Fee'),
        ('commission', 'Commission/Revenue Share'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ]

    voucher_no = models.CharField(max_length=30, unique=True)
    university = models.ForeignKey('universities.University', on_delete=models.PROTECT, related_name='finance_transactions')
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='university_finance_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPES, default='other')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_date = models.DateField()
    description = models.CharField(max_length=300, blank=True)
    reference_no = models.CharField(max_length=100, blank=True)
    account = models.ForeignKey(FinanceAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='university_transactions')
    finance_transaction = models.ForeignKey(FinanceTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='university_link')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='university_transactions_created')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='university_transactions_approved')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name_plural = 'University Transactions'

    def __str__(self):
        return f'{self.voucher_no} - {self.university.name} - {self.get_transaction_type_display()} ₹{self.amount}'

    def save(self, *args, **kwargs):
        if not self.voucher_no:
            self.voucher_no = generate_voucher_no('UTX')
        super().save(*args, **kwargs)


class StaffSalary(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('payable', 'Payable'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='salary_records')
    salary_month = models.CharField(max_length=7, help_text='Format: YYYY-MM')
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_adjustments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_mode = models.CharField(max_length=20, choices=FinanceTransaction.PAYMENT_MODES, blank=True)
    account = models.ForeignKey(FinanceAccount, on_delete=models.SET_NULL, null=True, blank=True)
    voucher_no = models.CharField(max_length=30, blank=True)
    finance_transaction = models.ForeignKey(FinanceTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='salary_records_created')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_records_approved')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-salary_month', '-created_at']
        unique_together = ['staff', 'salary_month']
        verbose_name_plural = 'Staff Salaries'

    def __str__(self):
        return f'{self.staff.username} - {self.salary_month} - ₹{self.net_salary}'

    def save(self, *args, **kwargs):
        if not self.net_salary:
            self.net_salary = self.gross_salary - self.advance - self.deductions - self.other_adjustments
        self.balance = self.net_salary - self.paid_amount
        if not self.voucher_no:
            self.voucher_no = generate_voucher_no('SRN')
        super().save(*args, **kwargs)


class Refund(models.Model):
    REASON_CHOICES = [
        ('cancellation', 'Course Cancellation'),
        ('excess_payment', 'Excess Payment'),
        ('duplicate', 'Duplicate Payment'),
        ('university_refund', 'University Refund'),
        ('fee_adjustment', 'Fee Adjustment'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
    ]

    voucher_no = models.CharField(max_length=30, unique=True)
    admission = models.ForeignKey('admissions.Admission', on_delete=models.PROTECT, related_name='refunds')
    original_payment = models.ForeignKey('fees.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    refund_date = models.DateField()
    refund_mode = models.CharField(max_length=20, choices=FinanceTransaction.PAYMENT_MODES, default='cash')
    account = models.ForeignKey(FinanceAccount, on_delete=models.SET_NULL, null=True, blank=True)
    finance_transaction = models.ForeignKey(FinanceTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='refund_link')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='refunds_created')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds_approved')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-refund_date', '-created_at']

    def __str__(self):
        return f'{self.voucher_no} - ₹{self.amount} - {self.admission.admission_number}'

    def save(self, *args, **kwargs):
        if not self.voucher_no:
            self.voucher_no = generate_voucher_no('RF')
        super().save(*args, **kwargs)


class FinanceSettings(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField(blank=True)
    description = models.CharField(max_length=300, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Finance Settings'

    def __str__(self):
        return f'{self.setting_key}: {self.setting_value}'

    @classmethod
    def get_value(cls, key, default=''):
        try:
            setting = cls.objects.get(setting_key=key)
            return setting.setting_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key, value, description=''):
        obj, created = cls.objects.update_or_create(
            setting_key=key,
            defaults={'setting_value': value, 'description': description}
        )
        return obj


class BankReconciliation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reconciled', 'Reconciled'),
        ('discrepancy', 'Discrepancy'),
    ]

    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, related_name='reconciliations')
    reconciliation_date = models.DateField()
    statement_date = models.DateField(help_text='Bank statement date')
    book_balance = models.DecimalField(max_digits=14, decimal_places=2)
    bank_balance = models.DecimalField(max_digits=14, decimal_places=2)
    outstanding_deposits = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text='Deposits in transit')
    unpresented_cheques = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text='Cheques issued but not yet cleared')
    bank_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    interest_earned = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_adjustments = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reconciled_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    difference = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='bank_reconciliations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reconciliation_date']
        verbose_name_plural = 'Bank Reconciliations'

    def __str__(self):
        return f'{self.account.name} - {self.reconciliation_date} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        self.reconciled_balance = (
            self.bank_balance + self.outstanding_deposits - self.unpresented_cheques
            - self.bank_charges + self.interest_earned + self.other_adjustments
        )
        self.difference = self.book_balance - self.reconciled_balance
        if self.difference == 0:
            self.status = 'reconciled'
        super().save(*args, **kwargs)


class GatewaySettlement(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Settlement'),
        ('settled', 'Settled'),
        ('discrepancy', 'Discrepancy'),
    ]

    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, related_name='gateway_settlements')
    settlement_date = models.DateField()
    period_from = models.DateField()
    period_to = models.DateField()
    total_collected = models.DecimalField(max_digits=14, decimal_places=2, help_text='Total student payments via gateway')
    gateway_fees = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_on_fees = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_settlement = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_credit_date = models.DateField(null=True, blank=True)
    bank_credit_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='gateway_settlements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-settlement_date']
        verbose_name_plural = 'Gateway Settlements'

    def __str__(self):
        return f'{self.account.name} - {self.settlement_date} - ₹{self.net_settlement}'

    def save(self, *args, **kwargs):
        self.net_settlement = self.total_collected - self.gateway_fees - self.gst_on_fees
        super().save(*args, **kwargs)


class Budget(models.Model):
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='budgets')
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')
    year = models.IntegerField()
    month = models.IntegerField(null=True, blank=True, help_text='1-12 for monthly, null for yearly')
    quarter = models.IntegerField(null=True, blank=True, help_text='1-4 for quarterly')
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='budgets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month', 'category__name']
        unique_together = ['category', 'period_type', 'year', 'month', 'quarter']

    def __str__(self):
        period = f'{self.year}'
        if self.month:
            period += f'-{self.month:02d}'
        elif self.quarter:
            period += f'-Q{self.quarter}'
        return f'{self.category.name} - {period} - ₹{self.budget_amount}'

    @property
    def actual_amount(self):
        from django.db.models import Sum
        from datetime import date
        if self.period_type == 'monthly' and self.month:
            start_date = date(self.year, self.month, 1)
            if self.month == 12:
                end_date = date(self.year + 1, 1, 1)
            else:
                end_date = date(self.year, self.month + 1, 1)
        elif self.period_type == 'quarterly' and self.quarter:
            start_month = (self.quarter - 1) * 3 + 1
            start_date = date(self.year, start_month, 1)
            end_month = start_month + 3
            if end_month > 12:
                end_date = date(self.year + 1, end_month - 12, 1)
            else:
                end_date = date(self.year, end_month, 1)
        else:
            start_date = date(self.year, 1, 1)
            end_date = date(self.year + 1, 1, 1)

        return FinanceTransaction.objects.filter(
            category=self.category, direction='out', status='posted',
            transaction_date__gte=start_date, transaction_date__lt=end_date
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    @property
    def variance(self):
        return self.budget_amount - self.actual_amount

    @property
    def variance_percent(self):
        if self.budget_amount == 0:
            return Decimal('0')
        return ((self.budget_amount - self.actual_amount) / self.budget_amount) * 100


class ReminderLog(models.Model):
    REMINDER_TYPES = [
        ('day_not_closed', 'Day Not Closed'),
        ('expense_pending', 'Expense Pending Approval'),
        ('refund_pending', 'Refund Pending Approval'),
        ('salary_pending', 'Salary Pending'),
        ('low_cash', 'Low Cash Balance'),
        ('fee_overdue', 'Fee Overdue'),
        ('university_due', 'University Payment Due'),
        ('budget_exceeded', 'Budget Exceeded'),
    ]

    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_reminders')
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_via = models.CharField(max_length=20, blank=True, help_text='email, sms, or notification')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_reminder_type_display()} - {self.title}'


class BankStatementEntry(models.Model):
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, related_name='statement_entries')
    transaction_date = models.DateField()
    description = models.CharField(max_length=300)
    reference_no = models.CharField(max_length=100, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    matched = models.BooleanField(default=False)
    finance_transaction = models.ForeignKey(FinanceTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date', '-imported_at']
        verbose_name_plural = 'Bank Statement Entries'

    def __str__(self):
        return f'{self.transaction_date} - {self.description} - ₹{self.debit or self.credit}'


class GSTRecord(models.Model):
    GST_TYPES = [
        ('cgst', 'CGST'),
        ('sgst', 'SGST'),
        ('igst', 'IGST'),
    ]

    financial_year = models.CharField(max_length=10)
    quarter = models.IntegerField(choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    gst_type = models.CharField(max_length=5, choices=GST_TYPES)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text='GST rate %')
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    source_type = models.CharField(max_length=20, help_text='income or expense')
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-financial_year', '-quarter']
        verbose_name_plural = 'GST Records'

    def __str__(self):
        return f'{self.financial_year} Q{self.quarter} - {self.gst_type} - ₹{self.gst_amount}'


class FinanceAuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
        ('refund', 'Refunded'),
        ('reversal', 'Reversal'),
        ('reopen_day', 'Reopen Day'),
        ('change_opening', 'Change Opening Balance'),
        ('change_payment', 'Change Payment'),
        ('change_category', 'Change Category'),
        ('change_account', 'Change Account'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50)
    record_id = models.CharField(max_length=50)
    description = models.CharField(max_length=300, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Finance Audit Logs'

    def __str__(self):
        return f'{self.action} {self.module} #{self.record_id}'


class SalaryTemplate(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('biweekly', 'Bi-Weekly'),
        ('weekly', 'Weekly'),
    ]

    staff_name = models.CharField(max_length=150)
    staff_role = models.CharField(max_length=100, blank=True)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    payment_day = models.IntegerField(default=1, help_text='Day of month to generate salary')
    finance_account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_generated = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['staff_name']

    def __str__(self):
        return f'{self.staff_name} - ₹{self.net_payable:,.2f} ({self.get_frequency_display()})'


class RecurringExpense(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=200, help_text='e.g., Office Rent, Internet Bill')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    payment_day = models.IntegerField(default=1, help_text='Day of month/quarter/year to generate')
    payee = models.CharField(max_length=200, blank=True, help_text='Who gets paid')
    finance_account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_generated = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - ₹{self.amount:,.2f} ({self.get_frequency_display()})'


class ScheduledReport(models.Model):
    REPORT_TYPES = [
        ('daily_collection', 'Daily Collection'),
        ('daily_expense', 'Daily Expense'),
        ('cash_flow', 'Cash Flow'),
        ('profit_loss', 'Profit & Loss'),
        ('budget_vs_actual', 'Budget vs Actual'),
        ('gst_report', 'GST Report'),
    ]
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    send_day = models.IntegerField(default=1, help_text='Day of week (1=Mon) or month to send')
    send_time = models.TimeField(default='09:00')
    recipients = models.TextField(help_text='Comma-separated email addresses')
    format = models.CharField(max_length=10, choices=[('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')], default='pdf')
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_report_type_display()} - {self.get_frequency_display()})'
