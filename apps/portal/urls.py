from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('login/', views.portal_login, name='login'),
    path('logout/', views.portal_logout, name='logout'),
    path('', views.home, name='home'),
    path('work/', views.work_history, name='work'),
    path('payments/', views.payment_history, name='payments'),
]
