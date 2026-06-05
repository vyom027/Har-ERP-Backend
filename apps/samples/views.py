from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from apps.core.models import Party
from apps.labor.models import Labor
from .models import Sample, SampleColor
from decimal import Decimal
import json

@login_required
def sample_list(request):
    search = request.GET.get('search', '')
    samples = Sample.objects.select_related('party', 'labor').prefetch_related('colors')
    
    if search:
        samples = samples.filter(
            Q(sample_name__icontains=search) |
            Q(party__name__icontains=search) |
            Q(labor__name__icontains=search) |
            Q(colors__color_name__icontains=search)
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
    existing_colors_json = "[]"
    if sample_id:
        existing_sample = get_object_or_404(Sample, id=sample_id)
        colors = [{'name': c.color_name, 'pieces': c.pieces} for c in existing_sample.colors.all()]
        existing_colors_json = json.dumps(colors)
        
    context = {
        'parties': parties,
        'labors': labors,
        'existing_sample': existing_sample,
        'existing_colors_json': existing_colors_json,
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
    
    # Handle dynamic colors breakdown
    color_names = request.POST.getlist('color_names[]')
    color_pieces = request.POST.getlist('color_pieces[]')
    
    if sample_id:
        sample = get_object_or_404(Sample, id=sample_id)
        sample.party_id = party_id
        sample.labor_id = labor_id
        sample.sample_name = sample_name
        sample.rate = rate
        sample.work_date = work_date
        sample.remarks = remarks
        sample.save()
        # Clean up existing colors for update
        sample.colors.all().delete()
    else:
        sample = Sample.objects.create(
            party_id=party_id,
            labor_id=labor_id,
            sample_name=sample_name,
            rate=rate,
            work_date=work_date,
            remarks=remarks
        )
    
    # Add new color rows
    total_pcs = 0
    for name, pcs in zip(color_names, color_pieces):
        if name and pcs:
            pieces = int(pcs)
            SampleColor.objects.create(
                sample=sample,
                color_name=name,
                pieces=pieces
            )
            total_pcs += pieces
            
    # Finalize totals
    sample.total_pieces = total_pcs
    sample.total_amount = total_pcs * sample.rate
    sample.save()
        
    return HttpResponse(status=204, headers={'HX-Trigger': 'sampleUpdated'})

@login_required
def delete_sample(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=400)
    
    sample_id = request.POST.get('sample_id')
    if sample_id:
        Sample.objects.filter(id=sample_id).delete()
        
    return HttpResponse(status=204, headers={'HX-Trigger': 'sampleUpdated'})
