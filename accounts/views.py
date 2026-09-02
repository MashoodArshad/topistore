from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignUpForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Assalam-o-Alaikum! Welcome to Shah G Cap House, {user.first_name or user.username}.")
            return redirect('core:home')
        else:
            messages.error(request, "Registration failed. Please check form errors below.")
    else:
        form = SignUpForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect('core:home')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()
        
    # Styling existing login inputs
    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-emerald focus:border-transparent text-sm transition',
            'placeholder': field.label
        })
        
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('core:home')
from django.contrib.auth.decorators import login_required
from orders.models import Order  # Import Order model taake orders history profile page par dikha sakein

@login_required
def profile_view(request):
    """
    Displays User personal info and their past orders list.
    """
    user_orders = Order.objects.filter(user=request.user)
    context = {
        'orders': user_orders,
    }
    return render(request, 'accounts/profile.html', context)