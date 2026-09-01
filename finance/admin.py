from django.contrib import admin
from .models import (
    FinanceAccount, ExpenseCategory, FinanceTransaction,
    ExpenseEntry, OpeningBalance, DayClosing, FinanceAuditLog,
    UniversityAccount, UniversityTransaction, StaffSalary,
    Refund, Branch, CostCentre, FinanceSettings,
    BankReconciliation, GatewaySettlement, Budget,
    ReminderLog, BankStatementEntry, GSTRecord,
    SalaryTemplate, RecurringExpense, ScheduledReport,
)

admin.site.register(FinanceAccount)
admin.site.register(ExpenseCategory)
admin.site.register(FinanceTransaction)
admin.site.register(ExpenseEntry)
admin.site.register(OpeningBalance)
admin.site.register(DayClosing)
admin.site.register(FinanceAuditLog)
admin.site.register(UniversityAccount)
admin.site.register(UniversityTransaction)
admin.site.register(StaffSalary)
admin.site.register(Refund)
admin.site.register(Branch)
admin.site.register(CostCentre)
admin.site.register(FinanceSettings)
admin.site.register(BankReconciliation)
admin.site.register(GatewaySettlement)
admin.site.register(Budget)
admin.site.register(ReminderLog)
admin.site.register(BankStatementEntry)
admin.site.register(GSTRecord)
admin.site.register(SalaryTemplate)
admin.site.register(RecurringExpense)
admin.site.register(ScheduledReport)
