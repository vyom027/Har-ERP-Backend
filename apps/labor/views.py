from django.shortcuts import render, redirect, get_object_or_404
from .models import Labor, Payment
from apps.production.models import WorkEntry
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal

# ... (labor_list, labor_profile, add_labor remain the same)

@login_required
def labor_list(request):
    labors = Labor.objects.all()
    return render(request, 'labor/labor_list.html', {'labors': labors})

@login_required
def labor_profile(request, pk):
    labor = get_object_or_404(Labor, pk=pk)
    work = WorkEntry.objects.filter(labor=labor).select_related('lot', 'operation')
    payments = Payment.objects.filter(labor=labor)
    ledger = []
    for w in work:
        ledger.append({'date': w.work_date, 'type': 'Work', 'details': f"Lot {w.lot.lot_number} / {w.operation.name}", 'credit': w.total_amount, 'debit': 0})
    for p in payments:
        ledger.append({'date': p.payment_date, 'type': 'Payment', 'details': f"{p.get_payment_type_display()} - {p.note}", 'credit': 0, 'debit': p.amount})
    ledger.sort(key=lambda x: x['date'])
    running_balance = 0
    for item in ledger:
        running_balance += (item['credit'] - item['debit'])
        item['balance'] = running_balance
    return render(request, 'labor/labor_profile.html', {'labor': labor, 'ledger': reversed(ledger), 'total_earned': labor.total_earned, 'total_paid': labor.total_paid, 'pending': labor.pending_balance})

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
