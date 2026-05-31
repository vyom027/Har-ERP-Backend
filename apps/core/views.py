from django.shortcuts import render, redirect, get_object_or_404
from django.db import models as models
from .models import Lot, Party, LotColor
from django.contrib.auth.decorators import login_required
from django.db import transaction

@login_required
def add_party(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        notes = request.POST.get('notes')
        
        Party.objects.create(
            name=name,
            phone=phone,
            address=address,
            notes=notes
        )
        return redirect('core:lot_list')
    return render(request, 'core/add_party.html')

@login_required
def lot_list(request):
    lots = Lot.objects.select_related('party').prefetch_related('colors').order_by('-created_at')
    return render(request, 'core/lot_list.html', {'lots': lots})

@login_required
def lot_detail(request):
    # Handled by PKR
    pass

@login_required
def add_lot(request):
    if request.method == 'POST':
        with transaction.atomic():
            party_id = request.POST.get('party_id')
            lot_number = request.POST.get('lot_number')
            total_pieces = request.POST.get('total_pieces')
            remarks = request.POST.get('remarks')
            
            lot = Lot.objects.create(
                party_id=party_id,
                lot_number=lot_number,
                total_pieces=total_pieces,
                remarks=remarks
            )
            
            colors = request.POST.getlist('colors[]')
            pieces = request.POST.getlist('pieces[]')
            
            for c, p in zip(colors, pieces):
                if c and p:
                    LotColor.objects.create(lot=lot, color_name=c, pieces=p)
            
            return redirect('core:lot_list')
            
    parties = Party.objects.all()
    return render(request, 'core/add_lot.html', {'parties': parties})

@login_required
def lot_detail(request, pk):
    lot = get_object_or_404(Lot.objects.select_related('party').prefetch_related('colors'), pk=pk)
    return render(request, 'core/lot_detail.html', {'lot': lot})

@login_required
def edit_lot(request, pk):
    lot = get_object_or_404(Lot, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            lot.party_id = request.POST.get('party_id')
            lot.lot_number = request.POST.get('lot_number')
            lot.total_pieces = request.POST.get('total_pieces')
            lot.remarks = request.POST.get('remarks')
            lot.status = request.POST.get('status')
            lot.save()
            
            # Update colors: Clear old and add new
            lot.colors.all().delete()
            colors = request.POST.getlist('colors[]')
            pieces = request.POST.getlist('pieces[]')
            
            for c, p in zip(colors, pieces):
                if c and p:
                    LotColor.objects.create(lot=lot, color_name=c, pieces=p)
            
            return redirect('core:lot_detail', pk=lot.pk)
            
    parties = Party.objects.all()
    return render(request, 'core/edit_lot.html', {'lot': lot, 'parties': parties})

@login_required
def delete_lot(request, pk):
    lot = get_object_or_404(Lot, pk=pk)
    if request.method == 'POST':
        lot.delete()
        return redirect('core:lot_list')
    return redirect('core:lot_detail', pk=pk)

@login_required
def party_list(request):
    parties = Party.objects.annotate(lot_count=models.Count('lot')).order_by('name')
    return render(request, 'core/party_list.html', {'parties': parties})

@login_required
def edit_party(request, pk):
    party = get_object_or_404(Party, pk=pk)
    if request.method == 'POST':
        party.name = request.POST.get('name')
        party.phone = request.POST.get('phone')
        party.address = request.POST.get('address')
        party.notes = request.POST.get('notes')
        party.save()
        return redirect('core:party_list')
    return render(request, 'core/edit_party.html', {'party': party})

@login_required
def delete_party(request, pk):
    party = get_object_or_404(Party, pk=pk)
    if request.method == 'POST':
        party.delete()
        return redirect('core:party_list')
    return redirect('core:party_list')
