from django.db.models import Avg


def update_product_rating(product):
    # Calculate average rating from all reviews
    average_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']
    
    # Update product rating (set to 0.0 if no reviews exist)
    product.rating = average_rating if average_rating is not None else 0.0
    product.save(update_fields=['rating'])

