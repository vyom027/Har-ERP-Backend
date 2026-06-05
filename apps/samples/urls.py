from django.urls import path
from . import views

app_name = 'samples'

urlpatterns = [
    path('', views.sample_list, name='list'),
    path('modal/', views.sample_modal, name='sample_modal'),
    path('save/', views.save_sample, name='save_sample'),
    path('delete/', views.delete_sample, name='delete_sample'),
]
