from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from apps.portal import views as portal_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Worker portal + token-gated PIN setup
    path('setup/<str:token>/', portal_views.setup, name='labor_setup'),
    path('portal/', include('apps.portal.urls')),

    path('', include('apps.dashboard.urls')),
    path('core/', include('apps.core.urls')),
    path('operations/', include('apps.operations.urls')),
    path('labor/', include('apps.labor.urls')),
    path('production/', include('apps.production.urls')),
    path('reports/', include('apps.reports.urls')),
    path('samples/', include('apps.samples.urls')),
    path('inward/', include('apps.inward.urls')),
]
