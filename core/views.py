from django.shortcuts import render
from products.models import Product, Category


def home(request):
    """
    Renders the Shah G Cap House homepage with dynamic categories
    and active products fetched directly from PostgreSQL database.
    """
    categories = Category.objects.all()
    # Fetch only active products, ordered by newest first
    featured_products = Product.objects.filter(is_active=True)[:14]

    context = {
        'categories': categories,
        'featured_products': featured_products,
    }
    return render(request, 'core/home.html', context)