from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from datetime import date
from decimal import Decimal
from .models import Payment
from .forms import PaymentForm
from admissions.models import Admission
from core.audit import log_action
from accounts.decorators import admin_required, role_required
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


@login_required
@role_required('admin', 'accountant')
def fee_dashboard(request):
    from django.db.models import Q, Sum, Count
    from django.utils import timezone
    q = request.GET.get('q', '').strip()
    total_collected = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    total_fees = Admission.objects.aggregate(t=Sum('total_fee'))['t'] or 0
    total_pending = total_fees - total_collected
    all_admissions = Admission.objects.select_related('student').all()
    pending_students = sum(1 for a in all_admissions if a.balance_amount > 0)

    admissions = Admission.objects.select_related('student', 'university', 'course').all()
    if q:
        admissions = admissions.filter(
            Q(student__student_id__icontains=q) | Q(student__name__icontains=q) | Q(student__mobile__icontains=q)
        )

    student_data = []
    for a in admissions:
        semesters = Semester.objects.filter(course=a.course).order_by('semester_number')
        semester_payments = []
        for sem in semesters:
            paid = Payment.objects.filter(
                admission=a, semester=sem, is_voided=False
            ).aggregate(t=Sum('amount'))['t'] or 0
            is_overdue = timezone.localdate() > sem.due_date and paid < sem.fee_amount
            days_left = (sem.due_date - timezone.localdate()).days
            semester_payments.append({
                'semester': sem,
                'paid': paid,
                'balance': sem.fee_amount - paid,
                'is_paid': paid >= sem.fee_amount,
                'is_overdue': is_overdue,
                'days_left': days_left,
            })
        total_paid = sum(sp['paid'] for sp in semester_payments)
        total_balance = sum(sp['balance'] for sp in semester_payments)
        student_data.append({
            'admission': a,
            'semesters': semester_payments,
            'total_paid': total_paid,
            'total_balance': total_balance,
        })

    error_msg = ''
    if q and not admissions.exists():
        error_msg = f'No students found for "{q}".'

    return render(request, 'fees/dashboard.html', {
        'total_collected': total_collected,
        'total_fees': total_fees,
        'total_pending': total_pending,
        'pending_students': pending_students,
        'student_data': student_data,
        'admissions': admissions,
        'q': q,
        'error_msg': error_msg,
    })


@login_required
@role_required('admin', 'accountant')
def payment_create(request, admission_id):
    admission = get_object_or_404(Admission, pk=admission_id)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.admission = admission
            payment.received_by = request.user
            payment.save()
            log_action(request.user, 'payment', 'Payment', payment.pk, payment.receipt_number, details=f"Rs. {payment.amount} for {admission.admission_number}")

            if not payment.semester:
                remaining = payment.amount
                semesters = Semester.objects.filter(course=admission.course, is_active=True).order_by('semester_number')
                for sem in semesters:
                    if remaining <= 0:
                        break
                    paid = Payment.objects.filter(admission=admission, semester=sem, is_voided=False).exclude(pk=payment.pk).aggregate(t=Sum('amount'))['t'] or 0
                    balance = sem.fee_amount - paid
                    if balance <= 0:
                        continue
                    allocate = min(remaining, balance)
                    sem_payment = Payment.objects.create(
                        admission=admission, semester=sem, amount=allocate,
                        payment_date=payment.payment_date, payment_mode=payment.payment_mode,
                        transaction_ref=payment.receipt_number, received_by=request.user,
                        notes=f'Auto-allocated from {payment.receipt_number}'
                    )
                    remaining -= allocate

            try:
                from finance.models import FinanceAccount, FinanceTransaction, generate_voucher_no
                account = FinanceAccount.objects.filter(
                    account_type='upi' if payment.payment_mode == 'upi' else
                    'bank' if payment.payment_mode in ('bank_transfer', 'neft', 'rtgs', 'imps', 'card') else
                    'cash', is_active=True
                ).first()
                if not account:
                    account = FinanceAccount.objects.filter(account_type='cash', is_active=True).first()
                if account:
                    FinanceTransaction.objects.create(
                        voucher_type='RV', transaction_date=payment.payment_date,
                        account=account, source_type='student', source_id=admission.pk,
                        description=f'Student Fee - {admission.student.name} ({admission.admission_number})',
                        amount=payment.amount, direction='in',
                        payment_mode=payment.payment_mode,
                        reference_no=payment.receipt_number,
                        status='posted', created_by=request.user,
                    )
                else:
                    import logging
                    logging.warning(f'Finance: No finance account found for payment mode {payment.payment_mode}')
            except Exception as e:
                import logging
                logging.error(f'Finance: Failed to create finance transaction for payment {payment.receipt_number}: {e}')

            messages.success(request, f'Payment {payment.receipt_number} recorded.')
            return redirect('admission_detail', pk=admission_id)
    else:
        form = PaymentForm(initial={'payment_date': date.today()})
    return render(request, 'fees/payment_form.html', {'form': form, 'admission': admission})


@login_required
@role_required('admin', 'accountant')
def payment_detail(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('admission__student', 'admission__university', 'admission__course', 'received_by'), pk=pk)
    return render(request, 'fees/payment_detail.html', {'payment': payment})


@login_required
@admin_required
def payment_void(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        payment.is_voided = True
        payment.voided_reason = reason
        payment.save()
        log_action(request.user, 'void', 'Payment', payment.pk, payment.receipt_number, details=f"Reason: {reason}")
        messages.success(request, f'Payment {payment.receipt_number} voided.')
    return redirect('admission_detail', pk=payment.admission_id)


@login_required
@role_required('admin', 'accountant')
def receipt_view(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('admission__student', 'admission__university', 'admission__course', 'received_by'), pk=pk)
    return render(request, 'fees/receipt.html', {'payment': payment})


@login_required
@role_required('admin', 'accountant')
def receipt_pdf(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('admission__student', 'admission__university', 'admission__course', 'received_by'), pk=pk)
    admission = payment.admission

    NAVY = HexColor('#0f172a')
    GOLD = HexColor('#f59e0b')
    BLUE = HexColor('#2563eb')
    GREEN = HexColor('#16a34a')
    LIGHT_BG = HexColor('#f8fafc')
    GRAY = HexColor('#64748b')
    DARK = HexColor('#1e293b')
    BORDER = HexColor('#e2e8f0')

    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header background
    p.setFillColor(NAVY)
    p.rect(0, h - 100, w, 100, fill=1, stroke=0)

    # Gold accent line
    p.setFillColor(GOLD)
    p.rect(0, h - 104, w, 4, fill=1, stroke=0)

    # Company name
    p.setFillColor(HexColor('#ffffff'))
    p.setFont('Helvetica-Bold', 22)
    p.drawCentredString(w / 2, h - 45, 'RENIC TECH')
    p.setFont('Helvetica', 10)
    p.setFillColor(HexColor('#94a3b8'))
    p.drawCentredString(w / 2, h - 62, 'Distance Education ERP')

    # Receipt title
    p.setFillColor(GOLD)
    p.setFont('Helvetica-Bold', 14)
    p.drawCentredString(w / 2, h - 85, 'FEE RECEIPT')

    y = h - 130

    # Receipt info box
    p.setFillColor(LIGHT_BG)
    p.roundRect(40, y - 80, w - 80, 80, 8, fill=1, stroke=0)

    p.setFillColor(DARK)
    p.setFont('Helvetica-Bold', 10)
    p.drawString(55, y - 20, 'Receipt No:')
    p.setFont('Helvetica', 10)
    p.setFillColor(BLUE)
    p.drawString(130, y - 20, payment.receipt_number)

    p.setFillColor(DARK)
    p.setFont('Helvetica-Bold', 10)
    p.drawString(55, y - 38, 'Date:')
    p.setFont('Helvetica', 10)
    p.drawString(130, y - 38, str(payment.payment_date))

    p.setFont('Helvetica-Bold', 10)
    p.drawString(55, y - 56, 'Admission:')
    p.setFont('Helvetica', 10)
    p.drawString(130, y - 56, admission.admission_number)

    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 20, 'Student:')
    p.setFont('Helvetica', 10)
    p.drawString(360, y - 20, f'{admission.student.name}')

    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 38, 'ID:')
    p.setFont('Helvetica', 10)
    p.drawString(360, y - 38, admission.student.student_id)

    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 56, 'Course:')
    p.setFont('Helvetica', 10)
    p.drawString(360, y - 56, admission.course.name)

    y -= 110

    # University info
    p.setFillColor(DARK)
    p.setFont('Helvetica-Bold', 10)
    p.drawString(55, y, 'University:')
    p.setFont('Helvetica', 10)
    p.drawString(130, y, admission.university.name)

    y -= 35

    # Payment Details Section
    p.setFillColor(NAVY)
    p.roundRect(40, y - 110, w - 80, 110, 8, fill=1, stroke=0)

    p.setFillColor(GOLD)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(55, y - 18, 'PAYMENT DETAILS')

    # Amount Paid - large
    p.setFillColor(HexColor('#ffffff'))
    p.setFont('Helvetica-Bold', 28)
    p.drawString(55, y - 55, f'Rs. {payment.amount:,.2f}')

    p.setFillColor(HexColor('#94a3b8'))
    p.setFont('Helvetica', 10)
    p.drawString(55, y - 70, 'Amount Paid')

    # Payment mode
    p.setFillColor(HexColor('#ffffff'))
    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 40, 'Payment Mode:')
    p.setFont('Helvetica', 10)
    p.drawString(400, y - 40, payment.get_payment_mode_display())

    # Transaction ref
    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 58, 'Transaction Ref:')
    p.setFont('Helvetica', 10)
    p.drawString(400, y - 58, payment.transaction_ref or 'N/A')

    # Received by
    p.setFont('Helvetica-Bold', 10)
    p.drawString(300, y - 76, 'Received By:')
    p.setFont('Helvetica', 10)
    p.drawString(400, y - 76, payment.received_by.get_full_name() or payment.received_by.username)

    y -= 135

    # Fee Summary
    p.setFillColor(LIGHT_BG)
    p.roundRect(40, y - 80, w - 80, 80, 8, fill=1, stroke=0)

    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(55, y - 18, 'FEE SUMMARY')

    col_w = (w - 80) / 3

    # Total Fee
    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(55, y - 40, 'Total Fee')
    p.setFillColor(DARK)
    p.setFont('Helvetica-Bold', 14)
    p.drawString(55, y - 58, f'Rs. {admission.total_fee:,.2f}')

    # Total Paid
    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(55 + col_w, y - 40, 'Total Paid')
    p.setFillColor(GREEN)
    p.setFont('Helvetica-Bold', 14)
    p.drawString(55 + col_w, y - 58, f'Rs. {admission.paid_amount:,.2f}')

    # Balance
    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(55 + col_w * 2, y - 40, 'Balance')
    balance_color = GREEN if admission.balance_amount == 0 else HexColor('#dc2626')
    p.setFillColor(balance_color)
    p.setFont('Helvetica-Bold', 14)
    p.drawString(55 + col_w * 2, y - 58, f'Rs. {admission.balance_amount:,.2f}')

    y -= 120

    # Signature section
    p.setStrokeColor(BORDER)
    p.setLineWidth(0.5)
    p.line(50, y, 200, y)
    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(50, y - 15, 'Authorized Signature')

    p.line(w - 200, y, w - 50, y)
    p.drawString(w - 200, y - 15, 'Student Signature')

    # Footer
    p.setFillColor(NAVY)
    p.rect(0, 0, w, 40, fill=1, stroke=0)
    p.setFillColor(HexColor('#94a3b8'))
    p.setFont('Helvetica', 7)
    p.drawCentredString(w / 2, 25, 'RENIC TECH — Distance Education ERP | This is a computer-generated receipt.')
    p.drawCentredString(w / 2, 15, f'Generated on {date.today().strftime("%d %B %Y")} | For queries contact admin@renictech.com')

    # Gold line above footer
    p.setFillColor(GOLD)
    p.rect(0, 40, w, 2, fill=1, stroke=0)

    p.showPage()
    p.save()
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{payment.receipt_number}.pdf"'
    return response


@login_required
@role_required('admin', 'accountant')
def fee_statement_pdf(request, admission_id):
    from .models import Semester
    admission = get_object_or_404(Admission.objects.select_related('student', 'university', 'course'), pk=admission_id)
    payments = Payment.objects.filter(admission=admission, is_voided=False).order_by('payment_date')
    semesters = Semester.objects.filter(course=admission.course).order_by('semester_number')

    NAVY = HexColor('#0f172a')
    GOLD = HexColor('#d4a843')
    GREEN = HexColor('#059669')
    RED = HexColor('#dc2626')
    GRAY = HexColor('#6b7280')
    LIGHT_BG = HexColor('#f8fafc')
    WHITE = HexColor('#ffffff')

    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header
    p.setFillColor(NAVY)
    p.rect(0, h - 120, w, 120, fill=1, stroke=0)
    p.setFillColor(GOLD)
    p.rect(0, h - 124, w, 4, fill=1, stroke=0)

    p.setFillColor(WHITE)
    p.setFont('Helvetica-Bold', 24)
    p.drawCentredString(w / 2, h - 45, 'RENIC TECH')
    p.setFont('Helvetica', 10)
    p.setFillColor(HexColor('#94a3b8'))
    p.drawCentredString(w / 2, h - 62, 'Distance Education ERP')

    p.setFillColor(GOLD)
    p.setFont('Helvetica-Bold', 16)
    p.drawCentredString(w / 2, h - 90, 'FEE STATEMENT')

    p.setFillColor(HexColor('#94a3b8'))
    p.setFont('Helvetica', 9)
    p.drawCentredString(w / 2, h - 108, f'Generated on {date.today().strftime("%d %B %Y")}')

    y = h - 150

    # Student Info Box
    p.setFillColor(LIGHT_BG)
    p.roundRect(40, y - 90, w - 80, 90, 8, fill=1, stroke=0)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(55, y - 15, 'Student Name')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 13)
    p.drawString(55, y - 32, admission.student.name)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(250, y - 15, 'Student ID')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(250, y - 32, admission.student.student_id)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(400, y - 15, 'Admission No')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(400, y - 32, admission.admission_number)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(55, y - 58, 'University')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 11)
    p.drawString(55, y - 75, admission.university.name)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(250, y - 58, 'Course')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 11)
    p.drawString(250, y - 75, admission.course.name)

    p.setFillColor(GRAY)
    p.setFont('Helvetica', 9)
    p.drawString(400, y - 58, 'Mobile')
    p.setFillColor(NAVY)
    p.setFont('Helvetica-Bold', 11)
    p.drawString(400, y - 75, admission.student.mobile or '-')

    y -= 110

    # Fee Summary
    p.setFillColor(NAVY)
    p.roundRect(40, y - 60, (w - 90) / 3, 60, 6, fill=1, stroke=0)
    p.setFillColor(WHITE)
    p.setFont('Helvetica', 10)
    p.drawString(55, y - 18, 'Total Fee')
    p.setFont('Helvetica-Bold', 18)
    p.drawString(55, y - 45, f'Rs. {admission.total_fee:,.0f}')

    p.setFillColor(GREEN)
    p.roundRect(40 + (w - 80) / 3 + 5, y - 60, (w - 90) / 3, 60, 6, fill=1, stroke=0)
    p.setFillColor(WHITE)
    p.setFont('Helvetica', 10)
    p.drawString(55 + (w - 80) / 3 + 5, y - 18, 'Paid')
    p.setFont('Helvetica-Bold', 18)
    p.drawString(55 + (w - 80) / 3 + 5, y - 45, f'Rs. {admission.paid_amount:,.0f}')

    balance_color = GREEN if admission.balance_amount == 0 else RED
    p.setFillColor(balance_color)
    p.roundRect(40 + 2 * ((w - 80) / 3 + 5), y - 60, (w - 90) / 3, 60, 6, fill=1, stroke=0)
    p.setFillColor(WHITE)
    p.setFont('Helvetica', 10)
    p.drawString(55 + 2 * ((w - 80) / 3 + 5), y - 18, 'Balance')
    p.setFont('Helvetica-Bold', 18)
    p.drawString(55 + 2 * ((w - 80) / 3 + 5), y - 45, f'Rs. {admission.balance_amount:,.0f}')

    y -= 80

    # Semester-wise Breakdown
    if semesters.exists():
        p.setFillColor(NAVY)
        p.setFont('Helvetica-Bold', 12)
        p.drawString(55, y, 'Semester-wise Fee Details')
        y -= 25

        # Table Header
        p.setFillColor(NAVY)
        p.roundRect(40, y - 22, w - 80, 22, 4, fill=1, stroke=0)
        p.setFillColor(WHITE)
        p.setFont('Helvetica-Bold', 9)
        p.drawString(55, y - 16, 'Semester')
        p.drawString(200, y - 16, 'Fee')
        p.drawString(300, y - 16, 'Paid')
        p.drawString(400, y - 16, 'Balance')
        p.drawString(490, y - 16, 'Due Date')
        y -= 28

        for sem in semesters:
            paid = Payment.objects.filter(admission=admission, semester=sem, is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
            balance = sem.fee_amount - paid
            is_paid = paid >= sem.fee_amount

            # Alternate row background
            if semesters.filter(pk__lt=sem.pk).count() % 2 == 0:
                p.setFillColor(LIGHT_BG)
                p.rect(40, y - 18, w - 80, 18, fill=1, stroke=0)

            p.setFillColor(NAVY)
            p.setFont('Helvetica', 9)
            p.drawString(55, y - 12, sem.name)

            p.drawString(200, y - 12, f'Rs. {sem.fee_amount:,.0f}')

            p.setFillColor(GREEN)
            p.drawString(300, y - 12, f'Rs. {paid:,.0f}')

            if balance > 0:
                p.setFillColor(RED)
            else:
                p.setFillColor(GREEN)
            p.drawString(400, y - 12, f'Rs. {balance:,.0f}')

            p.setFillColor(GRAY)
            p.drawString(490, y - 12, sem.due_date.strftime('%d %b %Y'))

            y -= 22

        y -= 10

    # Payment History
    if payments.exists():
        p.setFillColor(NAVY)
        p.setFont('Helvetica-Bold', 12)
        p.drawString(55, y, 'Payment History')
        y -= 25

        # Table Header
        p.setFillColor(NAVY)
        p.roundRect(40, y - 22, w - 80, 22, 4, fill=1, stroke=0)
        p.setFillColor(WHITE)
        p.setFont('Helvetica-Bold', 9)
        p.drawString(55, y - 16, 'Receipt No')
        p.drawString(170, y - 16, 'Date')
        p.drawString(280, y - 16, 'Semester')
        p.drawString(400, y - 16, 'Mode')
        p.drawString(490, y - 16, 'Amount')
        y -= 28

        for pay in payments:
            if payments.filter(pk__lt=pay.pk).count() % 2 == 0:
                p.setFillColor(LIGHT_BG)
                p.rect(40, y - 18, w - 80, 18, fill=1, stroke=0)

            p.setFillColor(NAVY)
            p.setFont('Helvetica', 9)
            p.drawString(55, y - 12, pay.receipt_number)
            p.drawString(170, y - 12, pay.payment_date.strftime('%d %b %Y'))
            p.drawString(280, y - 12, pay.semester.name if pay.semester else '-')
            p.drawString(400, y - 12, pay.get_payment_mode_display())
            p.setFillColor(GREEN)
            p.setFont('Helvetica-Bold', 9)
            p.drawString(490, y - 12, f'Rs. {pay.amount:,.0f}')
            y -= 22
    else:
        p.setFillColor(GRAY)
        p.setFont('Helvetica', 11)
        p.drawCentredString(w / 2, y - 20, 'No payments recorded yet.')
        y -= 40

    # Footer
    p.setFillColor(NAVY)
    p.rect(0, 0, w, 45, fill=1, stroke=0)
    p.setFillColor(GOLD)
    p.rect(0, 45, w, 2, fill=1, stroke=0)
    p.setFillColor(HexColor('#94a3b8'))
    p.setFont('Helvetica', 7)
    p.drawCentredString(w / 2, 30, 'RENIC TECH - Distance Education ERP')
    p.drawCentredString(w / 2, 20, 'This is a computer-generated fee statement. For queries, contact admin@renictech.com')
    p.drawCentredString(w / 2, 10, f'Page 1 of 1 | Generated on {date.today().strftime("%d %B %Y")}')

    p.showPage()
    p.save()
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Fee_Statement_{admission.student.student_id}.pdf"'
    return response


from .models import Semester
from courses.models import Course
from django.utils import timezone


@login_required
@role_required('admin', 'accountant')
def semester_list(request):
    course_id = request.GET.get('course')
    courses = Course.objects.all()
    semesters = Semester.objects.select_related('course').all()
    if course_id:
        semesters = semesters.filter(course_id=course_id)
    return render(request, 'fees/semester_list.html', {
        'semesters': semesters,
        'courses': courses,
        'selected_course': course_id,
    })


@login_required
@role_required('admin', 'accountant')
def semester_add(request):
    from .forms import SemesterForm
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semester added successfully.')
            return redirect('semester_list')
    else:
        form = SemesterForm()
    return render(request, 'fees/semester_form.html', {'form': form, 'title': 'Add Semester'})


@login_required
@role_required('admin', 'accountant')
def semester_edit(request, pk):
    from .forms import SemesterForm
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semester updated successfully.')
            return redirect('semester_list')
    else:
        form = SemesterForm(instance=semester)
    return render(request, 'fees/semester_form.html', {'form': form, 'title': 'Edit Semester', 'semester': semester})


@login_required
@role_required('admin', 'accountant')
def semester_delete(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == 'POST':
        semester.delete()
        messages.success(request, 'Semester deleted.')
        return redirect('semester_list')
    return render(request, 'fees/semester_confirm_delete.html', {'semester': semester})


@login_required
@role_required('admin', 'accountant')
def semester_bulk_create(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course_type = request.POST.get('course_type', 'arts_science')
        total_fee = Decimal(request.POST.get('total_fee', 0))
        start_date = request.POST.get('start_date')

        course = get_object_or_404(Course, pk=course_id)

        if course_type == 'engineering':
            num_years = 4
        else:
            num_years = 3

        num_semesters = num_years * 2
        fee_per_sem = total_fee / num_semesters

        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        start = datetime.strptime(start_date, '%Y-%m-%d').date()

        Semester.objects.filter(course=course).delete()

        for i in range(1, num_semesters + 1):
            due = start + relativedelta(months=6 * (i - 1))
            year = (i - 1) // 2 + 1
            sem_in_year = (i - 1) % 2 + 1
            Semester.objects.create(
                course=course,
                name=f'Year {year} Semester {sem_in_year}',
                semester_number=i,
                fee_amount=fee_per_sem,
                due_date=due,
                description=f'{course.name} - Year {year}, Sem {sem_in_year} ({num_years} years course)',
            )

        messages.success(request, f'{num_semesters} semesters ({num_years} years) created for {course.name}. ₹{fee_per_sem:,.0f} per semester.')
        return redirect('semester_list')

    courses = Course.objects.all()
    return render(request, 'fees/semester_bulk_create.html', {'courses': courses})


@login_required
def student_semester_detail(request, admission_id):
    from django.utils import timezone
    admission = get_object_or_404(Admission, pk=admission_id)
    semesters = Semester.objects.filter(course=admission.course).order_by('semester_number')

    unallocated = Payment.objects.filter(
        admission=admission, semester__isnull=True, is_voided=False
    ).aggregate(t=Sum('amount'))['t'] or 0

    semester_data = []
    for sem in semesters:
        allocated_paid = Payment.objects.filter(
            admission=admission, semester=sem, is_voided=False
        ).aggregate(t=Sum('amount'))['t'] or 0

        if unallocated > 0 and allocated_paid < sem.fee_amount:
            room = sem.fee_amount - allocated_paid
            extra = min(unallocated, room)
            allocated_paid += extra
            unallocated -= extra

        balance = sem.fee_amount - allocated_paid
        is_paid = allocated_paid >= sem.fee_amount
        is_overdue = timezone.localdate() > sem.due_date and not is_paid
        days_left = (sem.due_date - timezone.localdate()).days
        semester_data.append({
            'semester': sem,
            'paid': allocated_paid,
            'balance': balance,
            'is_paid': is_paid,
            'is_overdue': is_overdue,
            'days_left': days_left,
        })

    total_paid = sum(sp['paid'] for sp in semester_data)
    total_balance = sum(sp['balance'] for sp in semester_data)

    return render(request, 'fees/student_semester_detail.html', {
        'admission': admission,
        'semester_data': semester_data,
        'total_paid': total_paid,
        'total_balance': total_balance,
    })
