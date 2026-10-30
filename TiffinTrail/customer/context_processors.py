from .models import Cart, Subscription


def customer_context(request):
    cart_count = 0
    active_subs_count = 0
    cart = None

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        active_subs_count = Subscription.objects.filter(user=request.user, status='active').count()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()

    if cart:
        cart_count = cart.items_count

    return {
        'cart_items_count': cart_count,
        'active_subscriptions_count': active_subs_count,
        'current_cart': cart,
    }
