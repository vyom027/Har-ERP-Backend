from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from apps.labor.models import Labor, LaborSetupToken, normalize_mobile
from apps.labor.views import get_ledger_data
from apps.production.models import WorkEntry
from apps.samples.models import Sample
from .decorators import worker_required
from . import throttle


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


# ---------------------------------------------------------------------------
# PIN setup (token-gated, public)
# ---------------------------------------------------------------------------
def setup(request, token):
    tok = LaborSetupToken.resolve(token)
    if tok is None:
        return render(request, 'portal/setup_invalid.html', status=400)

    labor = tok.labor
    ip = _client_ip(request)

    if request.method == 'POST':
        if throttle.is_locked('setup', ip):
            return render(request, 'portal/setup.html', {
                'labor': labor, 'token': token,
                'error': 'Too many attempts. Try again in a few minutes.',
            }, status=429)

        pin = (request.POST.get('pin') or '').strip()
        confirm = (request.POST.get('pin_confirm') or '').strip()

        if not (pin.isdigit() and len(pin) == 4):
            throttle.register_failure('setup', ip)
            return render(request, 'portal/setup.html', {
                'labor': labor, 'token': token,
                'error': 'PIN must be exactly 4 digits.',
            })
        if pin != confirm:
            return render(request, 'portal/setup.html', {
                'labor': labor, 'token': token,
                'error': 'PINs do not match. Try again.',
            })

        username = labor.login_mobile
        if not username:
            return render(request, 'portal/setup.html', {
                'labor': labor, 'token': token,
                'error': 'No mobile number on file. Contact the admin.',
            })

        # Reuse an existing linked user, else create one keyed by mobile.
        user = labor.user
        if user is None:
            # Guard against a stray username collision
            if User.objects.filter(username=username).exclude(labor_profile=labor).exists():
                return render(request, 'portal/setup.html', {
                    'labor': labor, 'token': token,
                    'error': 'This mobile is already in use. Contact the admin.',
                })
            user = User.objects.create(username=username, is_staff=False)
            labor.user = user

        user.set_password(pin)          # bypasses NumericPasswordValidator by design
        user.is_active = True
        user.save()

        worker_group, _ = Group.objects.get_or_create(name='Worker')
        user.groups.add(worker_group)

        labor.is_activated = True
        labor.login_enabled = True
        labor.save(update_fields=['user', 'is_activated', 'login_enabled'])

        tok.consume()
        throttle.reset('setup', ip)
        return render(request, 'portal/setup_done.html', {'labor': labor})

    return render(request, 'portal/setup.html', {'labor': labor, 'token': token})


# ---------------------------------------------------------------------------
# Worker login
# ---------------------------------------------------------------------------
def portal_login(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('portal:home')

    if request.method == 'POST':
        mobile = normalize_mobile(request.POST.get('mobile'))
        pin = (request.POST.get('pin') or '').strip()
        ip = _client_ip(request)

        if throttle.is_locked('login', mobile) or throttle.is_locked('login', ip):
            return render(request, 'portal/login.html', {
                'error': 'Too many attempts. Try again in a few minutes.',
                'mobile': mobile,
            }, status=429)

        user = authenticate(request, username=mobile, password=pin)
        if user is None or user.is_staff or not hasattr(user, 'labor_profile'):
            throttle.register_failure('login', mobile)
            throttle.register_failure('login', ip)
            return render(request, 'portal/login.html', {
                'error': 'Invalid mobile number or PIN.',
                'mobile': mobile,
            })
        if not user.labor_profile.login_enabled:
            return render(request, 'portal/login.html', {
                'error': 'Your access has been disabled. Contact the admin.',
                'mobile': mobile,
            })

        login(request, user)
        throttle.reset('login', mobile)
        throttle.reset('login', ip)
        return redirect('portal:home')

    return render(request, 'portal/login.html')


def portal_logout(request):
    logout(request)
    return redirect('portal:login')


# ---------------------------------------------------------------------------
# Portal (read-only worker views)
# ---------------------------------------------------------------------------
@worker_required
def home(request):
    labor = request.labor
    context = {
        'labor': labor,
        'total_earned': labor.total_earned,
        'total_paid': labor.total_paid,
        'pending': labor.pending_balance,
    }
    return render(request, 'portal/home.html', context)


@worker_required
def work_history(request):
    labor = request.labor
    search = (request.GET.get('search') or '').strip()

    work_qs = WorkEntry.objects.filter(labor=labor).select_related('lot', 'operation')
    sample_qs = Sample.objects.filter(labor=labor).select_related('party')
    if search:
        work_qs = work_qs.filter(
            Q(lot__lot_number__icontains=search) | Q(operation__name__icontains=search)
        )
        sample_qs = sample_qs.filter(
            Q(sample_name__icontains=search) | Q(party__name__icontains=search)
        )

    rows = []
    for w in work_qs:
        rows.append({
            'date': w.work_date, 'lot': w.lot.lot_number,
            'detail': w.operation.name, 'pieces': w.pieces,
            'rate': w.rate, 'amount': w.total_amount,
        })
    for s in sample_qs:
        rows.append({
            'date': s.work_date, 'lot': 'SAMPLE',
            'detail': s.sample_name, 'pieces': s.total_pieces,
            'rate': s.rate, 'amount': s.total_amount,
        })
    rows.sort(key=lambda r: r['date'], reverse=True)

    paginator = Paginator(rows, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {'labor': labor, 'page_obj': page_obj, 'search': search}
    if request.headers.get('HX-Request'):
        return render(request, 'portal/partials/work_rows.html', context)
    return render(request, 'portal/work_history.html', context)


@worker_required
def payment_history(request):
    labor = request.labor
    payments = labor.payments.all().order_by('-payment_date', '-created_at')
    paginator = Paginator(payments, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'portal/payments.html', {'labor': labor, 'page_obj': page_obj})
