from .cart import Cart


def cart(request):
    """
    Makes the user's shopping cart available globally across all templates.
    """
    return {'cart': Cart(request)}