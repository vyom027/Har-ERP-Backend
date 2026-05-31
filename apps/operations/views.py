from django.shortcuts import render
from .models import Operation

def op_list(request):
    ops = Operation.objects.all().prefetch_related('sub_operations')
    return render(request, 'operations/list.html', {'operations': ops})
