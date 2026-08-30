from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('products/', include('products.urls', namespace='products')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('checkout/', include('orders.urls', namespace='orders')),
    path('', include('core.urls', namespace='core')),
]

# Serve media files (real product photos) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)