from django.shortcuts import render
from products.models import Product, Category


def index(request):
    """Home page view"""
    featured_products = Product.objects.all()[:8]

    context = {
        "featured_products": featured_products,
        "title": "AuroraMart - Your Premium Shopping Destination",
    }
    return render(request, "home/index.html", context)


def about(request):
    """About page view"""
    return render(request, "home/about.html")


def contact(request):
    """Contact page view"""
    return render(request, "home/contact.html")
