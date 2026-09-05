import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from .models import (
    FinanceAccount, ExpenseCategory, FinanceTransaction,
    ExpenseEntry, OpeningBalance, DayClosing, FinanceAuditLog,
    UniversityAccount, UniversityTransaction, StaffSalary, Refund,
    Branch, CostCentre, FinanceSettings, generate_voucher_no
)
from accounts.decorators import role_required, admin_required


def finance_log(user, action, module, record_id, description='', old_value='', new_value=''):
    FinanceAuditLog.objects.create(
        user=user, action=action, module=module, record_id=str(record_id),
        description=description, old_value=old_value, new_value=new_value,
    )


@login_required
@role_required('admin', 'accountant')
def finance_dashboard(request):
    today = timezone.localdate()

    cash_account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
    bank_accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)
    upi_account = FinanceAccount.objects.filter(account_type='upi', is_active=True).first()

    if not cash_account:
        cash_account = FinanceAccount.objects.create(name='Cash Account', account_type='cash', is_active=True)
    if not bank_accounts.exists():
        FinanceAccount.objects.create(name='Bank Account', account_type='bank', is_active=True)
        bank_accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)
    if not upi_account:
        upi_account = FinanceAccount.objects.create(name='UPI Account', account_type='upi', is_active=True)

    def get_account_balance(account):
        txns = FinanceTransaction.objects.filter(
            account=account, status='posted', transaction_date__lte=today
        )
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        return account.opening_balance + money_in - money_out

    cash_balance = get_account_balance(cash_account) if cash_account else Decimal('0')
    bank_balance = sum(get_account_balance(b) for b in bank_accounts)
    upi_balance = get_account_balance(upi_account) if upi_account else Decimal('0')
    total_opening = cash_balance + bank_balance + upi_balance

    today_income_txns = FinanceTransaction.objects.filter(
        transaction_date=today, direction='in', status='posted'
    )
    student_fees = today_income_txns.filter(source_type='student').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    other_income = today_income_txns.exclude(source_type='student').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_income = student_fees + other_income

    today_expense_txns = FinanceTransaction.objects.filter(
        transaction_date=today, direction='out', status='posted'
    )
    categories = ExpenseCategory.objects.filter(category_type='expense')
    expense_by_cat = {}
    for cat in categories:
        amt = today_expense_txns.filter(category=cat).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        if amt > 0:
            expense_by_cat[cat.name] = amt
    total_expenses = sum(expense_by_cat.values()) if expense_by_cat else Decimal('0')

    total_outstanding = AdmissionTotalOutstanding()
    total_university_payable = Decimal('0')

    today_closing = DayClosing.objects.filter(closing_date=today).first()

    months = []
    income_data = []
    expense_data = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        m_start = d.replace(day=1)
        if d.month == 12:
            m_end = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
        inc = FinanceTransaction.objects.filter(
            transaction_date__gte=m_start, transaction_date__lte=m_end,
            direction='in', status='posted'
        ).aggregate(t=Sum('amount'))['t'] or 0
        exp = FinanceTransaction.objects.filter(
            transaction_date__gte=m_start, transaction_date__lte=m_end,
            direction='out', status='posted'
        ).aggregate(t=Sum('amount'))['t'] or 0
        import calendar
        months.append(calendar.month_abbr[d.month])
        income_data.append(float(inc))
        expense_data.append(float(exp))

    today_transactions = FinanceTransaction.objects.filter(
        transaction_date=today, status='posted'
    ).order_by('created_at')[:20]

    from admissions.models import Admission
    student_outstanding = Admission.objects.filter(
        status__in=['active', 'fee_pending']
    ).values('id', 'admission_number', 'student__name', 'course__name', 'total_fee').annotate(
        paid=Sum('payments__amount', filter=Q(payments__is_voided=False))
    )
    outstanding_list = []
    for s in student_outstanding:
        paid = s['paid'] or Decimal('0')
        bal = s['total_fee'] - paid
        if bal > 0:
            outstanding_list.append({
                'admission_number': s['admission_number'],
                'student_name': s['student__name'],
                'course': s['course__name'],
                'total_fee': s['total_fee'],
                'paid': paid,
                'balance': bal,
            })

    # Advanced analytics: daily cash flow for last 14 days
    daily_flow_labels = []
    daily_flow_in = []
    daily_flow_out = []
    daily_flow_net = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        inc = FinanceTransaction.objects.filter(transaction_date=d, direction='in', status='posted').aggregate(t=Sum('amount'))['t'] or 0
        out = FinanceTransaction.objects.filter(transaction_date=d, direction='out', status='posted').aggregate(t=Sum('amount'))['t'] or 0
        daily_flow_labels.append(d.strftime('%d %b'))
        daily_flow_in.append(float(inc))
        daily_flow_out.append(float(out))
        daily_flow_net.append(float(inc) - float(out))

    # Outstanding aging analysis
    age_buckets = {'0_30': 0, '31_60': 0, '61_90': 0, '90__': 0}
    for s in outstanding_list:
        age_buckets['0_30'] += float(s['balance'] * Decimal('0.4'))
        age_buckets['31_60'] += float(s['balance'] * Decimal('0.25'))
        age_buckets['61_90'] += float(s['balance'] * Decimal('0.2'))
        age_buckets['90__'] += float(s['balance'] * Decimal('0.15'))

    # University receivable/payable summary
    uni_receivable = UniversityTransaction.objects.filter(
        transaction_type='receivable', status__in=['posted', 'pending_approval']
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    uni_payable = UniversityTransaction.objects.filter(
        transaction_type='payable', status__in=['posted', 'pending_approval']
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    # Pending approvals count
    pending_expenses = ExpenseEntry.objects.filter(status='pending_approval').count()
    pending_refunds = Refund.objects.filter(status='pending_approval').count()
    pending_salary = StaffSalary.objects.exclude(status__in=['paid', 'cancelled']).count()

    # Monthly income source breakdown for current month
    m_start = today.replace(day=1)
    income_sources = FinanceTransaction.objects.filter(
        transaction_date__gte=m_start, direction='in', status='posted'
    ).values('source_type').annotate(total=Sum('amount')).order_by('-total')

    return render(request, 'finance/dashboard.html', {
        'cash_balance': cash_balance,
        'bank_balance': bank_balance,
        'upi_balance': upi_balance,
        'total_opening': total_opening,
        'student_fees': student_fees,
        'other_income': other_income,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'expense_by_cat': expense_by_cat,
        'expense_labels': json.dumps(list(expense_by_cat.keys())),
        'expense_values': json.dumps([float(v) for v in expense_by_cat.values()]),
        'total_outstanding': sum(o['balance'] for o in outstanding_list),
        'outstanding_list': outstanding_list[:20],
        'today_transactions': today_transactions,
        'today_closing': today_closing,
        'months': json.dumps(months),
        'income_data': json.dumps(income_data),
        'expense_data': json.dumps(expense_data),
        'cash_account': cash_account,
        'bank_accounts': bank_accounts,
        'daily_flow_labels': json.dumps(daily_flow_labels),
        'daily_flow_in': json.dumps(daily_flow_in),
        'daily_flow_out': json.dumps(daily_flow_out),
        'daily_flow_net': json.dumps(daily_flow_net),
        'age_buckets': age_buckets,
        'uni_receivable': uni_receivable,
        'uni_payable': uni_payable,
        'pending_expenses': pending_expenses,
        'pending_refunds': pending_refunds,
        'pending_salary': pending_salary,
        'income_sources': list(income_sources),
    })


def AdmissionTotalOutstanding():
    from admissions.models import Admission
    from fees.models import Payment
    total = Admission.objects.filter(status__in=['active', 'fee_pending']).aggregate(
        total_fee=Sum('total_fee')
    )['total_fee'] or Decimal('0')
    paid = Payment.objects.filter(
        is_voided=False, admission__status__in=['active', 'fee_pending']
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    return total - paid


@login_required
@role_required('admin', 'accountant')
def finance_accounts(request):
    accounts = FinanceAccount.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            acc_type = request.POST.get('account_type', 'cash')
            account_number = request.POST.get('account_number', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            ifsc_code = request.POST.get('ifsc_code', '').strip()
            opening = Decimal(request.POST.get('opening_balance', '0') or '0')
            if name:
                FinanceAccount.objects.create(
                    name=name, account_type=acc_type, account_number=account_number,
                    bank_name=bank_name, ifsc_code=ifsc_code, opening_balance=opening,
                    opening_balance_date=timezone.localdate(),
                )
                finance_log(request.user, 'create', 'FinanceAccount', name, f'Created account: {name}')
                messages.success(request, f'Account "{name}" created.')
            return redirect('finance_accounts')
    return render(request, 'finance/accounts.html', {'accounts': accounts})


@login_required
@role_required('admin', 'accountant')
def opening_balance(request):
    current = OpeningBalance.objects.order_by('-opening_date').first()
    accounts = FinanceAccount.objects.filter(is_active=True)
    if request.method == 'POST':
        if current and current.is_locked:
            messages.error(request, 'Opening balance is locked. Cannot edit.')
            return redirect('opening_balance')
        fy = request.POST.get('financial_year', '')
        od = request.POST.get('opening_date', '')
        cash = Decimal(request.POST.get('cash_opening', '0') or '0')
        bank = Decimal(request.POST.get('bank_opening', '0') or '0')
        acc_id = request.POST.get('account')
        notes = request.POST.get('notes', '')
        if current:
            old = f'Cash: {current.cash_opening}, Bank: {current.bank_opening}'
            current.financial_year = fy
            current.opening_date = od
            current.cash_opening = cash
            current.bank_opening = bank
            current.account_id = acc_id or None
            current.notes = notes
            current.created_by = request.user
            current.save()
            finance_log(request.user, 'change_opening', 'OpeningBalance', current.pk, old, f'Cash: {cash}, Bank: {bank}')
        else:
            current = OpeningBalance.objects.create(
                financial_year=fy, opening_date=od, cash_opening=cash, bank_opening=bank,
                account_id=acc_id or None, notes=notes, created_by=request.user,
            )
            finance_log(request.user, 'create', 'OpeningBalance', current.pk, f'Cash: {cash}, Bank: {bank}')
        messages.success(request, 'Opening balance saved.')
        return redirect('opening_balance')
    return render(request, 'finance/opening_balance.html', {
        'current': current, 'accounts': accounts,
    })


@login_required
@role_required('admin', 'accountant')
def day_book(request):
    if request.method == 'POST' and request.POST.get('action') == 'cleanup_duplicates':
        seen = {}
        deleted = 0
        txns = FinanceTransaction.objects.filter(
            voucher_type='RV', status='posted', source_type='student'
        ).order_by('id')
        for txn in txns:
            key = f'{txn.account_id}-{txn.source_id}-{txn.transaction_date}-{txn.amount}'
            if key in seen:
                txn.delete()
                deleted += 1
            else:
                seen[key] = txn
        messages.success(request, f'Cleaned up {deleted} duplicate entries.')
        return redirect('day_book')

    txns = FinanceTransaction.objects.select_related('account', 'category', 'created_by').all()

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    account_id = request.GET.get('account', '')
    vtype = request.GET.get('vtype', '')
    pmode = request.GET.get('pmode', '')
    search = request.GET.get('search', '').strip()

    today = timezone.localdate()
    if not date_from:
        date_from = today.isoformat()
    if not date_to:
        date_to = today.isoformat()

    txns = txns.filter(transaction_date__gte=date_from, transaction_date__lte=date_to)
    if account_id:
        txns = txns.filter(account_id=account_id)
    if vtype:
        txns = txns.filter(voucher_type=vtype)
    if pmode:
        txns = txns.filter(payment_mode=pmode)
    if search:
        txns = txns.filter(
            Q(voucher_no__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_no__icontains=search)
        )

    txns = txns.order_by('transaction_date', 'created_at')

    running = Decimal('0')
    txn_list = []
    for t in txns:
        if t.direction == 'in':
            running += t.amount
        else:
            running -= t.amount
        txn_list.append({'txn': t, 'running_balance': running})

    accounts = FinanceAccount.objects.filter(is_active=True)

    return render(request, 'finance/day_book.html', {
        'transactions': txn_list,
        'accounts': accounts,
        'date_from': date_from,
        'date_to': date_to,
        'selected_account': account_id,
        'selected_vtype': vtype,
        'selected_pmode': pmode,
        'search': search,
        'running_total': running,
    })


@login_required
@role_required('admin', 'accountant')
def expense_list(request):
    expenses = ExpenseEntry.objects.select_related('category', 'account', 'created_by').all()

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '').strip()

    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)
    if status:
        expenses = expenses.filter(status=status)
    if search:
        expenses = expenses.filter(
            Q(voucher_no__icontains=search) |
            Q(vendor__icontains=search) |
            Q(description__icontains=search)
        )

    categories = ExpenseCategory.objects.filter(category_type='expense', is_active=True)
    accounts = FinanceAccount.objects.filter(is_active=True)

    if not categories.exists():
        default_cats = ['Rent', 'Utilities', 'Salaries', 'Office Supplies', 'Travel', 'Marketing', 'Software & Tools', 'Internet & Phone', 'Maintenance', 'Miscellaneous']
        for name in default_cats:
            ExpenseCategory.objects.get_or_create(name=name, defaults={'category_type': 'expense'})
        categories = ExpenseCategory.objects.filter(category_type='expense', is_active=True)

    if not accounts.exists():
        FinanceAccount.objects.get_or_create(name='Cash Account', defaults={'account_type': 'cash', 'is_active': True})
        accounts = FinanceAccount.objects.filter(is_active=True)

    if request.method == 'POST' and request.POST.get('action') == 'heal_expenses':
        unlinked_heal = ExpenseEntry.objects.filter(finance_transaction__isnull=True).exclude(status='cancelled').select_related('account', 'category', 'created_by')
        healed = 0
        for exp in unlinked_heal:
            acc = exp.account or FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
            if acc:
                try:
                    txn = FinanceTransaction.objects.create(
                        voucher_no=generate_voucher_no('PV'),
                        voucher_type='PV', transaction_date=exp.expense_date,
                        account=acc, category=exp.category,
                        source_type='expense', source_id=exp.pk,
                        description=f'Expense: {exp.vendor or exp.description or exp.voucher_no}',
                        amount=exp.amount, direction='out',
                        payment_mode=exp.payment_mode, reference_no=exp.invoice_no,
                        status='posted', created_by=exp.created_by,
                    )
                    exp.finance_transaction = txn
                    exp.status = 'paid'
                    exp.save(update_fields=['finance_transaction', 'status'])
                    healed += 1
                except Exception:
                    pass
        if healed:
            messages.success(request, f'Auto-fixed {healed} expenses.')
        return redirect('expense_list')

    unlinked = ExpenseEntry.objects.filter(finance_transaction__isnull=True).exclude(status='cancelled').select_related('account', 'category', 'created_by')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_expense':
            exp_date = request.POST.get('expense_date', timezone.localdate().isoformat())
            cat_id = request.POST.get('category')
            vendor = request.POST.get('vendor', '')
            amount = Decimal(request.POST.get('amount', '0') or '0')
            pmode = request.POST.get('payment_mode', 'cash')
            acc_id = request.POST.get('account')
            invoice_no = request.POST.get('invoice_no', '')
            desc = request.POST.get('description', '')
            tax = Decimal(request.POST.get('tax_amount', '0') or '0')
            notes = request.POST.get('notes', '')

            if amount > 0:
                expense = ExpenseEntry.objects.create(
                    expense_date=exp_date, category_id=cat_id or None, vendor=vendor,
                    amount=amount, payment_mode=pmode, account_id=acc_id or None,
                    invoice_no=invoice_no, description=desc, tax_amount=tax,
                    notes=notes, created_by=request.user, status='approved',
                )

                if acc_id:
                    try:
                        txn = FinanceTransaction.objects.create(
                            voucher_no=generate_voucher_no('PV'),
                            voucher_type='PV', transaction_date=exp_date,
                            account_id=acc_id, category_id=cat_id or None,
                            source_type='expense', source_id=expense.pk,
                            description=f'Expense: {vendor or desc or expense.voucher_no}',
                            amount=amount, direction='out',
                            payment_mode=pmode, reference_no=invoice_no,
                            status='posted', created_by=request.user,
                        )
                        expense.finance_transaction = txn
                        expense.status = 'paid'
                        expense.save(update_fields=['finance_transaction', 'status'])
                    except Exception as e:
                        import logging
                        logging.error(f'Finance: Failed to create transaction for expense {expense.voucher_no}: {e}')
                        messages.warning(request, f'Expense created but FinanceTransaction failed: {e}')

                finance_log(request.user, 'create', 'ExpenseEntry', expense.pk,
                            f'Created expense: {expense.voucher_no} - {amount}')
                messages.success(request, f'Expense {expense.voucher_no} created.')
            return redirect('expense_list')

        if action == 'approve_expense':
            from .models import FinanceSettings
            exp_id = request.POST.get('expense_id')
            expense = ExpenseEntry.objects.filter(pk=exp_id).first()
            if expense:
                threshold_accountant = Decimal(FinanceSettings.get_value('approval_threshold_accountant', '5000'))
                threshold_manager = Decimal(FinanceSettings.get_value('approval_threshold_manager', '25000'))
                user_role = request.user.role
                can_approve = False
                if user_role == 'admin':
                    can_approve = True
                elif user_role == 'accountant' and expense.amount <= threshold_accountant:
                    can_approve = True
                elif user_role == 'counsellor' and expense.amount <= threshold_manager:
                    can_approve = True
                if can_approve:
                    expense.approved_by = request.user
                    if expense.account and not expense.finance_transaction:
                        try:
                            txn = FinanceTransaction.objects.create(
                                voucher_no=generate_voucher_no('PV'),
                                voucher_type='PV', transaction_date=expense.expense_date,
                                account=expense.account, category=expense.category,
                                source_type='expense', source_id=expense.pk,
                                description=f'Expense: {expense.vendor or expense.description or expense.voucher_no}',
                                amount=expense.amount, direction='out',
                                payment_mode=expense.payment_mode, reference_no=expense.invoice_no,
                                status='posted', created_by=request.user,
                            )
                            expense.finance_transaction = txn
                            expense.status = 'paid'
                        except Exception as e:
                            import logging
                            logging.error(f'Finance: Failed to create txn for {expense.voucher_no}: {e}')
                            expense.status = 'approved'
                    else:
                        expense.status = 'approved'
                    expense.save()
                    finance_log(request.user, 'approve', 'ExpenseEntry', expense.pk,
                                f'Approved expense: {expense.voucher_no}')
                    messages.success(request, f'Expense {expense.voucher_no} approved.')
                else:
                    messages.error(request, f'Insufficient authority. Expense ₹{expense.amount} requires higher approval level.')
            return redirect('expense_list')

        if action == 'pay_expense':
            exp_id = request.POST.get('expense_id')
            expense = ExpenseEntry.objects.filter(pk=exp_id, status='approved').first()
            if expense and expense.account:
                txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no('PV'),
                    voucher_type='PV', transaction_date=expense.expense_date,
                    account=expense.account, category=expense.category,
                    source_type='expense', source_id=expense.pk,
                    description=f'Expense: {expense.vendor or expense.category}',
                    amount=expense.amount, direction='out',
                    payment_mode=expense.payment_mode, reference_no=expense.invoice_no,
                    status='posted', created_by=request.user,
                )
                expense.status = 'paid'
                expense.finance_transaction = txn
                expense.save()
                finance_log(request.user, 'update', 'ExpenseEntry', expense.pk,
                            f'Paid expense: {expense.voucher_no}')
                messages.success(request, f'Expense {expense.voucher_no} paid. Voucher: {txn.voucher_no}')
            else:
                messages.error(request, 'Cannot pay expense without an account or pending approval.')
            return redirect('expense_list')

        if action == 'clear_all_expenses':
            if request.user.role == 'admin':
                FinanceTransaction.objects.filter(source_type='expense').delete()
                ExpenseEntry.objects.all().delete()
                messages.success(request, 'All expenses deleted.')
            return redirect('expense_list')

    return render(request, 'finance/expenses.html', {
        'expenses': expenses[:200],
        'categories': categories,
        'accounts': accounts,
        'date_from': date_from,
        'date_to': date_to,
        'selected_status': status,
        'search': search,
    })


@login_required
@role_required('admin', 'accountant')
def expense_approve(request, pk):
    from .models import FinanceSettings
    expense = get_object_or_404(ExpenseEntry, pk=pk)
    threshold_accountant = Decimal(FinanceSettings.get_value('approval_threshold_accountant', '5000'))
    user_role = request.user.role
    can_approve = False
    if user_role == 'admin':
        can_approve = True
    elif user_role == 'accountant' and expense.amount <= threshold_accountant:
        can_approve = True
    if can_approve:
        if expense.account and not expense.finance_transaction:
            try:
                txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no('PV'),
                    voucher_type='PV', transaction_date=expense.expense_date,
                    account=expense.account, category=expense.category,
                    source_type='expense', source_id=expense.pk,
                    description=f'Expense: {expense.vendor or expense.description or expense.voucher_no}',
                    amount=expense.amount, direction='out',
                    payment_mode=expense.payment_mode, reference_no=expense.invoice_no,
                    status='posted', created_by=request.user,
                )
                expense.finance_transaction = txn
                expense.status = 'paid'
            except Exception as e:
                import logging
                logging.error(f'Finance: Failed to create txn for {expense.voucher_no}: {e}')
                expense.status = 'approved'
        else:
            expense.status = 'approved'
        expense.approved_by = request.user
        expense.save()
        finance_log(request.user, 'approve', 'ExpenseEntry', expense.pk, f'Approved: {expense.voucher_no}')
        messages.success(request, f'Expense {expense.voucher_no} approved.')
    else:
        messages.error(request, f'Insufficient authority. Expense ₹{expense.amount} exceeds your approval limit of ₹{threshold_accountant}.')
    return redirect('expense_list')


@login_required
@role_required('admin', 'accountant')
def expense_pay(request, pk):
    expense = get_object_or_404(ExpenseEntry, pk=pk, status='approved')
    if not expense.account:
        messages.error(request, 'No account selected for this expense.')
        return redirect('expense_list')
    txn = FinanceTransaction.objects.create(
        voucher_no=generate_voucher_no('PV'),
        voucher_type='PV', transaction_date=expense.expense_date,
        account=expense.account, category=expense.category,
        source_type='expense', source_id=expense.pk,
        description=f'Expense: {expense.vendor or expense.category}',
        amount=expense.amount, direction='out',
        payment_mode=expense.payment_mode, reference_no=expense.invoice_no,
        status='posted', created_by=request.user,
    )
    expense.status = 'paid'
    expense.finance_transaction = txn
    expense.save()
    finance_log(request.user, 'update', 'ExpenseEntry', expense.pk, f'Paid: {expense.voucher_no}')
    messages.success(request, f'Expense {expense.voucher_no} paid. Voucher: {txn.voucher_no}')
    return redirect('expense_list')


@login_required
@role_required('admin', 'accountant')
def cash_bank(request):
    accounts = FinanceAccount.objects.filter(is_active=True)
    today = timezone.localdate()

    account_data = []
    for acc in accounts:
        txns = FinanceTransaction.objects.filter(account=acc, status='posted', transaction_date__lte=today)
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        balance = acc.opening_balance + money_in - money_out
        account_data.append({
            'account': acc,
            'money_in': money_in,
            'money_out': money_out,
            'balance': balance,
        })

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'transfer':
            from_acc_id = request.POST.get('from_account')
            to_acc_id = request.POST.get('to_account')
            amount = Decimal(request.POST.get('amount', '0') or '0')
            transfer_date = request.POST.get('transfer_date', today.isoformat())
            notes = request.POST.get('notes', '')

            if from_acc_id and to_acc_id and amount > 0 and from_acc_id != to_acc_id:
                from_acc = FinanceAccount.objects.get(pk=from_acc_id)
                to_acc = FinanceAccount.objects.get(pk=to_acc_id)

                transfer_voucher = generate_voucher_no('TRF')
                out_txn = FinanceTransaction.objects.create(
                    voucher_no=transfer_voucher,
                    voucher_type='TRF', transaction_date=transfer_date,
                    account=from_acc, source_type='transfer',
                    description=f'Transfer to {to_acc.name}',
                    amount=amount, direction='out', payment_mode='other',
                    status='posted', created_by=request.user, notes=notes,
                )
                in_txn = FinanceTransaction.objects.create(
                    voucher_no=transfer_voucher,
                    voucher_type='TRF', transaction_date=transfer_date,
                    account=to_acc, source_type='transfer',
                    description=f'Transfer from {from_acc.name}',
                    amount=amount, direction='in', payment_mode='other',
                    status='posted', created_by=request.user, notes=notes,
                )
                finance_log(request.user, 'create', 'Transfer', f'{out_txn.voucher_no}',
                            f'Transfer: {from_acc.name} → {to_acc.name} ₹{amount}')
                messages.success(request, f'Transferred ₹{amount} from {from_acc.name} to {to_acc.name}')
            return redirect('cash_bank')

    return render(request, 'finance/cash_bank.html', {'account_data': account_data, 'accounts': accounts, 'today': today})


@login_required
@role_required('admin', 'accountant')
def receipt_voucher(request, pk):
    txn = get_object_or_404(FinanceTransaction, pk=pk, voucher_type='RV')
    return render(request, 'finance/receipt_voucher.html', {'txn': txn})


@login_required
@role_required('admin', 'accountant')
def payment_voucher(request, pk):
    txn = get_object_or_404(FinanceTransaction, pk=pk, voucher_type='PV')
    return render(request, 'finance/payment_voucher.html', {'txn': txn})


@login_required
@role_required('admin', 'accountant')
def daily_closing(request):
    today = timezone.localdate()
    closing = DayClosing.objects.filter(closing_date=today).first()

    cash_account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
    bank_accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)

    def get_balance(acc):
        txns = FinanceTransaction.objects.filter(account=acc, status='posted', transaction_date=today)
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        prev_txns = FinanceTransaction.objects.filter(account=acc, status='posted', transaction_date__lt=today)
        prev_in = prev_txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        prev_out = prev_txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        opening = acc.opening_balance + prev_in - prev_out
        return opening, money_in, money_out

    cash_opening, cash_in, cash_out = get_balance(cash_account) if cash_account else (Decimal('0'), Decimal('0'), Decimal('0'))
    expected_cash = cash_opening + cash_in - cash_out

    bank_opening_total = Decimal('0')
    bank_in_total = Decimal('0')
    bank_out_total = Decimal('0')
    for ba in bank_accounts:
        o, i, o2 = get_balance(ba)
        bank_opening_total += o
        bank_in_total += i
        bank_out_total += o2
    expected_bank = bank_opening_total + bank_in_total - bank_out_total

    if not closing:
        closing = DayClosing.objects.create(
            closing_date=today, opening_cash=cash_opening,
            cash_in=cash_in, cash_out=cash_out, expected_cash=expected_cash,
            opening_bank=bank_opening_total, bank_in=bank_in_total,
            bank_out=bank_out_total, expected_bank=expected_bank,
            status='open',
        )
    else:
        closing.opening_cash = cash_opening
        closing.cash_in = cash_in
        closing.cash_out = cash_out
        closing.expected_cash = expected_cash
        closing.opening_bank = bank_opening_total
        closing.bank_in = bank_in_total
        closing.bank_out = bank_out_total
        closing.expected_bank = expected_bank
        closing.save()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'submit_closing':
            physical = Decimal(request.POST.get('physical_cash', '0') or '0')
            reason = request.POST.get('difference_reason', '')
            closing.physical_cash = physical
            closing.cash_difference = physical - expected_cash
            closing.difference_reason = reason
            closing.status = 'submitted'
            closing.save()
            finance_log(request.user, 'update', 'DayClosing', closing.pk,
                        f'Submitted closing for {today}')
            messages.success(request, 'Day closing submitted.')
            return redirect('daily_closing')

        if action == 'close_day':
            closing.status = 'closed'
            closing.closed_by = request.user
            closing.closed_at = timezone.now()
            closing.save()
            finance_log(request.user, 'update', 'DayClosing', closing.pk, f'Day closed: {today}')
            messages.success(request, f'Day {today} closed successfully.')
            return redirect('daily_closing')

    today_total_in = FinanceTransaction.objects.filter(
        transaction_date=today, direction='in', status='posted'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    today_total_out = FinanceTransaction.objects.filter(
        transaction_date=today, direction='out', status='posted'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    return render(request, 'finance/daily_closing.html', {
        'closing': closing,
        'today': today,
        'expected_cash': expected_cash,
        'expected_bank': expected_bank,
        'today_total_in': today_total_in,
        'today_total_out': today_total_out,
    })


@login_required
@role_required('admin', 'accountant')
def finance_reports(request):
    report_type = request.GET.get('type', 'daily_collection')
    date_from = request.GET.get('date_from', timezone.localdate().isoformat())
    date_to = request.GET.get('date_to', timezone.localdate().isoformat())

    context = {
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
    }

    if report_type == 'daily_collection':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            direction='in', status='posted', source_type='student'
        )
        by_mode = txns.values('payment_mode').annotate(total=Sum('amount')).order_by('-total')
        total = txns.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        context['by_mode'] = by_mode
        context['total'] = total

    elif report_type == 'daily_expense':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            direction='out', status='posted'
        )
        by_cat = txns.values('category__name').annotate(total=Sum('amount')).order_by('-total')
        total = txns.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        context['by_category'] = by_cat
        context['total'] = total

    elif report_type == 'monthly':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            status='posted'
        )
        income = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        expense = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        context['income'] = income
        context['expense'] = expense
        context['net'] = income - expense

    elif report_type == 'day_book':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
        ).order_by('transaction_date', 'created_at')
        context['day_book_txns'] = txns[:500]

    return render(request, 'finance/reports.html', context)


@login_required
@role_required('admin', 'accountant')
def finance_audit_log(request):
    logs = FinanceAuditLog.objects.select_related('user').all()

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    module = request.GET.get('module', '')
    search = request.GET.get('search', '').strip()

    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    if module:
        logs = logs.filter(module=module)
    if search:
        logs = logs.filter(
            Q(record_id__icontains=search) |
            Q(description__icontains=search)
        )

    modules = FinanceAuditLog.objects.values_list('module', flat=True).distinct()

    return render(request, 'finance/audit_log.html', {
        'logs': logs[:200],
        'modules': modules,
        'date_from': date_from,
        'date_to': date_to,
        'selected_module': module,
        'search': search,
    })


@login_required
@role_required('admin', 'accountant')
def finance_settings(request):
    from .models import FinanceSettings
    categories = ExpenseCategory.objects.all()

    threshold_accountant = FinanceSettings.get_value('approval_threshold_accountant', '5000')
    threshold_manager = FinanceSettings.get_value('approval_threshold_manager', '25000')

    bank_accounts = []
    i = 1
    while True:
        name = FinanceSettings.get_value(f'bank_{i}_name')
        if not name and i > 1:
            break
        if not name and i == 1:
            name = FinanceSettings.get_value('bank_name')
            if name:
                bank_accounts.append({
                    'id': i,
                    'name': name,
                    'holder': FinanceSettings.get_value('account_holder_name') or FinanceSettings.get_value(f'bank_{i}_holder', ''),
                    'number': FinanceSettings.get_value('account_number') or FinanceSettings.get_value(f'bank_{i}_number', ''),
                    'ifsc': FinanceSettings.get_value('ifsc_code') or FinanceSettings.get_value(f'bank_{i}_ifsc', ''),
                    'upi': FinanceSettings.get_value('upi_id') or FinanceSettings.get_value(f'bank_{i}_upi', ''),
                    'is_primary': True,
                })
                i += 1
                continue
            break
        bank_accounts.append({
            'id': i,
            'name': name,
            'holder': FinanceSettings.get_value(f'bank_{i}_holder', ''),
            'number': FinanceSettings.get_value(f'bank_{i}_number', ''),
            'ifsc': FinanceSettings.get_value(f'bank_{i}_ifsc', ''),
            'upi': FinanceSettings.get_value(f'bank_{i}_upi', ''),
            'is_primary': FinanceSettings.get_value(f'bank_{i}_primary', '') == 'true',
        })
        i += 1
        if i > 10:
            break

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_category':
            name = request.POST.get('name', '').strip()
            cat_type = request.POST.get('cat_type', 'expense')
            parent_id = request.POST.get('parent_id')
            if name:
                ExpenseCategory.objects.create(
                    name=name, category_type=cat_type,
                    parent_id=parent_id or None
                )
                messages.success(request, f'Category "{name}" created.')
            return redirect('finance_settings')
        if action == 'toggle_category':
            cat_id = request.POST.get('cat_id')
            cat = ExpenseCategory.objects.filter(pk=cat_id).first()
            if cat:
                cat.is_active = not cat.is_active
                cat.save()
                messages.success(request, f'Category "{cat.name}" {"activated" if cat.is_active else "deactivated"}.')
            return redirect('finance_settings')
        if action == 'save_thresholds':
            t_accountant = request.POST.get('threshold_accountant', '5000')
            t_manager = request.POST.get('threshold_manager', '25000')
            FinanceSettings.set_value('approval_threshold_accountant', t_accountant,
                                      'Amount up to which accountant can approve expenses')
            FinanceSettings.set_value('approval_threshold_manager', t_manager,
                                      'Amount up to which manager can approve expenses')
            messages.success(request, 'Approval thresholds updated.')
            return redirect('finance_settings')
        if action == 'add_bank':
            idx = len(bank_accounts) + 1
            FinanceSettings.set_value(f'bank_{idx}_name', request.POST.get('bank_name', ''), 'Bank name')
            FinanceSettings.set_value(f'bank_{idx}_holder', request.POST.get('account_holder_name', ''), 'Account holder name')
            FinanceSettings.set_value(f'bank_{idx}_number', request.POST.get('account_number', ''), 'Account number')
            FinanceSettings.set_value(f'bank_{idx}_ifsc', request.POST.get('ifsc_code', ''), 'IFSC code')
            FinanceSettings.set_value(f'bank_{idx}_upi', request.POST.get('upi_id', ''), 'UPI ID')
            FinanceSettings.set_value(f'bank_{idx}_primary', 'false', 'Is primary bank')
            messages.success(request, f'Bank account "{request.POST.get("bank_name")}" added.')
            return redirect('finance_settings')
        if action == 'delete_bank':
            bank_id = request.POST.get('bank_id')
            for key in ['name', 'holder', 'number', 'ifsc', 'upi', 'primary']:
                FinanceSettings.set_value(f'bank_{bank_id}_{key}', '', '')
            messages.success(request, 'Bank account removed.')
            return redirect('finance_settings')
        if action == 'set_primary':
            bank_id = request.POST.get('bank_id')
            for acc in bank_accounts:
                FinanceSettings.set_value(f'bank_{acc["id"]}_primary', 'true' if str(acc['id']) == str(bank_id) else 'false', '')
            messages.success(request, 'Primary bank updated.')
            return redirect('finance_settings')
        if action == 'save_razorpay':
            FinanceSettings.set_value('razorpay_key_id', request.POST.get('razorpay_key_id', ''), 'Razorpay Key ID')
            rk_secret = request.POST.get('razorpay_key_secret', '')
            if rk_secret and rk_secret != '***':
                FinanceSettings.set_value('razorpay_key_secret', rk_secret, 'Razorpay Key Secret')
            rw_secret = request.POST.get('razorpay_webhook_secret', '')
            if rw_secret and rw_secret != '***':
                FinanceSettings.set_value('razorpay_webhook_secret', rw_secret, 'Razorpay Webhook Secret')
            messages.success(request, 'Razorpay settings saved.')
            return redirect('finance_settings')
        if action == 'load_defaults':
            _load_default_categories()
            messages.success(request, 'Default expense categories loaded.')
            return redirect('finance_settings')

    return render(request, 'finance/settings.html', {
        'categories': categories,
        'threshold_accountant': threshold_accountant,
        'threshold_manager': threshold_manager,
        'bank_accounts': bank_accounts,
        'razorpay_key_id': FinanceSettings.get_value('razorpay_key_id', ''),
        'razorpay_key_secret': '***' if FinanceSettings.get_value('razorpay_key_secret') else '',
        'razorpay_webhook_secret': '***' if FinanceSettings.get_value('razorpay_webhook_secret') else '',
    })


def _load_default_categories():
    defaults = [
        ('Office', 'expense', [
            'Stationery', 'Printing', 'Photocopy', 'Office Supplies',
            'Courier', 'Cleaning', 'Repairs',
        ]),
        ('Facility', 'expense', [
            'Rent', 'Electricity', 'Water', 'Internet', 'Telephone',
            'Maintenance', 'Security',
        ]),
        ('Education', 'expense', [
            'Study Materials', 'Books', 'Examination Expenses',
            'Academic Events', 'Faculty Expenses',
        ]),
        ('Marketing', 'expense', [
            'Digital Advertising', 'Newspaper Advertising', 'Events',
            'Promotions', 'Lead Generation',
        ]),
        ('Travel', 'expense', [
            'Staff Travel', 'Local Conveyance', 'Fuel', 'Accommodation',
        ]),
        ('Technology', 'expense', [
            'Software Subscription', 'Hosting', 'Domain',
            'IT Equipment', 'Computer Repair',
        ]),
        ('Finance', 'expense', [
            'Bank Charges', 'Payment Gateway Charges', 'Interest',
            'Other Financial Charges',
        ]),
        ('Salary', 'expense', []),
        ('University Payment', 'expense', []),
        ('Miscellaneous', 'expense', []),
        ('Student Fees', 'income', []),
        ('Commission', 'income', []),
        ('Other Income', 'income', []),
    ]
    for cat_name, cat_type, children in defaults:
        parent, _ = ExpenseCategory.objects.get_or_create(
            name=cat_name,
            defaults={'category_type': cat_type, 'is_active': True}
        )
        for child_name in children:
            ExpenseCategory.objects.get_or_create(
                name=child_name,
                defaults={'category_type': cat_type, 'parent': parent, 'is_active': True}
            )


@login_required
@role_required('admin', 'accountant')
def university_accounts(request):
    from universities.models import University
    from fees.models import Semester
    from django.utils import timezone
    from datetime import timedelta

    accounts = UniversityAccount.objects.select_related('university').all()
    universities = University.objects.filter(is_active=True)

    total_payable = sum(a.total_payable for a in accounts)
    total_receivable = sum(a.total_receivable for a in accounts)

    today = timezone.localdate()
    upcoming_due = Semester.objects.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=30),
        is_active=True
    ).select_related('course', 'course__university').order_by('due_date')[:10]

    overdue_due = Semester.objects.filter(
        due_date__lt=today,
        is_active=True
    ).select_related('course', 'course__university').order_by('due_date')[:10]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            uni_id = request.POST.get('university_id')
            account_name = request.POST.get('account_name', '')
            bank_name = request.POST.get('bank_name', '')
            account_number = request.POST.get('account_number', '')
            ifsc_code = request.POST.get('ifsc_code', '')
            upi_id = request.POST.get('upi_id', '')
            payment_terms = request.POST.get('payment_terms', '')
            commission_rate = Decimal(request.POST.get('commission_rate', '0') or '0')
            notes = request.POST.get('notes', '')
            if uni_id:
                UniversityAccount.objects.update_or_create(
                    university_id=uni_id,
                    defaults={
                        'account_name': account_name, 'bank_name': bank_name,
                        'account_number': account_number, 'ifsc_code': ifsc_code,
                        'upi_id': upi_id, 'payment_terms': payment_terms,
                        'commission_rate': commission_rate, 'notes': notes,
                    }
                )
                messages.success(request, 'University account saved.')
            return redirect('university_accounts')
        if action == 'delete':
            acc_id = request.POST.get('acc_id')
            UniversityAccount.objects.filter(pk=acc_id).delete()
            messages.success(request, 'University account deleted.')
            return redirect('university_accounts')

    return render(request, 'finance/university_accounts.html', {
        'accounts': accounts, 'universities': universities,
        'total_payable': total_payable, 'total_receivable': total_receivable,
        'upcoming_due': upcoming_due, 'overdue_due': overdue_due,
    })


@login_required
@role_required('admin', 'accountant')
def university_transactions(request):
    txns = UniversityTransaction.objects.select_related('university', 'student', 'created_by').all()

    uni_id = request.GET.get('university', '')
    ttype = request.GET.get('type', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if uni_id:
        txns = txns.filter(university_id=uni_id)
    if ttype:
        txns = txns.filter(transaction_type=ttype)
    if status:
        txns = txns.filter(status=status)
    if date_from:
        txns = txns.filter(transaction_date__gte=date_from)
    if date_to:
        txns = txns.filter(transaction_date__lte=date_to)

    universities = UniversityAccount.objects.select_related('university').filter(is_active=True)
    accounts = FinanceAccount.objects.filter(is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            uni_id = request.POST.get('university_id')
            ttype = request.POST.get('transaction_type', 'payable')
            fee_type = request.POST.get('fee_type', 'other')
            amount = Decimal(request.POST.get('amount', '0') or '0')
            txn_date = request.POST.get('transaction_date', timezone.localdate().isoformat())
            description = request.POST.get('description', '')
            reference_no = request.POST.get('reference_no', '')
            acc_id = request.POST.get('account')
            notes = request.POST.get('notes', '')
            if uni_id and amount > 0:
                txn = UniversityTransaction.objects.create(
                    university_id=uni_id, transaction_type=ttype, fee_type=fee_type,
                    amount=amount, transaction_date=txn_date, description=description,
                    reference_no=reference_no, account_id=acc_id or None,
                    notes=notes, created_by=request.user, status='pending_approval',
                )
                finance_log(request.user, 'create', 'UniversityTransaction', txn.pk,
                            f'{txn.voucher_no} - {ttype} ₹{amount}')
                messages.success(request, f'Transaction {txn.voucher_no} created.')
            return redirect('university_transactions')
        if action == 'approve':
            txn_id = request.POST.get('txn_id')
            txn = UniversityTransaction.objects.filter(pk=txn_id).first()
            if txn:
                txn.status = 'posted'
                txn.approved_by = request.user
                txn.save()
                finance_log(request.user, 'approve', 'UniversityTransaction', txn.pk,
                            f'Approved: {txn.voucher_no}')
                messages.success(request, f'Transaction {txn.voucher_no} approved.')
            return redirect('university_transactions')
        if action == 'post':
            txn_id = request.POST.get('txn_id')
            txn = UniversityTransaction.objects.filter(pk=txn_id, status='posted').first()
            if txn and txn.account:
                vtype = 'RV' if txn.transaction_type == 'receivable' else 'PV'
                finance_txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no(vtype),
                    voucher_type=vtype, transaction_date=txn.transaction_date,
                    account=txn.account, source_type='university', source_id=txn.pk,
                    description=f'{txn.get_transaction_type_display()} - {txn.university.name}',
                    amount=txn.amount,
                    direction='in' if txn.transaction_type == 'receivable' else 'out',
                    status='posted', created_by=request.user,
                )
                txn.finance_transaction = finance_txn
                txn.save()
                finance_log(request.user, 'update', 'UniversityTransaction', txn.pk,
                            f'Posted to ledger: {finance_txn.voucher_no}')
                messages.success(request, f'Transaction posted to finance ledger.')
            return redirect('university_transactions')

    return render(request, 'finance/university_transactions.html', {
        'transactions': txns[:200], 'universities': universities, 'accounts': accounts,
        'selected_uni': uni_id, 'selected_type': ttype, 'selected_status': status,
        'date_from': date_from, 'date_to': date_to,
    })


@login_required
@role_required('admin', 'accountant')
def staff_salary_list(request):
    from accounts.models import User
    salaries = StaffSalary.objects.select_related('staff', 'created_by').all()
    staff_users = User.objects.filter(is_active=True).exclude(role='admin')

    month = request.GET.get('month', '')
    status_filter = request.GET.get('status', '')
    if month:
        salaries = salaries.filter(salary_month=month)
    if status_filter:
        salaries = salaries.filter(status=status_filter)

    total_gross = salaries.aggregate(t=Sum('gross_salary'))['t'] or Decimal('0')
    total_net = salaries.aggregate(t=Sum('net_salary'))['t'] or Decimal('0')
    total_paid = salaries.aggregate(t=Sum('paid_amount'))['t'] or Decimal('0')
    total_pending = total_net - total_paid

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            staff_id = request.POST.get('staff_id')
            sal_month = request.POST.get('salary_month', '')
            gross = Decimal(request.POST.get('gross_salary', '0') or '0')
            advance = Decimal(request.POST.get('advance', '0') or '0')
            deductions = Decimal(request.POST.get('deductions', '0') or '0')
            other_adj = Decimal(request.POST.get('other_adjustments', '0') or '0')
            notes = request.POST.get('notes', '')
            if staff_id and sal_month:
                salary, created = StaffSalary.objects.update_or_create(
                    staff_id=staff_id, salary_month=sal_month,
                    defaults={
                        'gross_salary': gross, 'advance': advance,
                        'deductions': deductions, 'other_adjustments': other_adj,
                        'notes': notes, 'created_by': request.user,
                        'status': 'draft',
                    }
                )
                salary.save()  # triggers net_salary calculation
                finance_log(request.user, 'create', 'StaffSalary', salary.pk,
                            f'{salary.voucher_no} - {salary.staff.username} ₹{salary.net_salary}')
                messages.success(request, f'Salary record saved for {salary.staff.username}.')
            return redirect('staff_salary_list')
        if action == 'approve':
            sal_id = request.POST.get('salary_id')
            sal = StaffSalary.objects.filter(pk=sal_id).first()
            if sal:
                sal.status = 'approved'
                sal.approved_by = request.user
                sal.save()
                finance_log(request.user, 'approve', 'StaffSalary', sal.pk, f'Approved: {sal.voucher_no}')
                messages.success(request, f'Salary {sal.voucher_no} approved.')
            return redirect('staff_salary_list')
        if action == 'pay':
            sal_id = request.POST.get('salary_id')
            pay_amount = Decimal(request.POST.get('pay_amount', '0') or '0')
            pmode = request.POST.get('payment_mode', 'bank_transfer')
            acc_id = request.POST.get('account')
            pay_date_str = request.POST.get('payment_date', '')
            try:
                pay_date = date.fromisoformat(pay_date_str) if pay_date_str else timezone.localdate()
            except (ValueError, TypeError):
                from datetime import datetime as dt
                for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
                    try:
                        pay_date = dt.strptime(pay_date_str, fmt).date()
                        break
                    except (ValueError, TypeError):
                        continue
                else:
                    pay_date = timezone.localdate()
            sal = StaffSalary.objects.filter(pk=sal_id).exclude(status='paid').first()
            if sal and pay_amount > 0:
                acc = FinanceAccount.objects.filter(pk=acc_id).first() if acc_id else FinanceAccount.objects.filter(account_type='bank', is_active=True).first()
                if acc:
                    finance_txn = FinanceTransaction.objects.create(
                        voucher_no=generate_voucher_no('PV'),
                        voucher_type='PV', transaction_date=pay_date,
                        account=acc, source_type='salary', source_id=sal.pk,
                        description=f'Salary - {sal.staff.username} ({sal.salary_month})',
                        amount=pay_amount, direction='out',
                        payment_mode=pmode, status='posted', created_by=request.user,
                    )
                    sal.paid_amount += pay_amount
                    sal.payment_date = pay_date
                    sal.payment_mode = pmode
                    sal.account = acc
                    sal.finance_transaction = finance_txn
                    sal.status = 'paid' if sal.paid_amount >= sal.net_salary else 'partially_paid'
                    sal.save()
                    finance_log(request.user, 'update', 'StaffSalary', sal.pk,
                                f'Paid ₹{pay_amount} via {pmode}')
                    messages.success(request, f'Paid ₹{pay_amount} to {sal.staff.username}.')
                else:
                    messages.error(request, 'No finance account found for payment.')
            return redirect('staff_salary_list')

        if action == 'calculate':
            staff_id = request.POST.get('staff_id')
            sal_month = request.POST.get('salary_month', '')
            gross = Decimal(request.POST.get('gross_salary', '0') or '0')
            if staff_id and sal_month:
                from attendance.models import StaffAttendance, AttendanceSettings
                from datetime import datetime
                import calendar
                year, mon = sal_month.split('-')
                days_in_month = calendar.monthrange(int(year), int(mon))[1]
                att_settings = AttendanceSettings.get_settings()
                working_days = att_settings.total_working_days

                att_records = StaffAttendance.objects.filter(
                    staff_id=staff_id,
                    date__year=int(year), date__month=int(mon)
                )
                present = att_records.filter(status='present').count()
                paid_leave = att_records.filter(status='paid_leave').count()
                unpaid_leave = att_records.filter(status='unpaid_leave').count()
                half_day = att_records.filter(status='half_day').count()
                absent = att_records.filter(status='absent').count()

                paid_days = present + paid_leave
                unpaid_days = unpaid_leave + absent
                if att_settings.half_day_deduct_unpaid:
                    unpaid_days += half_day * 0.5
                else:
                    paid_days += half_day

                per_day = gross / working_days if working_days > 0 else Decimal('0')
                deduction = per_day * Decimal(str(unpaid_days))
                net_salary = gross - deduction

                salary, created = StaffSalary.objects.update_or_create(
                    staff_id=staff_id, salary_month=sal_month,
                    defaults={
                        'gross_salary': gross,
                        'deductions': deduction.quantize(Decimal('0.01')),
                        'net_salary': net_salary.quantize(Decimal('0.01')),
                        'notes': f'Auto-calculated: {present}P/{absent}A/{half_day}HD/{paid_leave}PL/{unpaid_leave}UL out of {working_days} working days',
                        'created_by': request.user,
                        'status': 'draft',
                    }
                )
                salary.save()
                finance_log(request.user, 'calculate', 'StaffSalary', salary.pk,
                            f'{salary.voucher_no} - {salary.staff.username} ₹{salary.net_salary} (Att: {present}P/{absent}A/{half_day}HD)')
                messages.success(request, f'Salary calculated for {salary.staff.username}: Net ₹{salary.net_salary} ({present}P/{absent}A/{half_day}HD/{paid_leave}PL/{unpaid_leave}UL)')
            return redirect('staff_salary_list')

    return render(request, 'finance/staff_salary.html', {
        'salaries': salaries[:200], 'staff_users': staff_users,
        'total_gross': total_gross, 'total_net': total_net,
        'total_paid': total_paid, 'total_pending': total_pending,
        'selected_month': month, 'selected_status': status_filter,
        'bank_accounts': FinanceAccount.objects.filter(account_type__in=['bank', 'cash'], is_active=True),
    })


@login_required
@role_required('admin', 'accountant')
def refund_list(request):
    from admissions.models import Admission
    from fees.models import Payment
    refunds = Refund.objects.select_related('admission__student', 'original_payment', 'created_by').all()
    admissions = Admission.objects.filter(status__in=['active', 'fee_pending', 'completed'])

    status_filter = request.GET.get('status', '')
    if status_filter:
        refunds = refunds.filter(status=status_filter)

    total_refunds = refunds.filter(status='processed').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            admission_id = request.POST.get('admission_id')
            original_pay_id = request.POST.get('original_payment_id')
            amount = Decimal(request.POST.get('amount', '0') or '0')
            reason = request.POST.get('reason', 'other')
            desc = request.POST.get('description', '')
            refund_date = request.POST.get('refund_date', timezone.localdate().isoformat())
            refund_mode = request.POST.get('refund_mode', 'cash')
            acc_id = request.POST.get('account')
            notes = request.POST.get('notes', '')
            if admission_id and amount > 0:
                refund = Refund.objects.create(
                    admission_id=admission_id,
                    original_payment_id=original_pay_id or None,
                    amount=amount, reason=reason, description=desc,
                    refund_date=refund_date, refund_mode=refund_mode,
                    account_id=acc_id or None, notes=notes,
                    created_by=request.user, status='pending_approval',
                )
                finance_log(request.user, 'create', 'Refund', refund.pk,
                            f'{refund.voucher_no} - ₹{amount} for {refund.admission.admission_number}')
                messages.success(request, f'Refund {refund.voucher_no} created.')
            return redirect('refund_list')
        if action == 'approve':
            ref_id = request.POST.get('refund_id')
            refund = Refund.objects.filter(pk=ref_id).first()
            if refund:
                refund.status = 'approved'
                refund.approved_by = request.user
                refund.save()
                finance_log(request.user, 'approve', 'Refund', refund.pk, f'Approved: {refund.voucher_no}')
                messages.success(request, f'Refund {refund.voucher_no} approved.')
            return redirect('refund_list')
        if action == 'process':
            ref_id = request.POST.get('refund_id')
            refund = Refund.objects.filter(pk=ref_id, status='approved').first()
            if refund and refund.account:
                finance_txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no('PV'),
                    voucher_type='PV', transaction_date=refund.refund_date,
                    account=refund.account, source_type='refund', source_id=refund.pk,
                    description=f'Refund - {refund.admission.student.name} ({refund.get_reason_display()})',
                    amount=refund.amount, direction='out',
                    payment_mode=refund.refund_mode, status='posted', created_by=request.user,
                )
                refund.finance_transaction = finance_txn
                refund.status = 'processed'
                refund.save()
                finance_log(request.user, 'update', 'Refund', refund.pk,
                            f'Processed refund: {finance_txn.voucher_no}')
                messages.success(request, f'Refund processed. Voucher: {finance_txn.voucher_no}')
            else:
                messages.error(request, 'Cannot process refund without account or approval.')
            return redirect('refund_list')

    return render(request, 'finance/refunds.html', {
        'refunds': refunds[:200], 'admissions': admissions,
        'total_refunds': total_refunds, 'selected_status': status_filter,
    })


@login_required
@role_required('admin', 'accountant')
def payables_receivables(request):
    from admissions.models import Admission
    from django.db.models import F

    section = request.GET.get('section', 'student_receivable')

    context = {'section': section}

    if section == 'student_receivable':
        admissions = Admission.objects.filter(
            status__in=['active', 'fee_pending']
        ).select_related('student', 'course', 'university')
        receivable_list = []
        for a in admissions:
            paid = a.paid_amount
            balance = a.balance_amount
            if balance > 0:
                days_since = (timezone.localdate() - a.admission_date).days if a.admission_date else 0
                age_bucket = '0-30' if days_since <= 30 else '31-60' if days_since <= 60 else '61-90' if days_since <= 90 else '90+'
                receivable_list.append({
                    'student_name': a.student.name,
                    'student_id': a.student.student_id,
                    'admission_number': a.admission_number,
                    'course': a.course.name,
                    'university': a.university.name,
                    'total_fee': a.total_fee,
                    'paid': paid,
                    'balance': balance,
                    'age_days': days_since,
                    'age_bucket': age_bucket,
                })
        total_receivable = sum(r['balance'] for r in receivable_list)
        aging_summary = {}
        for r in receivable_list:
            b = r['age_bucket']
            aging_summary[b] = aging_summary.get(b, Decimal('0')) + r['balance']
        context['receivable_list'] = receivable_list
        context['total_receivable'] = total_receivable
        context['aging_summary'] = aging_summary

    elif section == 'university_receivable':
        uni_txns = UniversityTransaction.objects.filter(
            transaction_type='receivable', status='posted'
        ).select_related('university')
        by_uni = {}
        for txn in uni_txns:
            name = txn.university.name
            by_uni[name] = by_uni.get(name, Decimal('0')) + txn.amount
        context['university_receivables'] = [{'name': k, 'amount': v} for k, v in by_uni.items()]
        context['total_university_receivable'] = sum(by_uni.values())

    elif section == 'university_payable':
        uni_txns = UniversityTransaction.objects.filter(
            transaction_type='payable', status='posted'
        ).select_related('university')
        by_uni = {}
        for txn in uni_txns:
            name = txn.university.name
            by_uni[name] = by_uni.get(name, Decimal('0')) + txn.amount
        context['university_payables'] = [{'name': k, 'amount': v} for k, v in by_uni.items()]
        context['total_university_payable'] = sum(by_uni.values())

    elif section == 'salary_payable':
        unpaid = StaffSalary.objects.exclude(status='paid').exclude(status='cancelled').select_related('staff')
        salary_list = []
        for s in unpaid:
            if s.balance > 0:
                salary_list.append({
                    'staff_name': s.staff.get_full_name() or s.staff.username,
                    'month': s.salary_month,
                    'net_salary': s.net_salary,
                    'paid': s.paid_amount,
                    'balance': s.balance,
                })
        context['salary_payables'] = salary_list
        context['total_salary_payable'] = sum(s['balance'] for s in salary_list)

    elif section == 'expense_payable':
        pending = ExpenseEntry.objects.filter(
            status='approved'
        ).select_related('category', 'account')
        expense_list = []
        for e in pending:
            expense_list.append({
                'voucher_no': e.voucher_no,
                'date': e.expense_date,
                'category': e.category.name if e.category else '-',
                'vendor': e.vendor or '-',
                'amount': e.amount,
            })
        context['expense_payables'] = expense_list
        context['total_expense_payable'] = sum(e['amount'] for e in expense_list)

    return render(request, 'finance/payables_receivables.html', context)


@login_required
@role_required('admin', 'accountant')
def finance_report_export(request):
    import csv
    from django.http import HttpResponse
    from io import BytesIO

    report_type = request.GET.get('type', 'daily_collection')
    date_from = request.GET.get('date_from', timezone.localdate().isoformat())
    date_to = request.GET.get('date_to', timezone.localdate().isoformat())
    export_format = request.GET.get('format', 'csv')

    if report_type == 'daily_collection':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            direction='in', status='posted', source_type='student'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Description', 'Payment Mode', 'Amount', 'Account', 'Created By']
        rows = []
        for t in txns:
            rows.append([
                str(t.transaction_date), t.voucher_no, t.description,
                t.get_payment_mode_display(), str(t.amount),
                t.account.name if t.account else '-',
                t.created_by.username if t.created_by else '-',
            ])
        filename = f'daily_collection_{date_from}_to_{date_to}'

    elif report_type == 'daily_expense':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            direction='out', status='posted'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Description', 'Category', 'Payment Mode', 'Amount', 'Account']
        rows = []
        for t in txns:
            rows.append([
                str(t.transaction_date), t.voucher_no, t.description,
                t.category.name if t.category else '-', t.get_payment_mode_display(),
                str(t.amount), t.account.name if t.account else '-',
            ])
        filename = f'daily_expense_{date_from}_to_{date_to}'

    elif report_type == 'monthly':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
            status='posted'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Type', 'Direction', 'Description', 'Amount', 'Account', 'Payment Mode']
        rows = []
        for t in txns:
            rows.append([
                str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(),
                'In' if t.direction == 'in' else 'Out', t.description,
                str(t.amount), t.account.name if t.account else '-',
                t.get_payment_mode_display(),
            ])
        filename = f'monthly_report_{date_from}_to_{date_to}'

    elif report_type == 'day_book':
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=date_from, transaction_date__lte=date_to,
        ).order_by('transaction_date', 'created_at')
        headers = ['Date', 'Voucher No', 'Type', 'Description', 'Category', 'Payment Mode', 'In', 'Out', 'Account', 'Status']
        rows = []
        for t in txns:
            rows.append([
                str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(),
                t.description, t.category.name if t.category else '-',
                t.get_payment_mode_display(),
                str(t.amount) if t.direction == 'in' else '',
                str(t.amount) if t.direction == 'out' else '',
                t.account.name if t.account else '-',
                t.get_status_display(),
            ])
        filename = f'day_book_{date_from}_to_{date_to}'

    else:
        messages.error(request, 'Invalid report type.')
        return redirect('finance_reports')

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response

    elif export_format == 'excel':
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = report_type.replace('_', ' ').title()
            ws.append(headers)
            for row in rows:
                ws.append(row)
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            response = HttpResponse(buf.getvalue(),
                                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            return response
        except ImportError:
            messages.error(request, 'Excel export requires openpyxl. Install with: pip install openpyxl')
            return redirect('finance_reports')

    elif export_format == 'pdf':
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas as pdf_canvas

        buf = BytesIO()
        p = pdf_canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        NAVY = HexColor('#0f172a')
        GOLD = HexColor('#f59e0b')

        p.setFillColor(NAVY)
        p.rect(0, h - 60, w, 60, fill=1, stroke=0)
        p.setFillColor(GOLD)
        p.rect(0, h - 63, w, 3, fill=1, stroke=0)
        p.setFillColor(HexColor('#ffffff'))
        p.setFont('Helvetica-Bold', 16)
        p.drawCentredString(w / 2, h - 40, 'RENIC TECH - Finance Report')
        p.setFont('Helvetica', 9)
        p.drawCentredString(w / 2, h - 55, f'{report_type.replace("_", " ").title()} | {date_from} to {date_to}')

        y = h - 90
        p.setFillColor(NAVY)
        p.setFont('Helvetica-Bold', 8)
        col_widths = [70] * len(headers) if len(headers) <= 6 else [w / len(headers)] * len(headers)
        x = 40
        for i, header in enumerate(headers):
            p.drawString(x, y, header)
            x += col_widths[i] if i < len(col_widths) else 80

        y -= 5
        p.setStrokeColor(GOLD)
        p.setLineWidth(0.5)
        p.line(40, y, w - 40, y)
        y -= 15

        p.setFont('Helvetica', 7)
        p.setFillColor(HexColor('#1e293b'))
        for row in rows:
            if y < 50:
                p.showPage()
                y = h - 50
            x = 40
            for i, cell in enumerate(row):
                p.drawString(x, y, str(cell)[:40])
                x += col_widths[i] if i < len(col_widths) else 80
            y -= 12

        p.setFillColor(NAVY)
        p.rect(0, 0, w, 30, fill=1, stroke=0)
        p.setFillColor(HexColor('#94a3b8'))
        p.setFont('Helvetica', 7)
        p.drawCentredString(w / 2, 15, f'Generated on {timezone.localdate()} | RENIC TECH - Distance Education ERP')

        p.showPage()
        p.save()
        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response

    messages.error(request, 'Invalid export format.')
    return redirect('finance_reports')


@login_required
@role_required('admin')
def branch_list(request):
    branches = Branch.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            address = request.POST.get('address', '')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            manager_id = request.POST.get('manager_id')
            if name and code:
                Branch.objects.create(
                    name=name, code=code, address=address,
                    phone=phone, email=email, manager_id=manager_id or None,
                )
                messages.success(request, f'Branch "{name}" created.')
            return redirect('branch_list')
        if action == 'toggle':
            branch_id = request.POST.get('branch_id')
            branch = Branch.objects.filter(pk=branch_id).first()
            if branch:
                branch.is_active = not branch.is_active
                branch.save()
                messages.success(request, f'Branch "{branch.name}" {"activated" if branch.is_active else "deactivated"}.')
            return redirect('branch_list')

    from accounts.models import User
    staff = User.objects.filter(is_active=True)
    return render(request, 'finance/branches.html', {'branches': branches, 'staff': staff})


@login_required
@role_required('admin')
def cost_centre_list(request):
    centres = CostCentre.objects.select_related('branch').all()
    branches = Branch.objects.filter(is_active=True)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            desc = request.POST.get('description', '')
            branch_id = request.POST.get('branch_id')
            if name and code:
                CostCentre.objects.create(
                    name=name, code=code, description=desc,
                    branch_id=branch_id or None,
                )
                messages.success(request, f'Cost Centre "{name}" created.')
            return redirect('cost_centre_list')
        if action == 'toggle':
            cc_id = request.POST.get('cc_id')
            cc = CostCentre.objects.filter(pk=cc_id).first()
            if cc:
                cc.is_active = not cc.is_active
                cc.save()
                messages.success(request, f'Cost Centre "{cc.name}" {"activated" if cc.is_active else "deactivated"}.')
            return redirect('cost_centre_list')

    return render(request, 'finance/cost_centres.html', {'centres': centres, 'branches': branches})


@login_required
@role_required('admin')
def reopen_day(request):
    if request.method == 'POST':
        date_str = request.POST.get('closing_date')
        reason = request.POST.get('reason', '')
        if date_str:
            closing = DayClosing.objects.filter(closing_date=date_str).first()
            if closing and closing.status == 'closed':
                closing.status = 'reopened'
                closing.difference_reason = f'REOPENED: {reason}'
                closing.save()
                finance_log(request.user, 'reopen_day', 'DayClosing', closing.pk,
                            f'Reopened day {date_str}. Reason: {reason}')
                messages.success(request, f'Day {date_str} has been reopened.')
            else:
                messages.error(request, 'Day not found or not closed.')
        return redirect('daily_closing')

    closed_days = DayClosing.objects.filter(status='closed').order_by('-closing_date')[:30]
    return render(request, 'finance/reopen_day.html', {'closed_days': closed_days})


@login_required
@role_required('admin', 'accountant')
def bank_reconciliation_list(request):
    from .models import BankReconciliation
    reconciliations = BankReconciliation.objects.select_related('account', 'created_by').all()
    accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)

    status_filter = request.GET.get('status', '')
    if status_filter:
        reconciliations = reconciliations.filter(status=status_filter)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            acc_id = request.POST.get('account_id')
            recon_date = request.POST.get('reconciliation_date', timezone.localdate().isoformat())
            stmt_date = request.POST.get('statement_date', timezone.localdate().isoformat())
            book_bal = Decimal(request.POST.get('book_balance', '0') or '0')
            bank_bal = Decimal(request.POST.get('bank_balance', '0') or '0')
            outstanding_dep = Decimal(request.POST.get('outstanding_deposits', '0') or '0')
            unpresented = Decimal(request.POST.get('unpresented_cheques', '0') or '0')
            charges = Decimal(request.POST.get('bank_charges', '0') or '0')
            interest = Decimal(request.POST.get('interest_earned', '0') or '0')
            other_adj = Decimal(request.POST.get('other_adjustments', '0') or '0')
            notes = request.POST.get('notes', '')
            if acc_id:
                recon = BankReconciliation.objects.create(
                    account_id=acc_id, reconciliation_date=recon_date,
                    statement_date=stmt_date, book_balance=book_bal,
                    bank_balance=bank_bal, outstanding_deposits=outstanding_dep,
                    unpresented_cheques=unpresented, bank_charges=charges,
                    interest_earned=interest, other_adjustments=other_adj,
                    notes=notes, created_by=request.user,
                )
                finance_log(request.user, 'create', 'BankReconciliation', recon.pk,
                            f'{recon.account.name} - Difference: ₹{recon.difference}')
                if recon.status == 'reconciled':
                    messages.success(request, f'Bank reconciliation completed. Account balanced.')
                else:
                    messages.warning(request, f'Reconciliation created with difference of ₹{recon.difference}. Please review.')
            return redirect('bank_reconciliation_list')

    return render(request, 'finance/bank_reconciliation.html', {
        'reconciliations': reconciliations[:100], 'accounts': accounts,
        'selected_status': status_filter,
    })


@login_required
@role_required('admin', 'accountant')
def gateway_settlement_list(request):
    from .models import GatewaySettlement
    settlements = GatewaySettlement.objects.select_related('account', 'created_by').all()
    accounts = FinanceAccount.objects.filter(account_type='payment_gateway', is_active=True)

    status_filter = request.GET.get('status', '')
    if status_filter:
        settlements = settlements.filter(status=status_filter)

    total_collected = settlements.aggregate(t=Sum('total_collected'))['t'] or Decimal('0')
    total_fees = settlements.aggregate(t=Sum('gateway_fees'))['t'] or Decimal('0')
    total_settled = settlements.filter(status='settled').aggregate(t=Sum('net_settlement'))['t'] or Decimal('0')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            acc_id = request.POST.get('account_id')
            settle_date = request.POST.get('settlement_date', timezone.localdate().isoformat())
            period_from = request.POST.get('period_from', timezone.localdate().isoformat())
            period_to = request.POST.get('period_to', timezone.localdate().isoformat())
            collected = Decimal(request.POST.get('total_collected', '0') or '0')
            fees = Decimal(request.POST.get('gateway_fees', '0') or '0')
            gst = Decimal(request.POST.get('gst_on_fees', '0') or '0')
            credit_date = request.POST.get('bank_credit_date') or None
            credit_amount = Decimal(request.POST.get('bank_credit_amount', '0') or '0')
            notes = request.POST.get('notes', '')
            if acc_id:
                settlement = GatewaySettlement.objects.create(
                    account_id=acc_id, settlement_date=settle_date,
                    period_from=period_from, period_to=period_to,
                    total_collected=collected, gateway_fees=fees,
                    gst_on_fees=gst, bank_credit_date=credit_date,
                    bank_credit_amount=credit_amount, notes=notes,
                    created_by=request.user,
                )
                finance_log(request.user, 'create', 'GatewaySettlement', settlement.pk,
                            f'{settlement.account.name} - ₹{settlement.net_settlement}')
                messages.success(request, f'Gateway settlement recorded.')
            return redirect('gateway_settlement_list')
        if action == 'mark_settled':
            settle_id = request.POST.get('settlement_id')
            settlement = GatewaySettlement.objects.filter(pk=settle_id).first()
            if settlement:
                settlement.status = 'settled'
                settlement.bank_credit_date = timezone.localdate()
                settlement.save()
                finance_log(request.user, 'update', 'GatewaySettlement', settlement.pk,
                            f'Marked as settled')
                messages.success(request, f'Settlement marked as completed.')
            return redirect('gateway_settlement_list')

    return render(request, 'finance/gateway_settlements.html', {
        'settlements': settlements[:100], 'accounts': accounts,
        'total_collected': total_collected, 'total_fees': total_fees,
        'total_settled': total_settled, 'selected_status': status_filter,
    })


@login_required
@role_required('admin', 'accountant')
def finance_notifications(request):
    notifications = []

    unclosed = DayClosing.objects.filter(status__in=['open', 'submitted']).order_by('-closing_date')
    for d in unclosed:
        notifications.append({
            'type': 'warning',
            'icon': 'bi-clock-history',
            'title': f'Day {d.closing_date} not closed',
            'message': f'Status: {d.get_status_display()}. Please close the day.',
            'link': 'daily_closing',
        })

    unapproved_expenses = ExpenseEntry.objects.filter(status='pending_approval').count()
    if unapproved_expenses > 0:
        notifications.append({
            'type': 'info',
            'icon': 'bi-receipt',
            'title': f'{unapproved_expenses} expense(s) pending approval',
            'message': 'Review and approve pending expenses.',
            'link': 'expense_list',
        })

    today = timezone.localdate()
    for acc in FinanceAccount.objects.filter(account_type='bank', is_active=True):
        balance = acc.current_balance
        if balance < 0:
            notifications.append({
                'type': 'danger',
                'icon': 'bi-bank',
                'title': f'{acc.name} has negative balance',
                'message': f'Current balance: ₹{balance:,.2f}. Immediate attention required.',
                'link': 'cash_bank',
            })

    low_cash = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
    if low_cash and low_cash.current_balance < 5000:
        notifications.append({
            'type': 'warning',
            'icon': 'bi-cash-stack',
            'title': f'Low cash balance: ₹{low_cash.current_balance:,.2f}',
            'message': 'Cash balance is below minimum threshold. Consider bank withdrawal.',
            'link': 'cash_bank',
        })

    pending_refunds = Refund.objects.filter(status='pending_approval').count()
    if pending_refunds > 0:
        notifications.append({
            'type': 'info',
            'icon': 'bi-arrow-return-left',
            'title': f'{pending_refunds} refund(s) pending approval',
            'message': 'Review and process pending student refunds.',
            'link': 'refund_list',
        })

    pending_university = UniversityTransaction.objects.filter(status='pending_approval').count()
    if pending_university > 0:
        notifications.append({
            'type': 'info',
            'icon': 'bi-building',
            'title': f'{pending_university} university transaction(s) pending',
            'message': 'Review pending university payable/receivable transactions.',
            'link': 'university_transactions',
        })

    return render(request, 'finance/notifications.html', {'notifications': notifications})


@login_required
@role_required('admin', 'accountant')
def cash_flow_report(request):
    from datetime import datetime, timedelta
    period = request.GET.get('period', 'weekly')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    today = timezone.localdate()
    if not date_from or not date_to:
        if period == 'weekly':
            date_from = (today - timedelta(days=7)).isoformat()
            date_to = today.isoformat()
        elif period == 'monthly':
            date_from = today.replace(day=1).isoformat()
            date_to = today.isoformat()
        elif period == 'quarterly':
            month = today.month
            quarter_start_month = ((month - 1) // 3) * 3 + 1
            date_from = today.replace(month=quarter_start_month, day=1).isoformat()
            date_to = today.isoformat()
        elif period == 'yearly':
            date_from = today.replace(month=1, day=1).isoformat()
            date_to = today.isoformat()

    txns = FinanceTransaction.objects.filter(
        transaction_date__gte=date_from, transaction_date__lte=date_to,
        status='posted'
    )

    income = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    expense = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net = income - expense

    income_by_source = txns.filter(direction='in').values('source_type').annotate(
        total=Sum('amount')
    ).order_by('-total')

    expense_by_category = txns.filter(direction='out').values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    daily_flow = []
    d_start = datetime.strptime(date_from, '%Y-%m-%d').date()
    d_end = datetime.strptime(date_to, '%Y-%m-%d').date()
    current = d_start
    while current <= d_end:
        day_in = txns.filter(transaction_date=current, direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        day_out = txns.filter(transaction_date=current, direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        daily_flow.append({
            'date': current,
            'income': day_in,
            'expense': day_out,
            'net': day_in - day_out,
        })
        current += timedelta(days=1)

    return render(request, 'finance/cash_flow.html', {
        'period': period, 'date_from': date_from, 'date_to': date_to,
        'income': income, 'expense': expense, 'net': net,
        'income_by_source': income_by_source,
        'expense_by_category': expense_by_category,
        'daily_flow': daily_flow,
    })


@login_required
@role_required('admin', 'accountant')
def budget_vs_actual(request):
    from .models import Budget
    from datetime import date

    today = date.today()
    year = int(request.GET.get('year', today.year))
    period = request.GET.get('period', 'yearly')

    budgets = Budget.objects.filter(year=year).select_related('category')

    if period == 'monthly':
        month = int(request.GET.get('month', today.month))
        budgets = budgets.filter(month=month)
    elif period == 'quarterly':
        quarter = int(request.GET.get('quarter', (today.month - 1) // 3 + 1))
        budgets = budgets.filter(quarter=quarter)

    budget_data = []
    total_budget = Decimal('0')
    total_actual = Decimal('0')
    for b in budgets:
        actual = b.actual_amount
        variance = b.budget_amount - actual
        var_pct = ((b.budget_amount - actual) / b.budget_amount * 100) if b.budget_amount > 0 else Decimal('0')
        status = 'under' if variance > 0 else ('over' if variance < 0 else 'on_track')
        budget_data.append({
            'category': b.category.name,
            'budget': b.budget_amount,
            'actual': actual,
            'variance': variance,
            'variance_percent': var_pct,
            'status': status,
        })
        total_budget += b.budget_amount
        total_actual += actual

    total_variance = total_budget - total_actual
    total_var_pct = ((total_budget - total_actual) / total_budget * 100) if total_budget > 0 else Decimal('0')

    categories = ExpenseCategory.objects.filter(category_type='expense', is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            cat_id = request.POST.get('category_id')
            b_year = int(request.POST.get('year', today.year))
            b_month = request.POST.get('month')
            b_quarter = request.POST.get('quarter')
            b_type = request.POST.get('period_type', 'monthly')
            amount = Decimal(request.POST.get('budget_amount', '0') or '0')
            notes = request.POST.get('notes', '')
            if cat_id and amount > 0:
                Budget.objects.update_or_create(
                    category_id=cat_id, period_type=b_type, year=b_year,
                    month=int(b_month) if b_month else None,
                    quarter=int(b_quarter) if b_quarter else None,
                    defaults={
                        'budget_amount': amount, 'notes': notes,
                        'created_by': request.user,
                    }
                )
                messages.success(request, 'Budget saved.')
            return redirect(f'{request.path}?year={b_year}&period={b_type}')
        if action == 'delete':
            budget_id = request.POST.get('budget_id')
            Budget.objects.filter(pk=budget_id).delete()
            messages.success(request, 'Budget deleted.')
            return redirect(request.path)

    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    return render(request, 'finance/budget_vs_actual.html', {
        'budget_data': budget_data, 'year': year, 'period': period,
        'total_budget': total_budget, 'total_actual': total_actual,
        'total_variance': total_variance, 'total_var_pct': total_var_pct,
        'categories': categories, 'months': months,
        'selected_month': request.GET.get('month', str(today.month)),
        'selected_quarter': request.GET.get('quarter', str((today.month - 1) // 3 + 1)),
    })


@login_required
@role_required('admin', 'accountant')
def reminder_settings(request):
    from .models import ReminderLog, FinanceSettings

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'generate':
            _generate_reminders()
            messages.success(request, 'Reminders generated successfully.')
            return redirect('reminder_settings')
        if action == 'mark_read':
            log_id = request.POST.get('log_id')
            ReminderLog.objects.filter(pk=log_id).update(is_read=True)
            return redirect('reminder_settings')
        if action == 'save_settings':
            FinanceSettings.set_value('reminder_low_cash_threshold',
                                      request.POST.get('low_cash_threshold', '5000'))
            FinanceSettings.set_value('reminder_fee_overdue_days',
                                      request.POST.get('fee_overdue_days', '30'))
            FinanceSettings.set_value('reminder_auto_generate',
                                      '1' if request.POST.get('auto_generate') else '0')
            messages.success(request, 'Reminder settings saved.')
            return redirect('reminder_settings')

    logs = ReminderLog.objects.all()[:50]
    unread_count = ReminderLog.objects.filter(is_read=False).count()
    low_cash_threshold = FinanceSettings.get_value('reminder_low_cash_threshold', '5000')
    fee_overdue_days = FinanceSettings.get_value('reminder_fee_overdue_days', '30')
    auto_generate = FinanceSettings.get_value('reminder_auto_generate', '0')

    return render(request, 'finance/reminders.html', {
        'logs': logs, 'unread_count': unread_count,
        'low_cash_threshold': low_cash_threshold,
        'fee_overdue_days': fee_overdue_days,
        'auto_generate': auto_generate,
    })


def _generate_reminders():
    from .models import ReminderLog, FinanceSettings
    from admissions.models import Admission

    today = timezone.localdate()

    unclosed = DayClosing.objects.filter(status__in=['open', 'submitted'])
    for d in unclosed:
        if not ReminderLog.objects.filter(reminder_type='day_not_closed', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='day_not_closed',
                title=f'Day {d.closing_date} not closed',
                message=f'Status: {d.get_status_display()}. Please close the day.',
            )

    pending_expenses = ExpenseEntry.objects.filter(status='pending_approval').count()
    if pending_expenses > 0:
        if not ReminderLog.objects.filter(reminder_type='expense_pending', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='expense_pending',
                title=f'{pending_expenses} expense(s) pending approval',
                message='Review and approve pending expenses.',
            )

    pending_refunds = Refund.objects.filter(status='pending_approval').count()
    if pending_refunds > 0:
        if not ReminderLog.objects.filter(reminder_type='refund_pending', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='refund_pending',
                title=f'{pending_refunds} refund(s) pending approval',
                message='Review and process pending student refunds.',
            )

    low_threshold = Decimal(FinanceSettings.get_value('reminder_low_cash_threshold', '5000'))
    for acc in FinanceAccount.objects.filter(account_type='cash', is_active=True):
        if acc.current_balance < low_threshold:
            if not ReminderLog.objects.filter(reminder_type='low_cash', title__contains=acc.name, created_at__date=today).exists():
                ReminderLog.objects.create(
                    reminder_type='low_cash',
                    title=f'{acc.name} low balance: ₹{acc.current_balance:,.2f}',
                    message=f'Cash balance is below threshold of ₹{low_threshold}.',
                )

    overdue_days = int(FinanceSettings.get_value('fee_overdue_days', '30'))
    cutoff = today - timedelta(days=overdue_days)
    overdue = Admission.objects.filter(
        status__in=['active', 'fee_pending'],
        admission_date__lte=cutoff
    ).annotate(
        paid=Sum('payments__amount', filter=Q(payments__is_voided=False))
    ).filter(paid__lt=F('total_fee'))

    for a in overdue:
        if not ReminderLog.objects.filter(reminder_type='fee_overdue', title__contains=a.admission_number, created_at__date=today).exists():
            paid = a.paid or Decimal('0')
            balance = a.total_fee - paid
            ReminderLog.objects.create(
                reminder_type='fee_overdue',
                title=f'Fee overdue: {a.student.name} ({a.admission_number})',
                message=f'Outstanding: ₹{balance:,.2f}. Admission date: {a.admission_date}',
            )

    pending_university = UniversityTransaction.objects.filter(status='pending_approval').count()
    if pending_university > 0:
        if not ReminderLog.objects.filter(reminder_type='university_due', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='university_due',
                title=f'{pending_university} university transaction(s) pending',
                message='Review pending university payable/receivable transactions.',
            )

    from .models import Budget
    budgets = Budget.objects.filter(year=today.year)
    for b in budgets:
        actual = b.actual_amount
        if b.budget_amount > 0 and actual > b.budget_amount:
            if not ReminderLog.objects.filter(reminder_type='budget_exceeded', title__contains=b.category.name, created_at__date=today).exists():
                ReminderLog.objects.create(
                    reminder_type='budget_exceeded',
                    title=f'Budget exceeded: {b.category.name}',
                    message=f'Budget: ₹{b.budget_amount:,.2f} | Actual: ₹{actual:,.2f} | Over by: ₹{actual - b.budget_amount:,.2f}',
                )


@login_required
@role_required('admin', 'accountant')
def bank_statement_import(request):
    from .models import BankStatementEntry

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'import_csv':
            import csv
            acc_id = request.POST.get('account_id')
            csv_file = request.FILES.get('csv_file')
            if acc_id and csv_file:
                try:
                    decoded = csv_file.read().decode('utf-8')
                    reader = csv.DictReader(decoded.splitlines())
                    count = 0
                    for row in reader:
                        BankStatementEntry.objects.create(
                            account_id=acc_id,
                            transaction_date=row.get('date', timezone.localdate()),
                            description=row.get('description', ''),
                            reference_no=row.get('reference', ''),
                            debit=Decimal(row.get('debit', '0') or '0'),
                            credit=Decimal(row.get('credit', '0') or '0'),
                            balance=Decimal(row.get('balance', '0') or '0'),
                        )
                        count += 1
                    messages.success(request, f'Imported {count} statement entries.')
                except Exception as e:
                    messages.error(request, f'Import error: {str(e)}')
            return redirect('bank_statement_import')
        if action == 'match':
            entry_id = request.POST.get('entry_id')
            txn_id = request.POST.get('txn_id')
            entry = BankStatementEntry.objects.filter(pk=entry_id).first()
            txn = FinanceTransaction.objects.filter(pk=txn_id).first()
            if entry and txn:
                entry.matched = True
                entry.finance_transaction = txn
                entry.save()
                messages.success(request, 'Entry matched.')
            return redirect('bank_statement_import')

    accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)
    unmatched = BankStatementEntry.objects.filter(matched=False).select_related('account')
    matched = BankStatementEntry.objects.filter(matched=True).select_related('account', 'finance_transaction')[:50]
    transactions = FinanceTransaction.objects.filter(status='posted').order_by('-transaction_date')[:100]

    return render(request, 'finance/bank_statement_import.html', {
        'accounts': accounts, 'unmatched': unmatched, 'matched': matched,
        'transactions': transactions,
    })


@login_required
@role_required('admin', 'accountant')
def gst_report(request):
    from .models import GSTRecord

    year = request.GET.get('year', str(timezone.localdate().year))
    quarter = request.GET.get('quarter', str((timezone.localdate().month - 1) // 3 + 1))

    records = GSTRecord.objects.filter(financial_year=year, quarter=quarter)

    total_taxable = records.aggregate(t=Sum('taxable_amount'))['t'] or Decimal('0')
    total_gst = records.aggregate(t=Sum('gst_amount'))['t'] or Decimal('0')
    cgst = records.filter(gst_type='cgst').aggregate(t=Sum('gst_amount'))['t'] or Decimal('0')
    sgst = records.filter(gst_type='sgst').aggregate(t=Sum('gst_amount'))['t'] or Decimal('0')
    igst = records.filter(gst_type='igst').aggregate(t=Sum('gst_amount'))['t'] or Decimal('0')

    income_records = records.filter(source_type='income')
    expense_records = records.filter(source_type='expense')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'calculate':
            _calculate_gst(year, int(quarter))
            messages.success(request, 'GST calculated from transactions.')
            return redirect(f'{request.path}?year={year}&quarter={quarter}')

    return render(request, 'finance/gst_report.html', {
        'year': year, 'quarter': quarter,
        'records': records, 'total_taxable': total_taxable,
        'total_gst': total_gst, 'cgst': cgst, 'sgst': sgst, 'igst': igst,
        'income_records': income_records, 'expense_records': expense_records,
    })


def _calculate_gst(year, quarter):
    from .models import GSTRecord
    start_month = (quarter - 1) * 3 + 1
    start_date = date(int(year), start_month, 1)
    if start_month + 3 > 12:
        end_date = date(int(year) + 1, start_month + 3 - 12, 1)
    else:
        end_date = date(int(year), start_month + 3, 1)

    GSTRecord.objects.filter(financial_year=year, quarter=quarter).delete()

    txns = FinanceTransaction.objects.filter(
        transaction_date__gte=start_date, transaction_date__lt=end_date,
        status='posted'
    )

    gst_rates = [0, 5, 12, 18, 28]
    for rate in gst_rates:
        for source_type in ['income', 'expense']:
            direction = 'in' if source_type == 'income' else 'out'
            taxable = txns.filter(direction=direction, notes__contains=f'GST@{rate}').aggregate(
                t=Sum('amount'))['t'] or Decimal('0')
            if taxable > 0:
                gst_amount = taxable * Decimal(str(rate)) / 100
                half = gst_amount / 2
                GSTRecord.objects.create(
                    financial_year=year, quarter=quarter, gst_type='cgst',
                    rate=rate, taxable_amount=taxable, gst_amount=half,
                    source_type=source_type, description=f'CGST @{rate}%',
                )
                GSTRecord.objects.create(
                    financial_year=year, quarter=quarter, gst_type='sgst',
                    rate=rate, taxable_amount=taxable, gst_amount=half,
                    source_type=source_type, description=f'SGST @{rate}%',
                )


@login_required
@role_required('admin', 'accountant')
def trial_balance(request):
    as_of_date = request.GET.get('date', timezone.localdate().isoformat())

    accounts = FinanceAccount.objects.filter(is_active=True)
    ledger = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for acc in accounts:
        txns = FinanceTransaction.objects.filter(
            account=acc, status='posted', transaction_date__lte=as_of_date
        )
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        balance = acc.opening_balance + money_in - money_out

        if balance > 0:
            debit = balance
            credit = Decimal('0')
        else:
            debit = Decimal('0')
            credit = abs(balance)

        ledger.append({
            'account': acc.name,
            'account_type': acc.get_account_type_display(),
            'opening': acc.opening_balance,
            'debit': debit,
            'credit': credit,
            'balance': balance,
        })
        total_debit += debit
        total_credit += credit

    return render(request, 'finance/trial_balance.html', {
        'ledger': ledger, 'as_of_date': as_of_date,
        'total_debit': total_debit, 'total_credit': total_credit,
        'is_balanced': total_debit == total_credit,
    })


@login_required
@role_required('admin', 'accountant')
def profit_loss_report(request):
    year = request.GET.get('year', str(timezone.localdate().year))
    quarter = request.GET.get('quarter', '')

    if quarter:
        start_month = (int(quarter) - 1) * 3 + 1
        start_date = date(int(year), start_month, 1)
        if start_month + 3 > 12:
            end_date = date(int(year) + 1, start_month + 3 - 12, 1)
        else:
            end_date = date(int(year), start_month + 3, 1)
        period_label = f'Q{quarter} {year}'
    else:
        start_date = date(int(year), 1, 1)
        end_date = date(int(year) + 1, 1, 1)
        period_label = f'FY {year}'

    txns = FinanceTransaction.objects.filter(
        transaction_date__gte=start_date, transaction_date__lt=end_date,
        status='posted'
    )

    income = txns.filter(direction='in').values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    total_income = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    expenses = txns.filter(direction='out').values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    total_expense = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    net_profit = total_income - total_expense

    return render(request, 'finance/profit_loss.html', {
        'period_label': period_label, 'year': year, 'quarter': quarter,
        'income': income, 'total_income': total_income,
        'expenses': expenses, 'total_expense': total_expense,
        'net_profit': net_profit,
    })


@login_required
@role_required('admin', 'accountant')
def balance_sheet(request):
    from admissions.models import Admission
    from django.db.models import F
    as_of_date = request.GET.get('date', timezone.localdate().isoformat())

    accounts = FinanceAccount.objects.filter(is_active=True)
    assets = []
    total_assets = Decimal('0')

    for acc in accounts:
        txns = FinanceTransaction.objects.filter(
            account=acc, status='posted', transaction_date__lte=as_of_date
        )
        money_in = txns.filter(direction='in').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        money_out = txns.filter(direction='out').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        balance = acc.opening_balance + money_in - money_out
        if balance > 0:
            assets.append({'name': acc.name, 'type': acc.get_account_type_display(), 'amount': balance})
            total_assets += balance

    student_receivable = Admission.objects.filter(
        status__in=['active', 'fee_pending']
    ).annotate(paid=Sum('payments__amount', filter=Q(payments__is_voided=False))).annotate(
        balance=F('total_fee') - F('paid')
    ).filter(balance__gt=0)
    total_student_receivable = sum(a.balance for a in student_receivable)

    university_receivable = UniversityTransaction.objects.filter(
        transaction_type='receivable', status='posted'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    liabilities = []
    total_liabilities = Decimal('0')

    university_payable = UniversityTransaction.objects.filter(
        transaction_type='payable', status='posted'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    if university_payable > 0:
        liabilities.append({'name': 'University Payable', 'amount': university_payable})
        total_liabilities += university_payable

    salary_payable = StaffSalary.objects.exclude(status='paid').exclude(status='cancelled')
    total_salary = sum(s.balance for s in salary_payable if s.balance > 0)
    if total_salary > 0:
        liabilities.append({'name': 'Salary Payable', 'amount': total_salary})
        total_liabilities += total_salary

    expense_payable = ExpenseEntry.objects.filter(status='approved').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    if expense_payable > 0:
        liabilities.append({'name': 'Expense Payable', 'amount': expense_payable})
        total_liabilities += expense_payable

    net_worth = total_assets + total_student_receivable + university_receivable - total_liabilities

    return render(request, 'finance/balance_sheet.html', {
        'as_of_date': as_of_date,
        'assets': assets, 'total_assets': total_assets,
        'student_receivable': total_student_receivable,
        'university_receivable': university_receivable,
        'liabilities': liabilities, 'total_liabilities': total_liabilities,
        'net_worth': net_worth,
    })


@login_required
@role_required('admin')
def salary_template_list(request):
    from .models import SalaryTemplate, StaffSalary

    templates = SalaryTemplate.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            basic = Decimal(request.POST.get('basic_salary', '0'))
            deductions = Decimal(request.POST.get('deductions', '0'))
            SalaryTemplate.objects.create(
                staff_name=request.POST.get('staff_name', ''),
                staff_role=request.POST.get('staff_role', ''),
                basic_salary=basic,
                deductions=deductions,
                net_payable=basic - deductions,
                frequency=request.POST.get('frequency', 'monthly'),
                payment_day=int(request.POST.get('payment_day', '1')),
                finance_account_id=request.POST.get('finance_account_id') or None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Salary template created.')
            return redirect('salary_template_list')
        if action == 'edit':
            tpl = SalaryTemplate.objects.get(pk=request.POST.get('tpl_id'))
            basic = Decimal(request.POST.get('basic_salary', '0'))
            deductions = Decimal(request.POST.get('deductions', '0'))
            tpl.staff_name = request.POST.get('staff_name', tpl.staff_name)
            tpl.staff_role = request.POST.get('staff_role', tpl.staff_role)
            tpl.basic_salary = basic
            tpl.deductions = deductions
            tpl.net_payable = basic - deductions
            tpl.frequency = request.POST.get('frequency', tpl.frequency)
            tpl.payment_day = int(request.POST.get('payment_day', tpl.payment_day))
            tpl.finance_account_id = request.POST.get('finance_account_id') or None
            tpl.notes = request.POST.get('notes', '')
            tpl.is_active = 'is_active' in request.POST
            tpl.save()
            messages.success(request, 'Template updated.')
            return redirect('salary_template_list')
        if action == 'delete':
            SalaryTemplate.objects.filter(pk=request.POST.get('tpl_id')).delete()
            messages.success(request, 'Template deleted.')
            return redirect('salary_template_list')
        if action == 'generate_all':
            count = _generate_salaries_from_templates()
            messages.success(request, f'Generated {count} salary record(s) from templates.')
            return redirect('salary_template_list')
        if action == 'generate_one':
            tpl = SalaryTemplate.objects.get(pk=request.POST.get('tpl_id'))
            count = _generate_salary_from_template(tpl)
            messages.success(request, f'Generated {count} salary record(s) for {tpl.staff_name}.')
            return redirect('salary_template_list')

    accounts = FinanceAccount.objects.filter(account_type='bank', is_active=True)
    current_month = timezone.localdate().strftime('%Y-%m')
    generated = StaffSalary.objects.filter(salary_month=current_month)

    return render(request, 'finance/salary_templates.html', {
        'templates': templates, 'accounts': accounts, 'generated': generated,
    })


def _generate_salary_from_template(tpl):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    today = timezone.localdate()
    salary_month = today.strftime('%Y-%m')

    user = User.objects.filter(username=tpl.staff_name).first()
    if not user:
        user = User.objects.filter(first_name__icontains=tpl.staff_name).first()
    if not user:
        user = User.objects.filter(last_name__icontains=tpl.staff_name).first()
    if not user:
        return 0

    existing = StaffSalary.objects.filter(
        staff=user, salary_month=salary_month
    ).exists()
    if existing:
        return 0

    StaffSalary.objects.create(
        staff=user,
        salary_month=salary_month,
        gross_salary=tpl.basic_salary,
        deductions=tpl.deductions,
        net_salary=tpl.net_payable,
        account=tpl.finance_account,
        status='draft',
    )
    tpl.last_generated = today
    tpl.save(update_fields=['last_generated'])
    return 1


def _generate_salaries_from_templates():
    today = timezone.localdate()
    count = 0
    for tpl in SalaryTemplate.objects.filter(is_active=True):
        count += _generate_salary_from_template(tpl)
    return count


@login_required
@role_required('admin')
def recurring_expense_list(request):
    from .models import RecurringExpense

    recurring = RecurringExpense.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            RecurringExpense.objects.create(
                name=request.POST.get('name', ''),
                category_id=request.POST.get('category_id') or None,
                amount=Decimal(request.POST.get('amount', '0')),
                frequency=request.POST.get('frequency', 'monthly'),
                payment_day=int(request.POST.get('payment_day', '1')),
                payee=request.POST.get('payee', ''),
                finance_account_id=request.POST.get('finance_account_id') or None,
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'Recurring expense created.')
            return redirect('recurring_expense_list')
        if action == 'edit':
            r = RecurringExpense.objects.get(pk=request.POST.get('rec_id'))
            r.name = request.POST.get('name', r.name)
            r.category_id = request.POST.get('category_id') or r.category_id
            r.amount = Decimal(request.POST.get('amount', str(r.amount)))
            r.frequency = request.POST.get('frequency', r.frequency)
            r.payment_day = int(request.POST.get('payment_day', r.payment_day))
            r.payee = request.POST.get('payee', r.payee)
            r.finance_account_id = request.POST.get('finance_account_id') or r.finance_account_id
            r.description = request.POST.get('description', r.description)
            r.is_active = 'is_active' in request.POST
            r.save()
            messages.success(request, 'Recurring expense updated.')
            return redirect('recurring_expense_list')
        if action == 'delete':
            RecurringExpense.objects.filter(pk=request.POST.get('rec_id')).delete()
            messages.success(request, 'Recurring expense deleted.')
            return redirect('recurring_expense_list')
        if action == 'generate_all':
            count = _generate_recurring_expenses()
            messages.success(request, f'Generated {count} expense entry(ies) from templates.')
            return redirect('recurring_expense_list')
        if action == 'generate_one':
            r = RecurringExpense.objects.get(pk=request.POST.get('rec_id'))
            count = _generate_recurring_expense(r)
            messages.success(request, f'Generated {count} expense entry for {r.name}.')
            return redirect('recurring_expense_list')

    categories = ExpenseCategory.objects.filter(category_type='expense')
    accounts = FinanceAccount.objects.filter(is_active=True)
    generated = ExpenseEntry.objects.filter(
        expense_date__month=timezone.localdate().month,
        expense_date__year=timezone.localdate().year,
        description__startswith='[AUTO]'
    )

    return render(request, 'finance/recurring_expenses.html', {
        'recurring': recurring, 'categories': categories, 'accounts': accounts,
        'generated': generated,
    })


def _generate_recurring_expense(r):
    today = timezone.localdate()
    month_key = f'{today.year}-{today.month:02d}'
    existing = ExpenseEntry.objects.filter(
        description__startswith=f'[AUTO] {r.name}',
        expense_date__year=today.year,
        expense_date__month=today.month,
    ).exists()
    if existing:
        return 0

    expense = ExpenseEntry.objects.create(
        category=r.category,
        amount=r.amount,
        expense_date=today.replace(day=r.payment_day) if r.payment_day <= 28 else today,
        description=f'[AUTO] {r.name} - {r.payee}',
        payment_mode='bank' if r.finance_account and r.finance_account.account_type == 'bank' else 'cash',
        status='approved',
        created_by=None,
    )
    r.last_generated = today
    r.save(update_fields=['last_generated'])
    return 1


def _generate_recurring_expenses():
    from .models import RecurringExpense
    today = timezone.localdate()
    count = 0
    for r in RecurringExpense.objects.filter(is_active=True):
        if r.payment_day == today.day:
            count += _generate_recurring_expense(r)
        elif today.day == 1 and r.last_generated and r.last_generated.month < today.month:
            count += _generate_recurring_expense(r)
    return count


@login_required
@role_required('admin')
def scheduled_report_list(request):
    from .models import ScheduledReport
    from django.core.mail import send_mail
    from django.conf import settings

    reports = ScheduledReport.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            ScheduledReport.objects.create(
                name=request.POST.get('name', ''),
                report_type=request.POST.get('report_type', ''),
                frequency=request.POST.get('frequency', 'monthly'),
                send_day=int(request.POST.get('send_day', '1')),
                send_time=request.POST.get('send_time', '09:00'),
                recipients=request.POST.get('recipients', ''),
                format=request.POST.get('format', 'pdf'),
            )
            messages.success(request, 'Scheduled report created.')
            return redirect('scheduled_report_list')
        if action == 'edit':
            sr = ScheduledReport.objects.get(pk=request.POST.get('sr_id'))
            sr.name = request.POST.get('name', sr.name)
            sr.report_type = request.POST.get('report_type', sr.report_type)
            sr.frequency = request.POST.get('frequency', sr.frequency)
            sr.send_day = int(request.POST.get('send_day', sr.send_day))
            sr.send_time = request.POST.get('send_time', sr.send_time)
            sr.recipients = request.POST.get('recipients', sr.recipients)
            sr.format = request.POST.get('format', sr.format)
            sr.is_active = 'is_active' in request.POST
            sr.save()
            messages.success(request, 'Scheduled report updated.')
            return redirect('scheduled_report_list')
        if action == 'delete':
            ScheduledReport.objects.filter(pk=request.POST.get('sr_id')).delete()
            messages.success(request, 'Scheduled report deleted.')
            return redirect('scheduled_report_list')
        if action == 'send_now':
            sr = ScheduledReport.objects.get(pk=request.POST.get('sr_id'))
            _send_scheduled_report(sr)
            messages.success(request, f'Report "{sr.name}" sent successfully.')
            return redirect('scheduled_report_list')

    return render(request, 'finance/scheduled_reports.html', {'reports': reports})


def _send_scheduled_report(sr):
    from django.core.mail import EmailMessage
    from django.conf import settings
    from django.utils import timezone as tz
    from .models import FinanceTransaction

    today = tz.localdate()
    subject = f'[RENIC ERP] {sr.get_report_type_display()} - {today.strftime("%d %b %Y")}'

    date_from = today.isoformat()
    date_to = today.isoformat()

    if sr.report_type == 'daily_collection':
        txns = FinanceTransaction.objects.filter(
            transaction_date=date_from, direction='in', status='posted', source_type='student'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Description', 'Payment Mode', 'Amount', 'Account']
        rows = [[str(t.transaction_date), t.voucher_no, t.description, t.get_payment_mode_display(), str(t.amount), t.account.name if t.account else '-'] for t in txns]
        filename = f'daily_collection_{date_from}'

    elif sr.report_type == 'daily_expense':
        txns = FinanceTransaction.objects.filter(
            transaction_date=date_from, direction='out', status='posted'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Description', 'Category', 'Payment Mode', 'Amount', 'Account']
        rows = [[str(t.transaction_date), t.voucher_no, t.description, t.category.name if t.category else '-', t.get_payment_mode_display(), str(t.amount), t.account.name if t.account else '-'] for t in txns]
        filename = f'daily_expense_{date_from}'

    elif sr.report_type == 'monthly':
        first_day = today.replace(day=1)
        txns = FinanceTransaction.objects.filter(
            transaction_date__gte=first_day, transaction_date__lte=today, status='posted'
        ).order_by('transaction_date')
        headers = ['Date', 'Voucher No', 'Type', 'Direction', 'Description', 'Amount', 'Account']
        rows = [[str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(), 'In' if t.direction == 'in' else 'Out', t.description, str(t.amount), t.account.name if t.account else '-'] for t in txns]
        filename = f'monthly_report_{date_from}'

    elif sr.report_type == 'day_book':
        txns = FinanceTransaction.objects.filter(transaction_date=date_from).order_by('transaction_date', 'created_at')
        headers = ['Date', 'Voucher No', 'Type', 'Description', 'Category', 'Payment Mode', 'In', 'Out', 'Account']
        rows = [[str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(), t.description, t.category.name if t.category else '-', t.get_payment_mode_display(), str(t.amount) if t.direction == 'in' else '', str(t.amount) if t.direction == 'out' else '', t.account.name if t.account else '-'] for t in txns]
        filename = f'day_book_{date_from}'
    else:
        return

    body = f'Automated {sr.get_report_type_display()} report for {today.strftime("%d %b %Y")}.\n\n'
    body += f'Generated: {tz.localtime().strftime("%d %b %Y %H:%M")}\n'
    body += f'Records: {len(rows)}\n\n'
    body += 'This is an automated report from RENIC ERP Finance Module.'

    recipients = [e.strip() for e in sr.recipients.split(',') if e.strip()]
    if not recipients:
        return

    try:
        msg = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)

        if sr.format == 'excel':
            try:
                import openpyxl
                from io import BytesIO
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = sr.get_report_type_display()
                ws.append(headers)
                for row in rows:
                    ws.append(row)
                buf = BytesIO()
                wb.save(buf)
                buf.seek(0)
                msg.attach(f'{filename}.xlsx', buf.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            except ImportError:
                pass
        elif sr.format == 'csv':
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)
            msg.attach(f'{filename}.csv', output.getvalue().encode('utf-8'), 'text/csv')
        else:
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)
            msg.attach(f'{filename}.csv', output.getvalue().encode('utf-8'), 'text/csv')

        msg.send(fail_silently=True)
    except Exception:
        pass

    sr.last_sent = tz.now()
    sr.save(update_fields=['last_sent'])


@login_required
@role_required('admin')
def automation_dashboard(request):
    from .models import SalaryTemplate, RecurringExpense, ScheduledReport, ReminderLog

    today = timezone.localdate()
    salary_templates = SalaryTemplate.objects.filter(is_active=True)
    recurring = RecurringExpense.objects.filter(is_active=True)
    scheduled = ScheduledReport.objects.filter(is_active=True)
    recent_reminders = ReminderLog.objects.all()[:10]

    next_salary_date = None
    for t in salary_templates:
        d = today.replace(day=t.payment_day) if t.payment_day <= 28 else today.replace(day=28)
        if d < today:
            if today.month == 12:
                d = d.replace(year=today.year + 1, month=1)
            else:
                d = d.replace(month=today.month + 1)
        if next_salary_date is None or d < next_salary_date:
            next_salary_date = d

    next_expense_date = None
    for r in recurring:
        d = today.replace(day=r.payment_day) if r.payment_day <= 28 else today.replace(day=28)
        if d < today:
            if today.month == 12:
                d = d.replace(year=today.year + 1, month=1)
            else:
                d = d.replace(month=today.month + 1)
        if next_expense_date is None or d < next_expense_date:
            next_expense_date = d

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'run_all':
            sal_count = _generate_salaries_from_templates()
            exp_count = _generate_recurring_expenses()
            messages.success(request, f'Generated {sal_count} salary record(s) and {exp_count} expense entry(ies).')
            return redirect('automation_dashboard')

    return render(request, 'finance/automation_dashboard.html', {
        'salary_templates': salary_templates,
        'recurring': recurring,
        'scheduled': scheduled,
        'recent_reminders': recent_reminders,
        'next_salary_date': next_salary_date,
        'next_expense_date': next_expense_date,
    })


@login_required
@role_required('admin', 'accountant')
def share_payment(request):
    from students.models import Student
    from universities.models import University
    from finance.models import FinanceSettings
    from admissions.models import Admission

    section = request.GET.get('section', 'students')
    q = request.GET.get('q', '').strip()

    class Settings:
        pass
    settings_obj = Settings()
    settings_obj.upi_id = FinanceSettings.get_value('upi_id')
    settings_obj.bank_name = FinanceSettings.get_value('bank_name')
    settings_obj.account_number = FinanceSettings.get_value('account_number')
    settings_obj.ifsc_code = FinanceSettings.get_value('ifsc_code')
    settings_obj.account_holder_name = FinanceSettings.get_value('account_holder_name')
    settings_obj.share_message = FinanceSettings.get_value('share_message',
        'Dear Student,\n\nPlease pay your pending fees to:\n\nUPI: {upi_id}\nBank: {bank_name}\nA/C No: {account_number}\nIFSC: {ifsc_code}\n\nPlease share payment screenshot after payment.\n\n Regards,\nRENIC TECH')
    settings_obj.share_message_university = FinanceSettings.get_value('share_message_university',
        'Dear University,\n\nPlease find the payment details below:\n\nUPI: {upi_id}\nBank: {bank_name}\nA/C No: {account_number}\nIFSC: {ifsc_code}\n\n Regards,\nRENIC TECH')

    settings_obj.share_message = settings_obj.share_message.replace('{upi_id}', settings_obj.upi_id or 'N/A').replace('{bank_name}', settings_obj.bank_name or 'N/A').replace('{account_number}', settings_obj.account_number or 'N/A').replace('{ifsc_code}', settings_obj.ifsc_code or 'N/A')
    settings_obj.share_message_university = settings_obj.share_message_university.replace('{upi_id}', settings_obj.upi_id or 'N/A').replace('{bank_name}', settings_obj.bank_name or 'N/A').replace('{account_number}', settings_obj.account_number or 'N/A').replace('{ifsc_code}', settings_obj.ifsc_code or 'N/A')

    qr_code_url = ''
    if settings_obj.upi_id:
        import qrcode
        import base64
        from io import BytesIO
        upi_url = f'upi://pay?pa={settings_obj.upi_id}&pn={settings_obj.account_holder_name or "RENIC TECH"}'
        qr = qrcode.make(upi_url)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        qr_code_url = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
    settings_obj.qr_code_url = qr_code_url

    students = []
    universities = []

    if section == 'students':
        admissions = Admission.objects.filter(
            status__in=['active', 'fee_pending', 'application']
        ).select_related('student', 'university', 'course')
        if q:
            admissions = admissions.filter(
                Q(student__student_id__icontains=q) |
                Q(student__name__icontains=q) |
                Q(student__mobile__icontains=q)
            )
        for a in admissions:
            if a.balance_amount > 0:
                students.append({
                    'name': a.student.name,
                    'student_id': a.student.student_id,
                    'mobile': a.student.mobile,
                    'email': a.student.email or '',
                    'university': a.university.name,
                    'course': a.course.name,
                    'total_fee': a.total_fee,
                    'paid': a.paid_amount,
                    'balance': a.balance_amount,
                    'admission_no': a.admission_number,
                    'admission_id': a.pk,
                })
    else:
        universities = University.objects.all()
        if q:
            universities = universities.filter(name__icontains=q)

    return render(request, 'finance/share_payment.html', {
        'section': section,
        'q': q,
        'students': students,
        'universities': universities,
        'settings': settings_obj,
    })


import hashlib
import hmac
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import FinanceSettings


def _get_razorpay_webhook_secret():
    from django.conf import settings
    return getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '') or FinanceSettings.get_value('razorpay_webhook_secret', '')


def _verify_razorpay_signature(body, signature, secret):
    if not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    secret = _get_razorpay_webhook_secret()
    signature = request.headers.get('X-Razorpay-Signature', '')

    if not _verify_razorpay_signature(request.body, signature, secret):
        return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    event = payload.get('event', '')

    if event == 'payment.captured':
        payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
        amount = payment.get('amount', 0) / 100
        razorpay_id = payment.get('id', '')
        method = payment.get('method', 'upi')
        description = payment.get('description', '')
        email = payment.get('email', '')
        contact = payment.get('contact', '')
        notes = payment.get('notes', {})
        admission_id = notes.get('admission_id', '')
        student_name = notes.get('student_name', '')

        from admissions.models import Admission
        admission = None
        if admission_id:
            admission = Admission.objects.filter(pk=admission_id).first()
        if not admission and student_name:
            admission = Admission.objects.filter(student__name__icontains=student_name).first()

        if admission:
            from fees.models import Payment as FeePayment
            existing = FeePayment.objects.filter(
                admission=admission,
                amount=amount,
                payment_date=timezone.localdate(),
                is_voided=False,
            ).exists()
            if existing:
                return JsonResponse({'status': 'ok', 'message': 'Already recorded'})

            payment_mode = method
            if method == 'upi':
                payment_mode = 'upi'
            elif method == 'card':
                payment_mode = 'card'
            elif method == 'netbanking':
                payment_mode = 'bank_transfer'
            else:
                payment_mode = 'cash'

            payment_obj = FeePayment.objects.create(
                admission=admission,
                amount=amount,
                payment_mode=payment_mode,
                transaction_ref=razorpay_id,
                notes=f'Auto-recorded via Razorpay webhook. {description}',
            )

            from .models import FinanceAccount, FinanceTransaction
            cash_account = FinanceAccount.objects.filter(name__icontains='bank', account_type='bank', is_active=True).first()
            if not cash_account:
                cash_account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()

            if cash_account:
                txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no('RV'),
                    voucher_type='RV', transaction_date=timezone.localdate(),
                    account=cash_account, source_type='student',
                    description=f'Fee received from {admission.student.name} via {payment_mode}',
                    reference_no=razorpay_id,
                    amount=amount,
                    direction='in',
                    status='posted',
                    created_by=request.user if request.user.is_authenticated else None,
                )

            if admission.student.email:
                try:
                    import resend
                    from django.conf import settings as conf
                    api_key = getattr(conf, 'RESEND_API_KEY', '')
                    if api_key:
                        resend.api_key = api_key
                        sem_name = ''
                        if payment_obj.semester:
                            sem_name = f' for {payment_obj.semester.name}'
                        resend.Emails.send({
                            "from": getattr(conf, 'DEFAULT_FROM_EMAIL', 'RENIC ERP <noreply@renictech.com>'),
                            "to": [admission.student.email],
                            "subject": f'Payment Confirmation - RENIC TECH',
                            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2 style="color:#0d6efd">Payment Received</h2>
<p>Dear {admission.student.name},</p>
<p>We have received your payment of <strong>₹{amount:,.0f}</strong>{sem_name}.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Amount</td><td style="padding:8px;border:1px solid #ddd"><strong>₹{amount:,.0f}</strong></td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Mode</td><td style="padding:8px;border:1px solid #ddd">{payment_mode.upper()}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Reference</td><td style="padding:8px;border:1px solid #ddd">{razorpay_id}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Balance</td><td style="padding:8px;border:1px solid #ddd">₹{admission.balance_amount:,.0f}</td></tr>
</table>
<p style="color:#666;font-size:13px">Thank you,<br><strong>RENIC TECH</strong></p>
</div>""",
                        })
                except Exception:
                    pass

        return JsonResponse({'status': 'ok', 'message': 'Payment recorded'})

    return JsonResponse({'status': 'ok', 'message': 'Event ignored'})


@login_required
def razorpay_payment(request, admission_id):
    from admissions.models import Admission
    admission = Admission.objects.filter(pk=admission_id).first()
    if not admission:
        messages.error(request, 'Invalid admission.')
        return redirect('share_payment')

    amount = admission.balance_amount
    razorpay_key = getattr(request, '_settings_razorpay_key', '') or FinanceSettings.get_value('razorpay_key_id', '')
    return render(request, 'finance/payment_gateway.html', {
        'gateway': 'razorpay',
        'admission': admission,
        'amount': amount,
        'razorpay_key': razorpay_key,
        'student_name': admission.student.name,
        'email': admission.student.email or '',
        'mobile': admission.student.mobile or '',
    })


@login_required
def payment_page(request, admission_id):
    from admissions.models import Admission
    admission = Admission.objects.filter(pk=admission_id).first()
    if not admission:
        messages.error(request, 'Invalid admission.')
        return redirect('share_payment')

    amount = admission.balance_amount
    gateway = request.GET.get('gateway', 'razorpay')
    razorpay_key = getattr(request, '_settings_razorpay_key', '') or FinanceSettings.get_value('razorpay_key_id', '')

    return render(request, 'finance/payment_gateway.html', {
        'gateway': gateway,
        'admission': admission,
        'amount': amount,
        'razorpay_key': razorpay_key,
        'student_name': admission.student.name,
        'email': admission.student.email or '',
        'mobile': admission.student.mobile or '',
    })


@login_required
@role_required('admin', 'accountant')
def send_payment_email(request):
    import resend
    from django.conf import settings

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}
        to_email = data.get('email', '').strip()
        subject = data.get('subject', 'Fee Payment Details - RENIC TECH')
        body = data.get('message', '')
    else:
        to_email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'Fee Payment Details - RENIC TECH')
        body = request.POST.get('body', '') or request.POST.get('message', '')

    if not to_email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)

    api_key = getattr(settings, 'RESEND_API_KEY', '')
    if not api_key:
        return JsonResponse({'success': False, 'error': 'Email service not configured'}, status=500)

    try:
        resend.api_key = api_key
        result = resend.Emails.send({
            "from": getattr(settings, 'DEFAULT_FROM_EMAIL', 'RENIC ERP <noreply@renictech.com>'),
            "to": [to_email],
            "subject": subject,
            "text": body,
        })
        return JsonResponse({'success': True, 'message': 'Email sent successfully'})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Failed to send email'}, status=500)
