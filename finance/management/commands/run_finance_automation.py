from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run all finance automations: salary generation, recurring expenses, reminders, scheduled reports'

    def add_arguments(self, parser):
        parser.add_argument('--salary', action='store_true', help='Generate salary records from templates')
        parser.add_argument('--expenses', action='store_true', help='Generate recurring expense entries')
        parser.add_argument('--reminders', action='store_true', help='Generate reminders')
        parser.add_argument('--reports', action='store_true', help='Send scheduled reports')
        parser.add_argument('--all', action='store_true', help='Run all automations')

    def handle(self, *args, **options):
        today = timezone.localdate()
        run_all = options['all']

        if run_all or options['salary']:
            self._generate_salaries(today)

        if run_all or options['expenses']:
            self._generate_expenses(today)

        if run_all or options['reminders']:
            self._generate_reminders(today)

        if run_all or options['reports']:
            self._send_reports(today)

        if not any([run_all, options['salary'], options['expenses'], options['reminders'], options['reports']]):
            self.stdout.write(self.style.WARNING('No automation specified. Use --all, --salary, --expenses, --reminders, or --reports'))

    def _generate_salaries(self, today):
        from finance.models import SalaryTemplate, StaffSalary
        from django.contrib.auth import get_user_model
        User = get_user_model()

        templates = SalaryTemplate.objects.filter(is_active=True)
        salary_month = today.strftime('%Y-%m')
        count = 0
        for tpl in templates:
            user = User.objects.filter(username=tpl.staff_name).first()
            if not user:
                user = User.objects.filter(first_name__icontains=tpl.staff_name).first()
            if not user:
                user = User.objects.filter(last_name__icontains=tpl.staff_name).first()
            if not user:
                logger.warning(f'No user found for template: {tpl.staff_name}')
                continue

            existing = StaffSalary.objects.filter(
                staff=user, salary_month=salary_month
            ).exists()
            if not existing:
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
                count += 1
                logger.info(f'Generated salary for {tpl.staff_name}: ₹{tpl.net_payable}')

        self.stdout.write(self.style.SUCCESS(f'Salary: Generated {count} record(s)'))

    def _generate_expenses(self, today):
        from finance.models import RecurringExpense, ExpenseEntry

        recurring = RecurringExpense.objects.filter(is_active=True)
        count = 0
        for r in recurring:
            if r.payment_day == today.day:
                existing = ExpenseEntry.objects.filter(
                    description__startswith=f'[AUTO] {r.name}',
                    expense_date__year=today.year,
                    expense_date__month=today.month,
                ).exists()
                if not existing:
                    expense_date = today.replace(day=r.payment_day) if r.payment_day <= 28 else today
                    ExpenseEntry.objects.create(
                        category=r.category,
                        amount=r.amount,
                        expense_date=expense_date,
                        description=f'[AUTO] {r.name} - {r.payee}',
                        payment_mode='bank' if r.finance_account and r.finance_account.account_type == 'bank' else 'cash',
                        status='approved',
                        created_by=None,
                    )
                    r.last_generated = today
                    r.save(update_fields=['last_generated'])
                    count += 1
                    logger.info(f'Generated expense for {r.name}: ₹{r.amount}')

        self.stdout.write(self.style.SUCCESS(f'Expenses: Generated {count} entry(ies)'))

    def _generate_reminders(self, today):
        from finance.models import ReminderLog, DayClosing, FinanceSettings, FinanceAccount
        from finance.models import ExpenseEntry, Refund, UniversityTransaction, Budget
        from admissions.models import Admission
        from django.db.models import Sum, F

        count = 0

        unclosed = DayClosing.objects.filter(status__in=['open', 'submitted'])
        for d in unclosed:
            if not ReminderLog.objects.filter(reminder_type='day_not_closed', created_at__date=today).exists():
                ReminderLog.objects.create(
                    reminder_type='day_not_closed',
                    title=f'Day {d.closing_date} not closed',
                    message=f'Status: {d.get_status_display()}. Please close the day.',
                )
                count += 1

        pending_expenses = ExpenseEntry.objects.filter(status='pending_approval').count()
        if pending_expenses > 0 and not ReminderLog.objects.filter(reminder_type='expense_pending', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='expense_pending',
                title=f'{pending_expenses} expense(s) pending approval',
                message='Review and approve pending expenses.',
            )
            count += 1

        pending_refunds = Refund.objects.filter(status='pending_approval').count()
        if pending_refunds > 0 and not ReminderLog.objects.filter(reminder_type='refund_pending', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='refund_pending',
                title=f'{pending_refunds} refund(s) pending approval',
                message='Review and process pending student refunds.',
            )
            count += 1

        low_threshold = Decimal(FinanceSettings.get_value('reminder_low_cash_threshold', '5000'))
        for acc in FinanceAccount.objects.filter(account_type='cash', is_active=True):
            if acc.current_balance < low_threshold:
                if not ReminderLog.objects.filter(reminder_type='low_cash', title__contains=acc.name, created_at__date=today).exists():
                    ReminderLog.objects.create(
                        reminder_type='low_cash',
                        title=f'{acc.name} low balance: ₹{acc.current_balance:,.2f}',
                        message=f'Cash balance is below threshold of ₹{low_threshold}.',
                    )
                    count += 1

        pending_university = UniversityTransaction.objects.filter(status='pending_approval').count()
        if pending_university > 0 and not ReminderLog.objects.filter(reminder_type='university_due', created_at__date=today).exists():
            ReminderLog.objects.create(
                reminder_type='university_due',
                title=f'{pending_university} university transaction(s) pending',
                message='Review pending university payable/receivable transactions.',
            )
            count += 1

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
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'Reminders: Generated {count} reminder(s)'))

    def _send_reports(self, today):
        from finance.models import ScheduledReport

        reports = ScheduledReport.objects.filter(is_active=True)
        count = 0
        for sr in reports:
            should_send = False
            if sr.frequency == 'daily':
                should_send = True
            elif sr.frequency == 'weekly' and today.isoweekday() == sr.send_day:
                should_send = True
            elif sr.frequency == 'monthly' and today.day == sr.send_day:
                should_send = True

            if should_send:
                from django.core.mail import EmailMessage
                from django.conf import settings

                subject = f'[RENIC ERP] {sr.get_report_type_display()} - {today.strftime("%d %b %Y")}'

                from ..models import FinanceTransaction
                date_str = today.isoformat()

                if sr.report_type == 'daily_collection':
                    txns = FinanceTransaction.objects.filter(transaction_date=date_str, direction='in', status='posted', source_type='student').order_by('transaction_date')
                    headers = ['Date', 'Voucher No', 'Description', 'Payment Mode', 'Amount', 'Account']
                    rows = [[str(t.transaction_date), t.voucher_no, t.description, t.get_payment_mode_display(), str(t.amount), t.account.name if t.account else '-'] for t in txns]
                    fname = f'daily_collection_{date_str}'
                elif sr.report_type == 'daily_expense':
                    txns = FinanceTransaction.objects.filter(transaction_date=date_str, direction='out', status='posted').order_by('transaction_date')
                    headers = ['Date', 'Voucher No', 'Description', 'Category', 'Payment Mode', 'Amount', 'Account']
                    rows = [[str(t.transaction_date), t.voucher_no, t.description, t.category.name if t.category else '-', t.get_payment_mode_display(), str(t.amount), t.account.name if t.account else '-'] for t in txns]
                    fname = f'daily_expense_{date_str}'
                elif sr.report_type == 'monthly':
                    first_day = today.replace(day=1)
                    txns = FinanceTransaction.objects.filter(transaction_date__gte=first_day, transaction_date__lte=today, status='posted').order_by('transaction_date')
                    headers = ['Date', 'Voucher No', 'Type', 'Direction', 'Description', 'Amount', 'Account']
                    rows = [[str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(), 'In' if t.direction == 'in' else 'Out', t.description, str(t.amount), t.account.name if t.account else '-'] for t in txns]
                    fname = f'monthly_report_{date_str}'
                elif sr.report_type == 'day_book':
                    txns = FinanceTransaction.objects.filter(transaction_date=date_str).order_by('transaction_date', 'created_at')
                    headers = ['Date', 'Voucher No', 'Type', 'Description', 'Category', 'Payment Mode', 'In', 'Out', 'Account']
                    rows = [[str(t.transaction_date), t.voucher_no, t.get_voucher_type_display(), t.description, t.category.name if t.category else '-', t.get_payment_mode_display(), str(t.amount) if t.direction == 'in' else '', str(t.amount) if t.direction == 'out' else '', t.account.name if t.account else '-'] for t in txns]
                    fname = f'day_book_{date_str}'
                else:
                    continue

                body = f'Automated {sr.get_report_type_display()} report for {today.strftime("%d %b %Y")}.\n\n'
                body += f'Generated: {timezone.localtime().strftime("%d %b %Y %H:%M")}\n'
                body += f'Records: {len(rows)}\n\n'
                body += 'This is an automated report from RENIC ERP Finance Module.'

                recipients = [e.strip() for e in sr.recipients.split(',') if e.strip()]
                if recipients:
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
                                msg.attach(f'{fname}.xlsx', buf.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                            except ImportError:
                                pass
                        else:
                            import csv
                            from io import StringIO
                            output = StringIO()
                            writer = csv.writer(output)
                            writer.writerow(headers)
                            writer.writerows(rows)
                            msg.attach(f'{fname}.csv', output.getvalue().encode('utf-8'), 'text/csv')
                        msg.send(fail_silently=True)
                        sr.last_sent = timezone.now()
                        sr.save(update_fields=['last_sent'])
                        count += 1
                        logger.info(f'Sent report: {sr.name} to {recipients}')
                    except Exception as e:
                        logger.error(f'Failed to send report {sr.name}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Reports: Sent {count} report(s)'))
