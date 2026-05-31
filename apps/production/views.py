from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, IntegerField
from django.db.models.functions import Cast
from apps.operations.models import Operation, SubOperation
from apps.core.models import Lot, LotColor
from apps.production.models import WorkEntry
from apps.labor.models import Labor
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from decimal import Decimal, InvalidOperation
import json

@login_required
def production_table(request):
    sort = request.GET.get('sort', '-created_at')
    search = request.GET.get('search', '')
    status = request.GET.get('status', 'active')
    
    ops = Operation.objects.filter(active=True).prefetch_related('sub_operations')
    
    # Base Queryset
    lots_qs = Lot.objects.select_related('party').prefetch_related('colors')
    
    # Apply Status Filter
    if status and status != 'all':
        lots_qs = lots_qs.filter(status=status)
    
    # Apply Search Filter
    if search:
        lots_qs = lots_qs.filter(
            Q(lot_number__icontains=search) |
            Q(party__name__icontains=search)
        )
    
    # Sorting logic
    if sort == 'lot_asc':
        # Cast lot_number to integer for correct numerical sorting
        lots_qs = lots_qs.annotate(
            lot_num_int=Cast('lot_number', output_field=IntegerField())
        ).order_by('lot_num_int')
    elif sort == 'lot_desc':
        lots_qs = lots_qs.annotate(
            lot_num_int=Cast('lot_number', output_field=IntegerField())
        ).order_by('-lot_num_int')
    elif sort == 'party_asc':
        lots_qs = lots_qs.order_by('party__name')
    elif sort == 'party_desc':
        lots_qs = lots_qs.order_by('-party__name')
    else:
        lots_qs = lots_qs.order_by('-created_at')
        
    lots = lots_qs
    
    # Build Header Structure
    header_config = []
    for op in ops:
        if op.has_sub_operations:
            subs = op.sub_operations.all()
            header_config.append({
                'op': op,
                'subs': subs,
                'colspan': subs.count()
            })
        else:
            header_config.append({
                'op': op,
                'subs': [None],
                'colspan': 1
            })

    # Optimization: Filter entries only for the lots being shown
    lot_ids = [l.id for l in lots]
    entries_qs = WorkEntry.objects.filter(lot_id__in=lot_ids).select_related('labor', 'lot_color')
    
    # Mapping structure: entries[lot_id][op_id][sub_op_id or 0][color_id] = entry_object
    entries_map = {}
    for entry in entries_qs:
        l_id = entry.lot_id
        o_id = entry.operation_id
        s_id = entry.sub_operation_id or 0
        c_id = entry.lot_color_id
        
        if l_id not in entries_map: entries_map[l_id] = {}
        if o_id not in entries_map[l_id]: entries_map[l_id][o_id] = {}
        if s_id not in entries_map[l_id][o_id]: entries_map[l_id][o_id][s_id] = {}
        
        if c_id not in entries_map[l_id][o_id][s_id]:
            entries_map[l_id][o_id][s_id][c_id] = []
            
        entries_map[l_id][o_id][s_id][c_id].append(entry)

    context = {
        'header_config': header_config,
        'lots': lots,
        'entries_map': entries_map,
        'current_sort': sort,
        'search': search,
        'status': status,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'production/partials/table_full.html', context)
    
    return render(request, 'production/table.html', context)

@login_required
def entry_modal(request):
    lot_id = request.GET.get('lot_id')
    op_id = request.GET.get('op_id')
    sub_op_id = request.GET.get('sub_op_id')
    entry_id = request.GET.get('entry_id')
    
    lot = get_object_or_404(Lot, id=lot_id)
    operation = get_object_or_404(Operation, id=op_id)
    sub_operation = None
    if sub_op_id and sub_op_id != '0':
        sub_operation = get_object_or_404(SubOperation, id=sub_op_id)
    
    labors = Labor.objects.filter(active=True)
    
    # 1. Get the target entry
    existing_entry = None
    if entry_id:
        existing_entry = get_object_or_404(WorkEntry, id=entry_id)

    # Calculate limits for each color
    color_limits = {}
    
    # General (No Color)
    gen_total = lot.total_pieces
    # Allotted: total across all entries in this cell for this color (excluding the one we are currently editing)
    gen_allotted_qs = WorkEntry.objects.filter(
        lot=lot, 
        operation=operation, 
        sub_operation=sub_operation,
        lot_color__isnull=True
    )
    if existing_entry and existing_entry.lot_color_id is None:
        gen_allotted_qs = gen_allotted_qs.exclude(id=existing_entry.id)
    
    color_limits['all'] = {'total': gen_total, 'allotted': gen_allotted_qs.aggregate(Sum('pieces'))['pieces__sum'] or 0}
    
    for color in lot.colors.all():
        c_qs = WorkEntry.objects.filter(
            lot=lot, 
            operation=operation, 
            sub_operation=sub_operation,
            lot_color=color
        )
        if existing_entry and existing_entry.lot_color_id == color.id:
            c_qs = c_qs.exclude(id=existing_entry.id)
            
        color_limits[str(color.id)] = {'total': color.pieces, 'allotted': c_qs.aggregate(Sum('pieces'))['pieces__sum'] or 0}

    context = {
        'lot': lot,
        'operation': operation,
        'sub_operation': sub_operation,
        'labors': labors,
        'existing_entry': existing_entry,
        'color_limits': color_limits,
    }
    return render(request, 'production/modal_content.html', context)

@login_required
def quick_add_production(request):
    lots = Lot.objects.filter(status='active').order_by('-created_at')
    ops = Operation.objects.filter(active=True)
    labors = Labor.objects.filter(active=True)
    
    return render(request, 'production/quick_add_modal.html', {
        'lots': lots,
        'operations': ops,
        'labors': labors,
    })

@login_required
def get_lot_colors(request):
    lot_id = request.GET.get('lot_id')
    colors = LotColor.objects.filter(lot_id=lot_id)
    return render(request, 'production/partials/color_options.html', {'colors': colors})

@login_required
def get_lot_data(request):
    lot_id = request.GET.get('lot_id')
    if not lot_id:
        return JsonResponse({'colors': [], 'limits': {}})
        
    lot = get_object_or_404(Lot, id=lot_id)
    ops = Operation.objects.filter(active=True)
    
    colors_data = [{'id': str(c.id), 'name': c.color_name, 'pieces': c.pieces} for c in lot.colors.all()]
    
    limits = {}
    for op in ops:
        op_id_str = str(op.id)
        limits[op_id_str] = {}
        
        # General
        gen_entries = WorkEntry.objects.filter(lot=lot, operation=op, sub_operation__isnull=True, lot_color__isnull=True)
        alloted_all = sum(e.pieces for e in gen_entries)
        labor_map_all = {str(e.labor_id): e.pieces for e in gen_entries}
        limits[op_id_str]['all'] = {'total': lot.total_pieces, 'alloted': alloted_all, 'labor_map': labor_map_all}
        
        for c in lot.colors.all():
            c_entries = WorkEntry.objects.filter(lot=lot, operation=op, sub_operation__isnull=True, lot_color=c)
            alloted_c = sum(e.pieces for e in c_entries)
            labor_map_c = {str(e.labor_id): e.pieces for e in c_entries}
            limits[op_id_str][str(c.id)] = {'total': c.pieces, 'alloted': alloted_c, 'labor_map': labor_map_c}
            
    return JsonResponse({'colors': colors_data, 'limits': limits})

@login_required
def save_entry(request):
    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        lot_id = request.POST.get('lot_id')
        op_id = request.POST.get('op_id')
        sub_op_id = request.POST.get('sub_op_id')
        color_id = request.POST.get('color_id')
        labor_id = request.POST.get('labor_id')
        pieces = request.POST.get('pieces')
        size = request.POST.get('size')
        rate_str = request.POST.get('rate')
        work_date = request.POST.get('work_date')
        remarks = request.POST.get('remarks', '')

        try:
            rate = Decimal(str(rate_str))
        except (InvalidOperation, ValueError):
            rate = Decimal('0.00')

        # Handle optional color
        lot_color_id = color_id if color_id and color_id != 'all' else None
        sub_op_id_val = sub_op_id if sub_op_id and sub_op_id != '0' else None
        pieces_val = int(pieces or 0)
        
        # Validation: Check if pieces exceed capacity
        allotted_query = WorkEntry.objects.filter(
            lot_id=lot_id,
            operation_id=op_id,
            sub_operation_id=sub_op_id_val,
            lot_color_id=lot_color_id
        )
        
        if entry_id:
            allotted_query = allotted_query.exclude(id=entry_id)
        
        allotted = allotted_query.aggregate(Sum('pieces'))['pieces__sum'] or 0
        
        if lot_color_id:
            total_capacity = LotColor.objects.get(id=lot_color_id).pieces
        else:
            total_capacity = Lot.objects.get(id=lot_id).total_pieces
            
        if (allotted + pieces_val) > total_capacity:
            print(f"ERROR: Capacity exceeded! Total:{total_capacity}, Allotted:{allotted}, New:{pieces_val}")

        # Targeted Update or Create
        if entry_id:
            entry = get_object_or_404(WorkEntry, id=entry_id)
            entry.labor_id = labor_id
            entry.lot_color_id = lot_color_id
            entry.size = size
            entry.pieces = pieces_val
            entry.rate = rate
            entry.work_date = work_date
            entry.remarks = remarks
            entry.save()
        else:
            entry = WorkEntry.objects.create(
                lot_id=lot_id,
                operation_id=op_id,
                sub_operation_id=sub_op_id_val,
                lot_color_id=lot_color_id,
                labor_id=labor_id,
                size=size,
                pieces=pieces_val,
                rate=rate,
                work_date=work_date,
                remarks=remarks
            )
        
        # Re-fetch lot and all entries for this specific cell to render correctly
        lot = Lot.objects.prefetch_related('colors').get(id=lot_id)
        cell_entries = WorkEntry.objects.filter(
            lot_id=lot_id, 
            operation_id=op_id, 
            sub_operation_id=sub_op_id_val
        ).select_related('labor')
        
        color_map = {}
        for e in cell_entries:
            if e.lot_color_id not in color_map: color_map[e.lot_color_id] = []
            color_map[e.lot_color_id].append(e)

        return render(request, 'production/partials/table_cell.html', {
            'lot': lot,
            'op_id': int(op_id),
            'sub_id': int(sub_op_id or 0),
            'color_map': color_map
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_entry(request):
    if request.method == 'POST':
        lot_id = request.POST.get('lot_id')
        op_id = request.POST.get('op_id')
        sub_op_id = request.POST.get('sub_op_id')
        color_id = request.POST.get('color_id')
        
        # Handle optional color
        lot_color_id = color_id if color_id and color_id != 'all' else None
        sub_operation_id = sub_op_id if sub_op_id and sub_op_id != '0' else None

        WorkEntry.objects.filter(
            lot_id=lot_id,
            operation_id=op_id,
            sub_operation_id=sub_operation_id,
            lot_color_id=lot_color_id
        ).delete()
        
        # Re-render cell
        lot = Lot.objects.prefetch_related('colors').get(id=lot_id)
        cell_entries = WorkEntry.objects.filter(
            lot_id=lot_id, 
            operation_id=op_id, 
            sub_operation_id=sub_operation_id
        ).select_related('labor')
        
        color_map = {}
        for e in cell_entries:
            if e.lot_color_id not in color_map: color_map[e.lot_color_id] = []
            color_map[e.lot_color_id].append(e)

        return render(request, 'production/partials/table_cell.html', {
            'lot': lot,
            'op_id': int(op_id),
            'sub_id': int(sub_op_id or 0),
            'color_map': color_map
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def get_last_rate(request):
    labor_id = request.GET.get('labor_id')
    op_id = request.GET.get('op_id')
    
    last_entry = WorkEntry.objects.filter(labor_id=labor_id, operation_id=op_id).order_by('-created_at').first()
    rate = last_entry.rate if last_entry else 0
    return HttpResponse(str(rate))

def op_list(request):
    ops = Operation.objects.all()
    return render(request, 'operations/list.html', {'operations': ops})
