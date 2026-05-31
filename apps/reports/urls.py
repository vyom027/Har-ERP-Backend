from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.home, name='home'),
    path('export/labor/', views.export_labor_excel, name='export_labor_excel'),
    path('export/production/', views.export_production_excel, name='export_production_excel'),
]
