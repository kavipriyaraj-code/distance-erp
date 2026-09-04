from django.core.management.base import BaseCommand
from finance.models import ExpenseEntry, FinanceAccount, FinanceTransaction, generate_voucher_no


class Command(BaseCommand):
    help = 'Backfill FinanceTransactions for approved/pending expenses that have none'

    def handle(self, *args, **options):
        expenses = ExpenseEntry.objects.filter(finance_transaction__isnull=True).exclude(status='cancelled')
        created = 0
        for expense in expenses:
            account = expense.account
            if not account:
                account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
            if not account:
                self.stdout.write(self.style.WARNING(f'Skipped {expense.voucher_no}: no account'))
                continue

            try:
                txn = FinanceTransaction.objects.create(
                    voucher_no=generate_voucher_no('PV'),
                    voucher_type='PV', transaction_date=expense.expense_date,
                    account=account, category=expense.category,
                    source_type='expense', source_id=expense.pk,
                    description=f'Expense: {expense.vendor or expense.description or expense.voucher_no}',
                    amount=expense.amount, direction='out',
                    payment_mode=expense.payment_mode, reference_no=expense.invoice_no,
                    status='posted', created_by=expense.created_by,
                )
                expense.finance_transaction = txn
                expense.status = 'paid'
                expense.save(update_fields=['finance_transaction', 'status'])
                created += 1
                self.stdout.write(f'  Fixed {expense.voucher_no}: Rs. {expense.amount}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error {expense.voucher_no}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Done. Fixed {created} expenses.'))
