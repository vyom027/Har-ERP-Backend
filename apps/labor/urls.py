from django.urls import path
from . import views

app_name = 'labor'

urlpatterns = [
    path('', views.labor_list, name='labor_list'),
    path('add/', views.add_labor, name='add_labor'),
    path('<int:pk>/', views.labor_profile, name='labor_profile'),
    path('<int:pk>/delete/', views.delete_labor, name='delete_labor'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.add_payment, name='add_payment'),
    path('payments/<int:pk>/edit/', views.edit_payment, name='edit_payment'),
    path('payments/<int:pk>/delete/', views.delete_payment, name='delete_payment'),
]
