from django.shortcuts import render
from products.models import Product, Category


def index(request):
    """Home page view"""
    featured_products = Product.objects.filter(is_active=True)[:8]
    categories = Category.objects.all()[:8]  # Add this line

    context = {
        "featured_products": featured_products,
        "categories": categories,  # Add this line
    }
    return render(request, "home/index.html", context)


def about(request):
    """About page view"""
    return render(request, "home/about.html")


def contact(request):
    """Contact page view"""
    return render(request, "home/contact.html")
