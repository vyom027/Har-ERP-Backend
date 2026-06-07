from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Operation

def op_list(request):
    ops = Operation.objects.all().prefetch_related('sub_operations')
    return render(request, 'operations/list.html', {'operations': ops})

@login_required
@require_POST
def update_operation_name(request):
    op_id = request.POST.get('id')
    new_name = request.POST.get('name')
    if not op_id or not new_name:
        return HttpResponse("Invalid data", status=400)
    
    op = get_object_or_404(Operation, id=op_id)
    op.name = new_name
    op.save()
    return HttpResponse(op.name)
