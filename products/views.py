from django.shortcuts import render, get_object_or_404
from .models import Product, Category

def product_list(request):
    """
    Renders the complete catalog page containing all 14 articles.
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    """
    Renders individual product detail page for a specific article.
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Get 4 related products from same category (excluding current product)
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'products/product_detail.html', context)