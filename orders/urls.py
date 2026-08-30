from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
]