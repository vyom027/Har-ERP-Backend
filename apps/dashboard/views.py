from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Lot
from apps.production.models import WorkEntry
from apps.labor.models import Labor, Payment
import json
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    today = timezone.now().date()

    # Stats
    active_production = (
        Lot.objects.filter(status="active").aggregate(total=Sum("total_pieces"))[
            "total"
        ]
        or 0
    )

    active_lots = Lot.objects.filter(status="active").count()
    total_labor_expense = (
        WorkEntry.objects.aggregate(total=Sum("total_amount"))["total"] or 0
    )
    total_paid = Payment.objects.aggregate(total=Sum("amount"))["total"] or 0
    pending_payments = total_labor_expense - total_paid

    # Charts Data
    # 1. Top 5 Workers
    top_workers_query = (
        WorkEntry.objects.values("labor__name")
        .annotate(earned=Sum("total_amount"))
        .order_by("-earned")[:5]
    )
    top_workers = {
        "labels": [w["labor__name"] for w in top_workers_query],
        "data": [float(w["earned"]) for w in top_workers_query],
    }

    # 2. Daily Production (Last 30 days)
    last_30_days = today - timedelta(days=29)
    daily_prod_query = (
        WorkEntry.objects.filter(work_date__gte=last_30_days)
        .values("work_date")
        .annotate(count=Sum("pieces"))
        .order_by("work_date")
    )
    daily_prod = {
        "labels": [d["work_date"].strftime("%d %b") for d in daily_prod_query],
        "data": [d["count"] for d in daily_prod_query],
    }

    # 3. Operation-wise breakdown
    op_breakdown_query = (
        WorkEntry.objects.values("operation__name")
        .annotate(cost=Sum("total_amount"))
        .order_by("-cost")
    )
    op_breakdown = {
        "labels": [o["operation__name"] for o in op_breakdown_query],
        "data": [float(o["cost"]) for o in op_breakdown_query],
    }

    context = {
        "stats": {
            "active_production": active_production,
            "active_lots": active_lots,
            "total_expense": total_labor_expense,
            "pending_payments": pending_payments,
        },
        "charts": {
            "top_workers": json.dumps(top_workers),
            "daily_prod": json.dumps(daily_prod),
            "op_breakdown": json.dumps(op_breakdown),
        },
        "recent_entries": WorkEntry.objects.select_related(
            "lot", "labor", "operation"
        ).order_by("-created_at")[:10],
        "recent_payments": Payment.objects.select_related("labor").order_by(
            "-created_at"
        )[:5],
    }
    return render(request, "dashboard/home.html", context)
