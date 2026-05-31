from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from .models import Labor, Payment
from apps.production.models import WorkEntry
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
from datetime import timedelta
from xhtml2pdf import pisa
from django.template.loader import get_template
import io
import hashlib
from django.conf import settings

def get_labor_token(labor):
    """Generate a stable, secure token for a worker without DB changes."""
    hash_input = f"{labor.id}{labor.name}{settings.SECRET_KEY}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

def get_ledger_data(labor, start_date=None, end_date=None):
    # Calculate Opening Balance
    opening_earned = 0
    opening_paid = 0
    if start_date:
        opening_earned = WorkEntry.objects.filter(labor=labor, work_date__lt=start_date).aggregate(total=Sum('total_amount'))['total'] or 0
        opening_paid = Payment.objects.filter(labor=labor, payment_date__lt=start_date).aggregate(total=Sum('amount'))['total'] or 0
    
    opening_balance = opening_earned - opening_paid

    work_qs = WorkEntry.objects.filter(labor=labor).select_related('lot', 'operation')
    payment_qs = Payment.objects.filter(labor=labor)
    
    if start_date:
        work_qs = work_qs.filter(work_date__gte=start_date)
        payment_qs = payment_qs.filter(payment_date__gte=start_date)
    if end_date:
        work_qs = work_qs.filter(work_date__lte=end_date)
        payment_qs = payment_qs.filter(payment_date__lte=end_date)
        
    ledger = []
    total_credit = 0
    total_debit = 0
    
    for w in work_qs:
        total_credit += w.total_amount
        ledger.append({
            'date': w.work_date, 
            'type': 'Work', 
            'details': f"Lot {w.lot.lot_number} / {w.operation.name}", 
            'credit': w.total_amount, 
            'debit': 0,
            'lot_number': w.lot.lot_number,
            'pieces': w.pieces,
            'rate': w.rate
        })
    for p in payment_qs:
        total_debit += p.amount
        ledger.append({
            'date': p.payment_date, 
            'type': 'Payment', 
            'details': f"{p.get_payment_type_display()} - {p.note}", 
            'credit': 0, 
            'debit': p.amount,
            'lot_number': '-',
            'pieces': '-',
            'rate': '-'
        })
        
    ledger.sort(key=lambda x: x['date'])
    
    running_balance = opening_balance
    for item in ledger:
        running_balance += (item['credit'] - item['debit'])
        item['balance'] = running_balance
        
    return ledger, opening_balance, running_balance, total_credit, total_debit

@login_required
def labor_list(request):
    labors = Labor.objects.all()
    return render(request, 'labor/labor_list.html', {'labors': labors})

@login_required
def labor_profile(request, pk):
    labor = get_object_or_404(Labor, pk=pk)
    
    # Filter Logic
    period = request.GET.get('period', 'all')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = timezone.now().date()
    
    if period == 'today':
        start_date = end_date
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == '10days':
        start_date = end_date - timedelta(days=10)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    ledger, opening_balance, final_balance, period_earned, period_paid = get_ledger_data(labor, start_date, end_date)
    
    # Construct WhatsApp URL with Public Share Link
    domain = request.build_absolute_uri('/')[:-1]
    share_token = get_labor_token(labor)
    # Ensure there is a proper ? separator
    share_path = reverse('labor:public_pdf', kwargs={'pk': labor.id, 'token': share_token})
    share_url = f"{domain}{share_path}?period={period}&start_date={start_date_str or ''}&end_date={end_date_str or ''}"
    
    share_msg = f"Hi {labor.name}, here is your work report ({period}).\n\n*Summary:*\nTotal Earned: Rs. {period_earned}\nTotal Paid: Rs. {period_paid}\nTotal Pending: Rs. {labor.pending_balance}\n\n*Download PDF Report:*\n{share_url}"
    
    import urllib.parse
    # Use quote to encode the message for the URL
    safe_msg = urllib.parse.quote(share_msg)
    wa_share_url = f"https://wa.me/{labor.phone.replace(' ', '').replace('-', '')}?text={safe_msg}"

    context = {
        'labor': labor, 
        'ledger': reversed(ledger), 
        'opening_balance': opening_balance,
        'final_balance': final_balance,
        'total_earned': labor.total_earned, 
        'total_paid': labor.total_paid, 
        'pending': labor.pending_balance,
        'period_earned': period_earned,
        'period_paid': period_paid,
        'current_period': period,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'wa_url': wa_share_url,
    }
    return render(request, 'labor/labor_profile.html', context)

def public_labor_pdf(request, pk, token):
    """Publicly accessible view for downloading a worker's PDF."""
    labor = get_object_or_404(Labor, pk=pk)
    
    # Verify Token
    if token != get_labor_token(labor):
        return HttpResponse("Invalid or expired sharing link.", status=403)
    
    # Filter Logic (Same as export_labor_pdf)
    period = request.GET.get('period', 'all')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = timezone.now().date()
    
    if period == 'today':
        start_date = end_date
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == '10days':
        start_date = end_date - timedelta(days=10)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    ledger, opening_balance, final_balance, period_earned, period_paid = get_ledger_data(labor, start_date, end_date)
    
    context = {
        'labor': labor,
        'ledger': ledger,
        'opening_balance': opening_balance,
        'final_balance': final_balance,
        'period_earned': period_earned,
        'period_paid': period_paid,
        'total_earned': labor.total_earned,
        'total_paid': labor.total_paid,
        'total_pending': labor.pending_balance,
        'current_period': period,
        'start_date': start_date or "Beginning",
        'end_date': end_date,
        'generated_at': timezone.now(),
    }
    
    # Render PDF
    html = get_template('labor/labor_ledger_pdf.html').render(context)
    result = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    filename = f"Report_{labor.name}_{timezone.now().strftime('%Y-%m-%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def export_labor_pdf(request, pk):
    labor = get_object_or_404(Labor, pk=pk)
    
    # Filter Logic (Same as profile)
    period = request.GET.get('period', 'all')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = timezone.now().date()
    
    if period == 'today':
        start_date = end_date
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == '10days':
        start_date = end_date - timedelta(days=10)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    ledger, opening_balance, final_balance, period_earned, period_paid = get_ledger_data(labor, start_date, end_date)
    
    context = {
        'labor': labor,
        'ledger': ledger,
        'opening_balance': opening_balance,
        'final_balance': final_balance,
        'period_earned': period_earned,
        'period_paid': period_paid,
        'total_earned': labor.total_earned,
        'total_paid': labor.total_paid,
        'total_pending': labor.pending_balance,
        'current_period': period,
        'start_date': start_date or "Beginning",
        'end_date': end_date,
        'generated_at': timezone.now(),
    }
    
    # Render PDF
    html = get_template('labor/labor_ledger_pdf.html').render(context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"Ledger_{labor.name}_{timezone.now().strftime('%Y-%m-%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

@login_required
def add_labor(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        Labor.objects.create(name=name, phone=phone)
        return redirect('labor:labor_list')
    return render(request, 'labor/add_labor.html')

@login_required
def payment_list(request):
    payments = Payment.objects.select_related('labor').order_by('-payment_date', '-created_at')
    return render(request, 'labor/payment_list.html', {'payments': payments})

@login_required
def add_payment(request):
    if request.method == 'POST':
        labor_id = request.POST.get('labor_id')
        amount = Decimal(request.POST.get('amount') or 0)
        payment_date = request.POST.get('payment_date')
        payment_type = request.POST.get('payment_type')
        note = request.POST.get('note')
        
        labor = get_object_or_404(Labor, id=labor_id)
        
        # Validation: Don't allow payment if it exceeds pending balance
        if amount > labor.pending_balance:
            messages.error(request, f"Error: Cannot pay ₹{amount}. Worker balance is only ₹{labor.pending_balance}.")
            labors = Labor.objects.filter(active=True)
            return render(request, 'labor/add_payment.html', {'labors': labors, 'selected_labor': labor})

        if amount <= 0:
            messages.error(request, "Error: Amount must be greater than zero.")
            labors = Labor.objects.filter(active=True)
            return render(request, 'labor/add_payment.html', {'labors': labors})

        Payment.objects.create(
            labor=labor,
            amount=amount,
            payment_date=payment_date,
            payment_type=payment_type,
            note=note
        )
        messages.success(request, f"Payment of ₹{amount} recorded for {labor.name}.")
        return redirect('labor:payment_list')
        
    labors = Labor.objects.filter(active=True)
    return render(request, 'labor/add_payment.html', {'labors': labors})

@login_required
def edit_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount') or 0)
        # For simplicity in edit, we just update. 
        # But we check validation again.
        if amount > (payment.labor.pending_balance + payment.amount):
             messages.error(request, "Error: Updated amount exceeds worker's available balance.")
        else:
            payment.amount = amount
            payment.payment_date = request.POST.get('payment_date')
            payment.note = request.POST.get('note')
            payment.save()
            messages.success(request, "Payment updated successfully.")
            return redirect('labor:payment_list')

    return render(request, 'labor/edit_payment.html', {'payment': payment})

@login_required
def delete_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        amount = payment.amount
        worker_name = payment.labor.name
        payment.delete()
        messages.warning(request, f"Payment of ₹{amount} for {worker_name} has been deleted.")
    return redirect('labor:payment_list')

@login_required
def delete_labor(request, pk):
    labor = get_object_or_404(Labor, pk=pk)
    if request.method == 'POST':
        name = labor.name
        # Optional: Check if there's history and maybe just deactivate instead?
        # But if the user explicitly wants to remove, we follow.
        labor.delete()
        messages.warning(request, f"Worker {name} and all their records have been removed.")
        return redirect('labor:labor_list')
    return redirect('labor:labor_list')
