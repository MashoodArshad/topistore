from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.decorators.cache import cache_control

# ⚡ High-Performance Cached Media View (Caches images in user's browser for 30 days)
cached_serve = cache_control(max_age=2592000, public=True, immutable=True)(serve)

urlpatterns = [
    path('admin/', admin.site.urls),
     path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls', namespace='products')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('checkout/', include('orders.urls', namespace='orders')),
    path('', include('core.urls', namespace='core')),
    
    # 📸 Fast production static and media routes with instant caching
    re_path(r'^media/(?P<path>.*)$', cached_serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', cached_serve, {'document_root': settings.STATIC_ROOT}),
]
from core import views as core_views

# Custom Error Handlers
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)