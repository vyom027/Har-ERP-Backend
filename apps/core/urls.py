from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('lots/', views.lot_list, name='lot_list'),
    path('party/add/', views.add_party, name='add_party'),
    path('lots/add/', views.add_lot, name='add_lot'),
    path('lots/<int:pk>/', views.lot_detail, name='lot_detail'),
    path('lots/<int:pk>/edit/', views.edit_lot, name='edit_lot'),
    path('lots/<int:pk>/delete/', views.delete_lot, name='delete_lot'),
    path('parties/', views.party_list, name='party_list'),
    path('parties/<int:pk>/edit/', views.edit_party, name='edit_party'),
    path('parties/<int:pk>/delete/', views.delete_party, name='delete_party'),
]
