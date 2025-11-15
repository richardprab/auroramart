from django.shortcuts import render
from django.db.models import Q
from products.models import Product, Category


def index(request):
    """Home page view"""
    # Featured products for "Recommended For You" section
    featured_products = (
        Product.objects.filter(is_active=True, variants__is_active=True)
        .distinct()
        .select_related("category")
        .prefetch_related("images", "variants")
        .order_by('-rating', '-created_at')[:8]
    )

    # Get all parent categories (categories without parent)
    cats = list(
        Category.objects.filter(parent__isnull=True, is_active=True)
        .only("id", "name", "slug")
        .order_by("name")
    )

    # Attach accurate product_count (includes direct children)
    # Only count products with active variants
    for c in cats:
        cat_ids = Category.objects.filter(Q(id=c.id) | Q(parent_id=c.id)).values_list(
            "id", flat=True
        )
        c.product_count = (
            Product.objects.filter(
                is_active=True, 
                category_id__in=cat_ids,
                variants__is_active=True
            )
            .distinct()
            .count()
        )
    
    # Get user's wishlist items if authenticated
    user_wishlist_ids = []
    profile_completion_percentage = None
    recently_viewed = []
    if request.user.is_authenticated:
        from accounts.models import Wishlist, BrowsingHistory, Customer, Staff
        from django.contrib.auth import logout
        from django.contrib import messages
        
        # If a Staff user is logged in, log them out and redirect to staff login
        if isinstance(request.user, Staff) or (hasattr(request.user, 'is_staff') and request.user.is_staff):
            logout(request)
            messages.info(request, 'Staff accounts cannot access customer pages. Please use the staff login.')
            from django.shortcuts import redirect
            return redirect('/adminpanel/login/')
        
        # Only proceed if user is a Customer
        if isinstance(request.user, Customer):
            user_wishlist_ids = list(
                Wishlist.objects.filter(user=request.user)
                .values_list('product_id', flat=True)
            )
            # Calculate profile completion percentage
            try:
                profile_completion_percentage = request.user.get_profile_completion_percentage()
            except (AttributeError, TypeError):
                profile_completion_percentage = None
            # Get recently viewed products (last 8)
            recently_viewed = BrowsingHistory.objects.filter(
                user=request.user
            ).select_related('product').prefetch_related('product__images', 'product__variants').order_by('-viewed_at')[:8]

    return render(
        request,
        "home/index.html",
        {
            "categories": cats,
            "featured_products": featured_products,
            "user_wishlist_ids": user_wishlist_ids,
            "profile_completion_percentage": profile_completion_percentage,
            "recently_viewed": recently_viewed,
        },
    )


def about(request):
    """About page view with real metrics"""
    from django.contrib.auth import get_user_model
    from orders.models import Order
    
    User = get_user_model()
    
    # Calculate real metrics
    total_products = Product.objects.filter(is_active=True, variants__is_active=True).distinct().count()
    from accounts.models import Customer, Staff, Superuser
    total_customers = Customer.objects.filter(is_active=True).count() + Staff.objects.filter(is_active=True).count() + Superuser.objects.filter(is_active=True).count()
    total_brands = Product.objects.filter(is_active=True).values('brand').distinct().count()
    total_orders = Order.objects.count()
    
    context = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_brands': total_brands,
        'total_orders': total_orders,
    }
    
    return render(request, "home/about.html", context)


def contact(request):
    """Contact page view"""
    return render(request, "home/contact.html")


def faq(request):
    """FAQ page view"""
    # FAQ data organized by category
    faqs = [
        {
            'category': 'Orders & Shipping',
            'icon': 'package',
            'questions': [
                {
                    'question': 'How long does shipping take?',
                    'answer': 'Standard shipping typically takes 3-5 business days. Express shipping is available and takes 1-2 business days. International orders may take 7-14 business days depending on the destination.'
                },
                {
                    'question': 'Do you offer free shipping?',
                    'answer': 'Yes! We offer free standard shipping on all orders over $50. For orders under $50, a flat rate of $5.99 applies.'
                },
                {
                    'question': 'Can I track my order?',
                    'answer': 'Absolutely! Once your order ships, you\'ll receive a tracking number via email. You can also track your order by logging into your account and viewing your order history.'
                },
                {
                    'question': 'Do you ship internationally?',
                    'answer': 'Yes, we ship to over 100 countries worldwide. International shipping rates and delivery times vary by location.'
                },
            ]
        },
        {
            'category': 'Returns & Refunds',
            'icon': 'rotate-ccw',
            'questions': [
                {
                    'question': 'What is your return policy?',
                    'answer': 'We offer a 30-day return policy for most items. Products must be unused, in original packaging, and with all tags attached. Some items like personalized products may not be eligible for return.'
                },
                {
                    'question': 'How do I start a return?',
                    'answer': 'Log into your account, go to your order history, select the order, and click "Request Return". Follow the instructions to print your return label. Return shipping is free for defective items.'
                },
                {
                    'question': 'When will I receive my refund?',
                    'answer': 'Refunds are processed within 5-7 business days after we receive your return. The refund will be issued to your original payment method.'
                },
                {
                    'question': 'Can I exchange an item?',
                    'answer': 'Yes! If you need a different size or color, you can exchange items within 30 days. Contact our customer service team to arrange an exchange.'
                },
            ]
        },
        {
            'category': 'Payment & Security',
            'icon': 'credit-card',
            'questions': [
                {
                    'question': 'What payment methods do you accept?',
                    'answer': 'We accept all major credit cards (Visa, MasterCard, American Express, Discover), PayPal, Apple Pay, and Google Pay.'
                },
                {
                    'question': 'Is my payment information secure?',
                    'answer': 'Yes! We use industry-standard SSL encryption to protect your payment information. We never store your full credit card details on our servers.'
                },
                {
                    'question': 'Can I use multiple payment methods?',
                    'answer': 'Currently, we support one payment method per order. However, you can use gift cards or store credit in combination with a primary payment method.'
                },
                {
                    'question': 'Do you offer payment plans?',
                    'answer': 'Yes! We partner with Afterpay and Klarna to offer buy now, pay later options on orders over $50. Choose this option at checkout.'
                },
            ]
        },
        {
            'category': 'Account & Profile',
            'icon': 'user',
            'questions': [
                {
                    'question': 'Do I need an account to shop?',
                    'answer': 'No, you can checkout as a guest. However, creating an account lets you track orders, save addresses, manage wishlists, and access exclusive deals.'
                },
                {
                    'question': 'How do I reset my password?',
                    'answer': 'Click "Forgot Password" on the login page. Enter your email address, and we\'ll send you a link to reset your password.'
                },
                {
                    'question': 'Can I change my email address?',
                    'answer': 'Yes! Log into your account, go to Account Settings, and update your email address. You\'ll need to verify your new email.'
                },
                {
                    'question': 'How do I delete my account?',
                    'answer': 'Contact our customer service team to request account deletion. We\'ll process your request within 7 business days. Note that this action is permanent.'
                },
            ]
        },
        {
            'category': 'Products & Stock',
            'icon': 'shopping-bag',
            'questions': [
                {
                    'question': 'How do I know if an item is in stock?',
                    'answer': 'Product pages show real-time stock availability. If an item shows "In Stock", it\'s available for immediate shipment. "Low Stock" means limited quantity remaining.'
                },
                {
                    'question': 'Can I get notified when out-of-stock items are available?',
                    'answer': 'Yes! Click "Notify Me" on any out-of-stock product page, enter your email, and we\'ll alert you when the item is back in stock.'
                },
                {
                    'question': 'Are your product descriptions accurate?',
                    'answer': 'We strive for 100% accuracy in all product descriptions. If you receive an item that doesn\'t match the description, contact us for a full refund or exchange.'
                },
                {
                    'question': 'Do you offer price matching?',
                    'answer': 'Yes! If you find a lower price on an identical item from an authorized retailer, contact us within 7 days of purchase for a price match.'
                },
            ]
        },
    ]
    
    context = {
        'faqs': faqs,
    }
    
    return render(request, "home/faq.html", context)
