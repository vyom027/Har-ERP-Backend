from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from .models import Inward, InwardItem
from .forms import InwardForm


@login_required
def inward_list(request):
    query = request.GET.get("q", "")
    inwards_list = Inward.objects.prefetch_related('items').all()

    if query:
        inwards_list = inwards_list.filter(
            Q(challan_no__icontains=query)
            | Q(delivery_party__icontains=query)
            | Q(buyer_party__icontains=query)
            | Q(article_no__icontains=query)
            | Q(items__roll_no__icontains=query)
        ).distinct()

    paginator = Paginator(inwards_list, 20)
    page_number = request.GET.get("page")
    inwards = paginator.get_page(page_number)

    return render(
        request, "inward/inward_list.html", {"inwards": inwards, "query": query}
    )


@login_required
def inward_create(request):
    if request.method == "POST":
        form = InwardForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                inward = form.save()
                
                # Handle items
                rolls = request.POST.getlist('roll_no[]')
                colors = request.POST.getlist('color[]')
                meters = request.POST.getlist('meters[]')
                
                for r, c, m in zip(rolls, colors, meters):
                    if r and m:
                        InwardItem.objects.create(inward=inward, roll_no=r, color=c, meters=m)
                
            return redirect("inward:inward_list")
    else:
        last_inward = Inward.objects.order_by("-sr_no").first()
        next_sr_no = (last_inward.sr_no + 1) if last_inward else 1
        form = InwardForm(initial={"sr_no": next_sr_no})

    return render(request, "inward/inward_form.html", {"form": form, "title": "Add Inward"})


@login_required
def inward_update(request, pk):
    inward = get_object_or_404(Inward, pk=pk)
    if request.method == "POST":
        form = InwardForm(request.POST, instance=inward)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                
                # Update items: Clear old and add new
                inward.items.all().delete()
                rolls = request.POST.getlist('roll_no[]')
                colors = request.POST.getlist('color[]')
                meters = request.POST.getlist('meters[]')
                
                for r, c, m in zip(rolls, colors, meters):
                    if r and m:
                        InwardItem.objects.create(inward=inward, roll_no=r, color=c, meters=m)
            return redirect("inward:inward_list")
    else:
        form = InwardForm(instance=inward)

    return render(
        request, "inward/inward_form.html", {"form": form, "title": "Edit Inward", "inward": inward}
    )


@login_required
def inward_delete(request, pk):
    inward = get_object_or_404(Inward, pk=pk)
    if request.method == "POST":
        inward.delete()
        return redirect("inward:inward_list")
    return render(request, "inward/inward_confirm_delete.html", {"inward": inward})
