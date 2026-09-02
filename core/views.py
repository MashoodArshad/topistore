from django.shortcuts import render, redirect
from django.contrib import messages
from products.models import Product, Category


def home(request):
    """
    Renders the Shah G Cap House homepage with dynamic categories
    and featured active products fetched from PostgreSQL database.
    """
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_active=True)[:6]

    context = {
        'categories': categories,
        'featured_products': featured_products,
    }
    return render(request, 'core/home.html', context)


def about(request):
    """
    Renders the elegant brand story and founder's profile page.
    """
    return render(request, 'core/about.html')


def contact(request):
    """
    Renders the customer support & WhatsApp contact page.
    Handles customer inquiries submission.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        messages.success(
            request, 
            f"JazakAllah Khair {name}! Your message has been received. Our team will reach out to you shortly."
        )
        return redirect('core:contact')

    return render(request, 'core/contact.html')
    from django.shortcuts import render

def custom_404(request, exception):
    """Custom 404 Page Not Found"""
    return render(request, 'core/404.html', status=404)

def custom_500(request):
    """Custom 500 Internal Server Error"""
    return render(request, 'core/500.html', status=500)