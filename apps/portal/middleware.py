"""Hard isolation for worker accounts.

A logged-in worker (non-staff User linked to a Labor) may ONLY reach portal,
setup, login and logout URLs. Any attempt to load an admin URL is redirected to
the worker portal. This is the central enforcement point so individual admin
views don't each need a decorator.
"""
from django.shortcuts import redirect


# URL namespaces/names a worker is allowed to reach
_ALLOWED_NAMESPACE = 'portal'
_ALLOWED_NAMES = {'logout', 'login'}


class WorkerAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated or user.is_staff:
            return None
        # Only gate actual workers (non-staff linked to a Labor)
        if not hasattr(user, 'labor_profile'):
            return None

        match = request.resolver_match
        if match is None:
            return None
        if match.namespace == _ALLOWED_NAMESPACE:
            return None
        if (match.view_name or '') in _ALLOWED_NAMES:
            return None
        # Worker reaching a non-portal URL — bounce to portal
        return redirect('portal:home')
