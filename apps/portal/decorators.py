from functools import wraps
from django.shortcuts import redirect


def worker_required(view_func):
    """Allow only authenticated, non-staff users linked to an active Labor."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect('portal:login')
        if user.is_staff or not hasattr(user, 'labor_profile'):
            return redirect('portal:login')
        labor = user.labor_profile
        if not labor.login_enabled or not labor.is_activated:
            return redirect('portal:login')
        request.labor = labor
        return view_func(request, *args, **kwargs)
    return _wrapped
