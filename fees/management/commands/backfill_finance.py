from django.core.management.base import BaseCommand
from fees.models import Payment
from finance.models import FinanceAccount, FinanceTransaction, generate_voucher_no


class Command(BaseCommand):
    help = 'Backfill missing FinanceTransactions for payments that have none'

    def handle(self, *args, **options):
        account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
        if not account:
            account = FinanceAccount.objects.create(name='Cash Account', account_type='cash', is_active=True)
            self.stdout.write(self.style.SUCCESS('Created default Cash Account'))

        payments = Payment.objects.filter(is_voided=False).order_by('payment_date')
        created = 0
        for payment in payments:
            exists = FinanceTransaction.objects.filter(
                source_type='student', source_id=payment.admission_id,
                reference_no=payment.receipt_number
            ).exists()
            if exists:
                continue

            FinanceTransaction.objects.create(
                voucher_no=generate_voucher_no('RV'),
                voucher_type='RV', transaction_date=payment.payment_date,
                account=account, source_type='student', source_id=payment.admission_id,
                description=f'Student Fee - {payment.admission.student.name} ({payment.admission.admission_number}){f" - {payment.semester.name}" if payment.semester else ""}',
                amount=payment.amount, direction='in',
                payment_mode=payment.payment_mode,
                reference_no=payment.receipt_number,
                status='posted', created_by=None,
            )
            created += 1
            self.stdout.write(f'  Created transaction for {payment.receipt_number}: Rs. {payment.amount}')

        self.stdout.write(self.style.SUCCESS(f'Done. Created {created} missing FinanceTransactions.'))
