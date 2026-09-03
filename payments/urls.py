from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('webhook/', views.safepay_webhook, name='safepay_webhook'),
    path('callback/<str:order_number>/', views.payment_callback, name='payment_callback'),
    path('cancel/<str:order_number>/', views.payment_cancel, name='payment_cancel'),
]