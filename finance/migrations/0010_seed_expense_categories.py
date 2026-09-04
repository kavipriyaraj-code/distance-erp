from django.db import migrations


def seed_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model('finance', 'ExpenseCategory')

    expense_cats = [
        ('Rent', 'expense'),
        ('Utilities', 'expense'),
        ('Salaries', 'expense'),
        ('Office Supplies', 'expense'),
        ('Travel', 'expense'),
        ('Marketing', 'expense'),
        ('Software & Tools', 'expense'),
        ('Internet & Phone', 'expense'),
        ('Maintenance', 'expense'),
        ('Miscellaneous', 'expense'),
    ]

    income_cats = [
        ('Student Fees', 'income'),
        ('Consulting', 'income'),
        ('Other Income', 'income'),
    ]

    for name, cat_type in expense_cats:
        ExpenseCategory.objects.get_or_create(name=name, defaults={'category_type': cat_type})

    for name, cat_type in income_cats:
        ExpenseCategory.objects.get_or_create(name=name, defaults={'category_type': cat_type})


def reverse_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model('finance', 'ExpenseCategory')
    ExpenseCategory.objects.filter(name__in=[
        'Rent', 'Utilities', 'Salaries', 'Office Supplies', 'Travel',
        'Marketing', 'Software & Tools', 'Internet & Phone', 'Maintenance',
        'Miscellaneous', 'Student Fees', 'Consulting', 'Other Income',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0009_add_automation_models'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_categories),
    ]
