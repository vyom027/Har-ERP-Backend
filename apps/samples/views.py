from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from apps.core.models import Party
from apps.labor.models import Labor
from .models import Sample
from decimal import Decimal
import json

@login_required
def sample_list(request):
    search = request.GET.get('search', '')
    samples = Sample.objects.select_related('party', 'labor')
    
    if search:
        samples = samples.filter(
            Q(sample_name__icontains=search) |
            Q(party__name__icontains=search) |
            Q(labor__name__icontains=search)
        ).distinct()
    
    context = {
        'samples': samples,
        'search': search,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'samples/partials/sample_table.html', context)
    
    return render(request, 'samples/list.html', context)

@login_required
def sample_modal(request):
    sample_id = request.GET.get('sample_id')
    parties = Party.objects.all().order_by('name')
    labors = Labor.objects.filter(active=True).order_by('name')
    
    existing_sample = None
    if sample_id:
        existing_sample = get_object_or_404(Sample, id=sample_id)
        
    context = {
        'parties': parties,
        'labors': labors,
        'existing_sample': existing_sample,
    }
    return render(request, 'samples/partials/modal_content.html', context)

@login_required
def save_sample(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=400)
        
    sample_id = request.POST.get('sample_id')
    party_id = request.POST.get('party_id')
    labor_id = request.POST.get('labor_id')
    sample_name = request.POST.get('sample_name')
    rate = Decimal(request.POST.get('rate') or '0.00')
    work_date = request.POST.get('work_date')
    remarks = request.POST.get('remarks', '')
    
    pieces = request.POST.get('pieces', '0')
    try:
        total_pieces = int(pieces)
    except ValueError:
        total_pieces = 0

    if sample_id:
        sample = get_object_or_404(Sample, id=sample_id)
        sample.party_id = party_id
        sample.labor_id = labor_id
        sample.sample_name = sample_name
        sample.total_pieces = total_pieces
        sample.rate = rate
        sample.work_date = work_date
        sample.remarks = remarks
        sample.save()
    else:
        sample = Sample.objects.create(
            party_id=party_id,
            labor_id=labor_id,
            sample_name=sample_name,
            total_pieces=total_pieces,
            rate=rate,
            work_date=work_date,
            remarks=remarks
        )
        
    return HttpResponse(status=204, headers={'HX-Trigger': 'sampleUpdated'})

@login_required
def delete_sample(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=400)
    
    sample_id = request.POST.get('sample_id')
    if sample_id:
        Sample.objects.filter(id=sample_id).delete()
        
    return HttpResponse(status=204, headers={'HX-Trigger': 'sampleUpdated'})
