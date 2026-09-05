from django.core.management.base import BaseCommand
from finance.models import FinanceTransaction


class Command(BaseCommand):
    help = 'Remove duplicate FinanceTransactions created by auto-allocation (keeps one per payment receipt)'

    def handle(self, *args, **options):
        seen = {}
        deleted = 0

        txns = FinanceTransaction.objects.filter(
            source_type='student', voucher_type='RV', status='posted'
        ).order_by('id')

        for txn in txns:
            key = (txn.account_id, txn.source_id, str(txn.transaction_date), txn.amount)
            if key in seen:
                txn.delete()
                deleted += 1
            else:
                seen[key] = txn

        self.stdout.write(self.style.SUCCESS(f'Cleaned up {deleted} duplicate FinanceTransactions'))
