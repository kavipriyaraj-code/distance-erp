from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from datetime import date
from .models import Payment
from .forms import PaymentForm
from admissions.models import Admission
from core.audit import log_action
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


@login_required
def fee_dashboard(request):
    total_collected = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    total_fees = Admission.objects.aggregate(t=Sum('total_fee'))['t'] or 0
    total_pending = total_fees - total_collected
    admissions_with_balance = Admission.objects.filter(status__in=['active', 'fee_pending']).select_related('student', 'university', 'course')
    for a in admissions_with_balance:
        a._paid = a.paid_amount
        a._balance = a.balance_amount
    recent_payments = Payment.objects.select_related('admission__student', 'admission__university').filter(is_voided=False)[:20]
    return render(request, 'fees/dashboard.html', {
        'total_collected': total_collected,
        'total_fees': total_fees,
        'total_pending': total_pending,
        'admissions_with_balance': admissions_with_balance,
        'recent_payments': recent_payments,
    })


@login_required
def payment_create(request, admission_id):
    admission = get_object_or_404(Admission, pk=admission_id)
    if request.method == 'POST':
        form = PaymentForm(request.POST, admission=admission)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.admission = admission
            payment.received_by = request.user
            payment.save()
            log_action(request.user, 'payment', 'Payment', payment.pk, payment.receipt_number, details=f"Rs. {payment.amount} for {admission.admission_number}")
            messages.success(request, f'Payment {payment.receipt_number} recorded.')
            return redirect('admission_detail', pk=admission_id)
    else:
        form = PaymentForm(initial={'payment_date': date.today()})
    return render(request, 'fees/payment_form.html', {'form': form, 'admission': admission})


@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('admission__student', 'admission__university', 'admission__course', 'received_by'), pk=pk)
    return render(request, 'fees/payment_detail.html', {'payment': payment})


@login_required
def payment_void(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
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
def receipt_view(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('admission__student', 'admission__university', 'admission__course', 'received_by'), pk=pk)
    return render(request, 'fees/receipt.html', {'payment': payment})


@login_required
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
