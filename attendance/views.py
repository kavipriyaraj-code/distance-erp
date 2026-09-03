from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, datetime, time
from calendar import monthrange
from decimal import Decimal
from .models import StaffAttendance, AttendanceSettings
from .forms import StaffAttendanceForm
from accounts.decorators import admin_required, role_required


@login_required
@admin_required
def admin_attendance_list(request):
    staff_users = StaffAttendance.objects.filter(
        staff__role__in=['counsellor', 'accountant'], staff__is_active=True
    ).values_list('staff_id', flat=True).distinct()

    all_staff = __import__('accounts.models', fromlist=['User']).User.objects.filter(
        role__in=['counsellor', 'accountant'], is_active=True
    )

    date_filter = request.GET.get('date', '')
    employee_filter = request.GET.get('employee', '')
    role_filter = request.GET.get('role', '')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    status_filter = request.GET.get('status', '')

    records = StaffAttendance.objects.select_related('staff', 'created_by').all()

    if date_filter:
        records = records.filter(date=date_filter)
    if employee_filter:
        records = records.filter(staff_id=employee_filter)
    if role_filter:
        records = records.filter(staff__role=role_filter)
    if month_filter:
        records = records.filter(date__month=month_filter)
    if year_filter:
        records = records.filter(date__year=year_filter)
    if status_filter:
        records = records.filter(status=status_filter)

    today = timezone.localdate()
    current_month = int(month_filter) if month_filter else today.month
    current_year = int(year_filter) if year_filter else today.year

    days_in_month = monthrange(current_year, current_month)[1]
    month_records = StaffAttendance.objects.filter(
        date__year=current_year, date__month=current_month
    )

    summary = {
        'total_days': days_in_month,
        'present': month_records.filter(status='present').count(),
        'absent': month_records.filter(status='absent').count(),
        'half_day': month_records.filter(status='half_day').count(),
        'paid_leave': month_records.filter(status='paid_leave').count(),
        'unpaid_leave': month_records.filter(status='unpaid_leave').count(),
        'holiday': month_records.filter(status='holiday').count(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'mark':
            staff_id = request.POST.get('staff_id')
            att_date = request.POST.get('date', today.isoformat())
            status_val = request.POST.get('status', 'present')
            check_in = request.POST.get('check_in') or None
            check_out = request.POST.get('check_out') or None
            notes = request.POST.get('admin_notes', '')

            if staff_id:
                obj, created = StaffAttendance.objects.update_or_create(
                    staff_id=staff_id, date=att_date,
                    defaults={
                        'status': status_val,
                        'check_in': check_in,
                        'check_out': check_out,
                        'admin_notes': notes,
                        'created_by': request.user,
                    }
                )
                msg = 'marked' if created else 'updated'
                messages.success(request, f'Attendance {msg} for {obj.staff.get_full_name() or obj.staff.username}.')
            return redirect('admin_attendance_list')

        if action == 'bulk_mark':
            att_date = request.POST.get('date', today.isoformat())
            for staff_member in all_staff:
                status_key = f'status_{staff_member.pk}'
                status_val = request.POST.get(status_key, '')
                if status_val:
                    StaffAttendance.objects.update_or_create(
                        staff=staff_member, date=att_date,
                        defaults={
                            'status': status_val,
                            'created_by': request.user,
                        }
                    )
            messages.success(request, f'Bulk attendance marked for {att_date}.')
            return redirect('admin_attendance_list')

        if action == 'edit':
            att_id = request.POST.get('attendance_id')
            att = StaffAttendance.objects.filter(pk=att_id).first()
            if att:
                att.status = request.POST.get('status', att.status)
                att.admin_notes = request.POST.get('admin_notes', att.admin_notes)
                check_in = request.POST.get('check_in')
                check_out = request.POST.get('check_out')
                if check_in:
                    att.check_in = check_in
                if check_out:
                    att.check_out = check_out
                att.save()
                messages.success(request, 'Attendance updated.')
            return redirect('admin_attendance_list')

    return render(request, 'attendance/admin_attendance.html', {
        'records': records[:500],
        'all_staff': all_staff,
        'summary': summary,
        'selected_date': date_filter,
        'selected_employee': employee_filter,
        'selected_role': role_filter,
        'selected_month': month_filter,
        'selected_year': year_filter,
        'selected_status': status_filter,
        'current_month': current_month,
        'current_year': current_year,
        'today': today,
    })


@login_required
@role_required('counsellor', 'accountant')
def staff_checkin_view(request):
    today = timezone.localdate()
    now_time = timezone.localtime().time()
    attendance, _ = StaffAttendance.objects.get_or_create(
        staff=request.user, date=today,
        defaults={'status': 'present', 'check_in': now_time}
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and not attendance.check_in:
            attendance.check_in = now_time
            attendance.status = 'present'
            attendance.save()
            messages.success(request, f'Checked in at {attendance.check_in_display}.')
        elif action == 'checkout' and attendance.check_in and not attendance.check_out:
            attendance.check_out = now_time
            attendance.save()
            messages.success(request, f'Checked out at {attendance.check_out_display}. Working hours: {attendance.working_hours}h.')
        return redirect('staff_checkin')

    history = StaffAttendance.objects.filter(staff=request.user).order_by('-date')[:30]
    return render(request, 'attendance/staff_checkin.html', {
        'attendance': attendance,
        'history': history,
        'today': today,
    })


@login_required
@role_required('counsellor', 'accountant')
def staff_attendance_history(request):
    records = StaffAttendance.objects.filter(staff=request.user).order_by('-date')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    if month_filter:
        records = records.filter(date__month=month_filter)
    if year_filter:
        records = records.filter(date__year=year_filter)

    today = timezone.localdate()
    current_month = int(month_filter) if month_filter else today.month
    current_year = int(year_filter) if year_filter else today.year

    days_in_month = monthrange(current_year, current_month)[1]
    month_records = records.filter(date__year=current_year, date__month=current_month)

    summary = {
        'total_days': days_in_month,
        'present': month_records.filter(status='present').count(),
        'absent': month_records.filter(status='absent').count(),
        'half_day': month_records.filter(status='half_day').count(),
        'paid_leave': month_records.filter(status='paid_leave').count(),
        'unpaid_leave': month_records.filter(status='unpaid_leave').count(),
        'holiday': month_records.filter(status='holiday').count(),
    }

    return render(request, 'attendance/staff_history.html', {
        'records': records[:100],
        'summary': summary,
        'selected_month': month_filter,
        'selected_year': year_filter,
        'current_month': current_month,
        'current_year': current_year,
    })


@login_required
@admin_required
def attendance_monthly_report(request):
    month = int(request.GET.get('month', timezone.localdate().month))
    year = int(request.GET.get('year', timezone.localdate().year))

    staff_users = __import__('accounts.models', fromlist=['User']).User.objects.filter(
        role__in=['counsellor', 'accountant'], is_active=True
    )
    days_in_month = monthrange(year, month)[1]

    staff_data = []
    for s in staff_users:
        records = StaffAttendance.objects.filter(staff=s, date__year=year, date__month=month)
        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        half_day = records.filter(status='half_day').count()
        paid_leave = records.filter(status='paid_leave').count()
        unpaid_leave = records.filter(status='unpaid_leave').count()
        holiday = records.filter(status='holiday').count()
        total_hours = records.aggregate(t=Sum('working_hours'))['t'] or 0

        staff_data.append({
            'staff': s,
            'present': present,
            'absent': absent,
            'half_day': half_day,
            'paid_leave': paid_leave,
            'unpaid_leave': unpaid_leave,
            'holiday': holiday,
            'total_hours': total_hours,
            'total_days': present + absent + half_day + paid_leave + unpaid_leave + holiday,
        })

    return render(request, 'attendance/monthly_report.html', {
        'staff_data': staff_data,
        'month': month,
        'year': year,
        'days_in_month': days_in_month,
    })
