from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from admissions.models import Admission
from .models import StudentDocument, DocumentType
from core.audit import log_action


@login_required
def document_overview(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = StudentDocument.objects.select_related('admission', 'admission__student', 'document_type', 'verified_by').all()
    if q:
        qs = qs.filter(admission__student__mobile__icontains=q)
    if status:
        qs = qs.filter(status=status)

    from collections import defaultdict
    grouped = defaultdict(lambda: {'student': None, 'admission': None, 'docs': []})
    for doc in qs:
        key = (doc.admission.student.pk, doc.admission.pk)
        grouped[key]['student'] = doc.admission.student
        grouped[key]['admission'] = doc.admission
        grouped[key]['docs'].append(doc)

    pending_count = StudentDocument.objects.filter(status='uploaded').count()
    verified_count = StudentDocument.objects.filter(status='verified').count()
    rejected_count = StudentDocument.objects.filter(status='rejected').count()
    return render(request, 'documents/overview.html', {
        'grouped': grouped.values(), 'q': q, 'status_filter': status,
        'pending_count': pending_count, 'verified_count': verified_count, 'rejected_count': rejected_count,
    })


@login_required
def document_list(request, admission_id):
    admission = get_object_or_404(Admission, pk=admission_id)
    docs = admission.documents.select_related('document_type').all()
    doc_types = DocumentType.objects.filter(is_active=True)
    existing_types = [d.document_type_id for d in docs]
    missing = doc_types.exclude(id__in=existing_types)
    return render(request, 'documents/list.html', {
        'admission': admission, 'documents': docs, 'missing_types': missing,
    })


@login_required
def document_upload(request, admission_id):
    admission = get_object_or_404(Admission, pk=admission_id)
    if request.method == 'POST':
        doc_type_id = request.POST.get('document_type')
        file = request.FILES.get('file')
        doc_type = get_object_or_404(DocumentType, pk=doc_type_id)
        doc, created = StudentDocument.objects.get_or_create(
            admission=admission, document_type=doc_type,
            defaults={'file': file, 'status': 'uploaded'}
        )
        if not created and file:
            doc.file = file
            doc.status = 'uploaded'
            doc.save()
        log_action(request.user, 'upload', 'Document', doc.pk, f"{doc_type.name} - {admission.admission_number}")
        messages.success(request, f'{doc_type.name} uploaded.')
    return redirect('document_list', admission_id=admission_id)


@login_required
def document_verify(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    doc = get_object_or_404(StudentDocument, pk=pk)
    doc.status = 'verified'
    doc.verified_by = request.user
    doc.verified_at = timezone.now()
    doc.save()
    log_action(request.user, 'verify', 'Document', doc.pk, f"{doc.document_type.name} - {doc.admission.admission_number}")
    messages.success(request, f'{doc.document_type.name} verified.')
    return redirect('document_list', admission_id=doc.admission_id)


@login_required
def document_reject(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    doc = get_object_or_404(StudentDocument, pk=pk)
    reason = request.POST.get('reason', '')
    doc.status = 'rejected'
    doc.rejection_reason = reason
    doc.verified_by = request.user
    doc.verified_at = timezone.now()
    doc.save()
    log_action(request.user, 'reject', 'Document', doc.pk, f"{doc.document_type.name} - {doc.admission.admission_number}", details=f"Reason: {reason}")
    messages.error(request, f'{doc.document_type.name} rejected.')
    return redirect('document_list', admission_id=doc.admission_id)
