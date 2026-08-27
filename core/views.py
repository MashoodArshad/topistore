from django.shortcuts import render

def home(request):
    """
    Renders the TopiStore homepage.
    """
    return render(request, 'core/home.html')