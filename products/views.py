from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category


def product_list(request):
    """
    Renders the complete catalog page with real-time search,
    dynamic category filtering, and price sorting.
    """
    # 1. Base QuerySet: Fetch only active products
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    # 2. Search Handling (?q=article)
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 3. Category Filter Handling (?category=slug)
    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    # 4. Sorting Handling (?sort=...)
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    else:
        # Default: Newest first
        products = products.order_by('-created_at')

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_count': products.count(),
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    """
    Renders individual product detail page for a specific article.
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Fetch up to 4 related products from the same category
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'products/product_detail.html', context)