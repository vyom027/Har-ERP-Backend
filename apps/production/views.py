from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, IntegerField
from django.db.models.functions import Cast
from django.core.paginator import Paginator
from apps.operations.models import Operation, SubOperation
from apps.core.models import Lot, LotColor
from apps.production.models import WorkEntry
from apps.labor.models import Labor
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from decimal import Decimal, InvalidOperation
import json
import base64

@login_required
def production_table(request):
    sort = request.GET.get('sort', '-created_at')
    search = request.GET.get('search', '')
    status = request.GET.get('status', 'active')
    page = request.GET.get('page', 1)
    party_id = request.GET.get('party_id')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    ops = Operation.objects.filter(active=True).prefetch_related('sub_operations')

    # Base Queryset
    lots_qs = Lot.objects.select_related('party').prefetch_related('colors')

    # Apply Party Filter
    from apps.core.models import Party
    party = None
    if party_id:
        party = get_object_or_404(Party, id=party_id)
        lots_qs = lots_qs.filter(party_id=party_id)

    # Apply Date Range Filter (on lot creation date)
    if start_date:
        lots_qs = lots_qs.filter(created_at__date__gte=start_date)
    if end_date:
        lots_qs = lots_qs.filter(created_at__date__lte=end_date)

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
        
    # Paginate
    paginator = Paginator(lots_qs, 20)
    page_obj = paginator.get_page(page)
    
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

    # Optimization: Filter entries only for the lots being shown on this page
    lot_ids = [l.id for l in page_obj]
    entries_qs = WorkEntry.objects.filter(lot_id__in=lot_ids).select_related('labor', 'lot_color')
    
    # Mapping structure: entries[lot_id][op_id][sub_op_id or 0][color_id or 0] = entry_object
    entries_map = {}
    for entry in entries_qs:
        l_id = entry.lot_id
        o_id = entry.operation_id
        s_id = entry.sub_operation_id or 0
        c_id = entry.lot_color_id or 0
        
        if l_id not in entries_map: entries_map[l_id] = {}
        if o_id not in entries_map[l_id]: entries_map[l_id][o_id] = {}
        if s_id not in entries_map[l_id][o_id]: entries_map[l_id][o_id][s_id] = {}
        
        if c_id not in entries_map[l_id][o_id][s_id]:
            entries_map[l_id][o_id][s_id][c_id] = []
            
        entries_map[l_id][o_id][s_id][c_id].append(entry)

    context = {
        'header_config': header_config,
        'lots': page_obj,
        'page_obj': page_obj,
        'entries_map': entries_map,
        'current_sort': sort,
        'search': search,
        'status': status,
        'party_id': party_id,
        'party': party,
        'start_date': start_date,
        'end_date': end_date,
        'parties': Party.objects.order_by('name'),
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
    initial_color_id = request.GET.get('color_id', '0') # Standardized 0 for General
    
    lot = get_object_or_404(Lot, id=lot_id)
    operation = get_object_or_404(Operation, id=op_id)
    sub_operation = None
    if sub_op_id and sub_op_id != '0':
        sub_operation = get_object_or_404(SubOperation, id=sub_op_id)
    
    labors = Labor.objects.filter(active=True)
    
    existing_entry = None
    if entry_id:
        existing_entry = get_object_or_404(WorkEntry, id=entry_id)
        initial_color_id = str(existing_entry.lot_color_id or '0')

    # Calculate limits for each color
    color_limits = {}
    
    # General (Key 0)
    gen_total = lot.total_pieces
    gen_qs = WorkEntry.objects.filter(lot=lot, operation=operation, sub_operation=sub_operation, lot_color__isnull=True)
    if existing_entry and existing_entry.lot_color_id is None:
        gen_qs = gen_qs.exclude(id=existing_entry.id)
    
    color_limits['0'] = {'total': gen_total, 'allotted': gen_qs.aggregate(Sum('pieces'))['pieces__sum'] or 0}
    
    for color in lot.colors.all():
        c_qs = WorkEntry.objects.filter(lot=lot, operation=operation, sub_operation=sub_operation, lot_color=color)
        if existing_entry and existing_entry.lot_color_id == color.id:
            c_qs = c_qs.exclude(id=existing_entry.id)
        color_limits[str(color.id)] = {'total': color.pieces, 'allotted': c_qs.aggregate(Sum('pieces'))['pieces__sum'] or 0}

    context = {
        'lot': lot,
        'operation': operation,
        'sub_operation': sub_operation,
        'labors': labors,
        'existing_entry': existing_entry,
        'color_limits_b64': base64.b64encode(json.dumps(color_limits).encode()).decode(),
        'initial_color_id': initial_color_id,
    }
    return render(request, 'production/modal_content.html', context)

@login_required
def quick_add_production(request):
    lots = Lot.objects.filter(status='active').order_by('-created_at')
    ops = Operation.objects.filter(active=True)
    labors = Labor.objects.filter(active=True)
    return render(request, 'production/quick_add_modal.html', {'lots': lots, 'operations': ops, 'labors': labors})

@login_required
def get_lot_colors(request):
    lot_id = request.GET.get('lot_id')
    colors = LotColor.objects.filter(lot_id=lot_id)
    return render(request, 'production/partials/color_options.html', {'colors': colors})

@login_required
def get_lot_data(request):
    lot_id = request.GET.get('lot_id')
    if not lot_id: return JsonResponse({'colors': [], 'limits': {}})
    lot = get_object_or_404(Lot, id=lot_id)
    ops = Operation.objects.filter(active=True)
    colors_data = [{'id': str(c.id), 'name': c.color_name, 'pieces': c.pieces} for c in lot.colors.all()]
    limits = {}
    for op in ops:
        op_id_str = str(op.id)
        limits[op_id_str] = {}
        # Use key 0 for General
        gen_entries = WorkEntry.objects.filter(lot=lot, operation=op, sub_operation__isnull=True, lot_color__isnull=True)
        limits[op_id_str]['0'] = {'total': lot.total_pieces, 'allotted': sum(e.pieces for e in gen_entries), 'labor_map': {str(e.labor_id): e.pieces for e in gen_entries}}
        for c in lot.colors.all():
            c_entries = WorkEntry.objects.filter(lot=lot, operation=op, sub_operation__isnull=True, lot_color=c)
            limits[op_id_str][str(c.id)] = {'total': c.pieces, 'allotted': sum(e.pieces for e in c_entries), 'labor_map': {str(e.labor_id): e.pieces for e in c_entries}}
    return JsonResponse({'colors': colors_data, 'limits': limits})

@login_required
def save_entry(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'}, status=400)
    entry_id = request.POST.get('entry_id')
    lot_id = request.POST.get('lot_id')
    op_id = request.POST.get('op_id')
    sub_op_id = request.POST.get('sub_op_id')
    color_id = request.POST.get('color_id')
    labor_id = request.POST.get('labor_id')
    pieces_val = int(request.POST.get('pieces') or 0)
    size = request.POST.get('size')
    rate = Decimal(request.POST.get('rate') or '0.00')
    work_date = request.POST.get('work_date')
    remarks = request.POST.get('remarks', '')

    lot_color_id = color_id if color_id and color_id != '0' else None
    sub_op_id_val = sub_op_id if sub_op_id and sub_op_id != '0' else None
    
    # Capacity Check
    allotted_query = WorkEntry.objects.filter(lot_id=lot_id, operation_id=op_id, sub_operation_id=sub_op_id_val, lot_color_id=lot_color_id)
    if entry_id: allotted_query = allotted_query.exclude(id=entry_id)
    allotted = allotted_query.aggregate(Sum('pieces'))['pieces__sum'] or 0
    total_capacity = LotColor.objects.get(id=lot_color_id).pieces if lot_color_id else Lot.objects.get(id=lot_id).total_pieces
    
    if (allotted + pieces_val) > total_capacity:
        return HttpResponse(f"Capacity exceeded! Allowed: {total_capacity}, Used: {allotted}", status=400)

    if entry_id:
        entry = get_object_or_404(WorkEntry, id=entry_id)
        entry.labor_id, entry.lot_color_id, entry.size, entry.pieces, entry.rate, entry.work_date, entry.remarks = labor_id, lot_color_id, size, pieces_val, rate, work_date, remarks
        entry.save()
    else:
        WorkEntry.objects.create(lot_id=lot_id, operation_id=op_id, sub_operation_id=sub_op_id_val, lot_color_id=lot_color_id, labor_id=labor_id, size=size, pieces=pieces_val, rate=rate, work_date=work_date, remarks=remarks)
    
    lot = Lot.objects.prefetch_related('colors').get(id=lot_id)
    cell_entries = WorkEntry.objects.filter(lot_id=lot_id, operation_id=op_id, sub_operation_id=sub_op_id_val).select_related('labor')
    color_map = {}
    for e in cell_entries:
        cid = e.lot_color_id or 0
        if cid not in color_map: color_map[cid] = []
        color_map[cid].append(e)

    return render(request, 'production/partials/table_cell.html', {'lot': lot, 'op_id': int(op_id), 'sub_id': int(sub_op_id or 0), 'color_map': color_map})

@login_required
def delete_entry(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'}, status=400)
    entry_id, lot_id, op_id, sub_op_id = request.POST.get('entry_id'), request.POST.get('lot_id'), request.POST.get('op_id'), request.POST.get('sub_op_id')
    sub_operation_id = sub_op_id if sub_op_id and sub_op_id != '0' else None
    if entry_id: WorkEntry.objects.filter(id=entry_id).delete()
    
    lot = Lot.objects.prefetch_related('colors').get(id=lot_id)
    cell_entries = WorkEntry.objects.filter(lot_id=lot_id, operation_id=op_id, sub_operation_id=sub_operation_id).select_related('labor')
    color_map = {}
    for e in cell_entries:
        cid = e.lot_color_id or 0
        if cid not in color_map: color_map[cid] = []
        color_map[cid].append(e)

    return render(request, 'production/partials/table_cell.html', {'lot': lot, 'op_id': int(op_id), 'sub_id': int(sub_op_id or 0), 'color_map': color_map})

@login_required
def get_last_rate(request):
    labor_id, op_id = request.GET.get('labor_id'), request.GET.get('op_id')
    last_entry = WorkEntry.objects.filter(labor_id=labor_id, operation_id=op_id).order_by('-created_at').first()
    return HttpResponse(str(last_entry.rate if last_entry else 0))

def op_list(request):
    return render(request, 'operations/list.html', {'operations': Operation.objects.all()})
