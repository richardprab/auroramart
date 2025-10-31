from cart.views import get_or_create_cart


def cart_context(request):
    """Add cart data to all templates"""
    try:
        cart = get_or_create_cart(request)
        return {
            "cart_count": cart.get_item_count(),
            "cart_total": cart.get_total(),
        }
    except:
        return {
            "cart_count": 0,
            "cart_total": 0,
        }
