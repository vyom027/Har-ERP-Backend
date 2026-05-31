from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    path('', views.production_table, name='table'),
    path('entry/modal/', views.entry_modal, name='entry_modal'),
    path('quick-add/', views.quick_add_production, name='quick_add'),
    path('get-colors/', views.get_lot_colors, name='get_colors'),
    path('get-lot-data/', views.get_lot_data, name='get_lot_data'),
    path('entry/save/', views.save_entry, name='save_entry'),
    path('entry/delete/', views.delete_entry, name='delete_entry'),
    path('entry/last-rate/', views.get_last_rate, name='get_last_rate'),
]
