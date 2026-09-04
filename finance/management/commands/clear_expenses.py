from django.core.management.base import BaseCommand
from finance.models import ExpenseEntry, FinanceTransaction


class Command(BaseCommand):
    help = 'Delete all expenses and their linked FinanceTransactions'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        expenses = ExpenseEntry.objects.all()
        expense_txns = FinanceTransaction.objects.filter(source_type='expense')
        count = expenses.count()
        txn_count = expense_txns.count()

        self.stdout.write(f'Found {count} expenses and {txn_count} linked FinanceTransactions')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes made'))
            return

        expense_txns.delete()
        deleted = expenses.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expenses and {txn_count} FinanceTransactions'))
