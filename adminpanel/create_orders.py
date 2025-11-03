import os
import django
import random
import sys
from decimal import Decimal
from datetime import timedelta

# Usage:
# 1. Create a single order:
#    python adminpanel/create_orders.py
# 2. Create multiple orders at once:
#    python adminpanel/create_orders.py 5  # Creates 5 orders

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auroramartproject.settings")

django.setup()

from accounts.models import User
from products.models import Product, ProductVariant
from orders.models import Order, OrderItem
from django.utils import timezone
from django.db import IntegrityError

def get_or_create_test_customer():
    """Get or create a test customer for orders"""
    user, created = User.objects.get_or_create(
        username='testcustomer',
        defaults={
            'email': 'customer@test.com',
            'first_name': 'Test',
            'last_name': 'Customer',
            'is_active': True,
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print("✅ Created test customer: testcustomer")
    return user

def create_single_order():
    """
    Creates a single order with random items.
    Returns the created order details.
    """
    
    # Get or create test customer
    customer = get_or_create_test_customer()
    
    # Get available product variants
    variants = list(ProductVariant.objects.filter(stock__gt=0)[:5])
    
    if not variants:
        print("❌ Error: No product variants with stock available.")
        print("Please create products first using: python adminpanel/create_instances/create_products.py")
        return None
    
    # Random order details
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    locations = ['warehouse', 'sorting_facility', 'local_hub', 'out_for_delivery', 'delivered']
    
    status = random.choice(statuses)
    location = random.choice(locations)
    
    # Match location to status for realism
    if status == 'pending':
        location = 'warehouse'
    elif status == 'confirmed':
        location = 'warehouse'
    elif status == 'processing':
        location = random.choice(['warehouse', 'sorting_facility'])
    elif status == 'shipped':
        location = random.choice(['sorting_facility', 'local_hub', 'out_for_delivery'])
    elif status == 'delivered':
        location = 'delivered'
    
    # CALCULATE SUBTOTAL AND TOTAL FIRST
    num_items = random.randint(1, min(4, len(variants)))
    selected_variants = random.sample(variants, num_items)
    
    subtotal = Decimal('0.00')
    items_data = []
    
    for variant in selected_variants:
        quantity = random.randint(1, 3)
        item_total = variant.price * quantity
        subtotal += item_total
        items_data.append({
            'variant': variant,
            'quantity': quantity,
            'price': variant.price
        })
    
    # Calculate total (you can add shipping, tax, discounts here)
    shipping_fee = Decimal('5.00')  # Example shipping fee
    tax = subtotal * Decimal('0.07')  # Example 7% tax
    total = subtotal + shipping_fee + tax
    
    try:
        # Create order WITH subtotal and total
        order = Order.objects.create(
            user=customer,
            status=status,
            contact_number=f'555{random.randint(1000000, 9999999)}',
            delivery_address=f'{random.randint(100, 999)} Test Street, Test City, {random.randint(10000, 99999)}',
            current_location=location,
            subtotal=subtotal,  # ADD THIS
            total=total,        # ADD THIS
            created_at=timezone.now() - timedelta(days=random.randint(0, 30)),
        )
        
        # Add order items using pre-calculated data
        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                variant=item_data['variant'],
                quantity=item_data['quantity'],
                price=item_data['price']
            )
        
        print("=" * 60)
        print("✅ Order Created Successfully!")
        print("=" * 60)
        print(f"Order ID: ORD{order.id}")
        print(f"Order Number: {order.order_number}")
        print(f"Customer: {customer.username} ({customer.email})")
        print(f"Status: {order.get_status_display()}")
        print(f"Location: {order.get_current_location_display()}")
        print(f"Items: {order.items.count()} item(s)")
        print(f"Subtotal: ${subtotal:.2f}")
        print(f"Tax: ${tax:.2f}")
        print(f"Shipping: ${shipping_fee:.2f}")
        print(f"Total: ${total:.2f}")
        print(f"Contact: {order.contact_number}")
        print(f"Address: {order.delivery_address}")
        print(f"Created: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'status': status,
            'location': location,
            'items_count': order.items.count(),
            'total_amount': total,
        }
        
    except IntegrityError as e:
        print(f"❌ Error: Unable to create order. {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_multiple_orders(count=1):
    """
    Create multiple orders at once.
    
    Args:
        count (int): Number of orders to create
    """
    print(f"\n📋 Creating {count} order(s)...\n")
    
    created_orders = []
    
    for i in range(count):
        print(f"\n--- Order {i+1}/{count} ---")
        order_data = create_single_order()
        if order_data:
            created_orders.append(order_data)
        print()  # Add spacing between orders
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Successfully created {len(created_orders)} order(s)")
    print("=" * 60)
    
    if created_orders:
        print("\n📝 Summary of Created Orders:")
        print("-" * 60)
        total_amount = Decimal('0.00')
        for order_data in created_orders:
            print(f"Order ID: ORD{order_data['order_id']} | "
                  f"Status: {order_data['status']} | "
                  f"Items: {order_data['items_count']} | "
                  f"Total: ${order_data['total_amount']:.2f}")
            total_amount += order_data['total_amount']
        print("-" * 60)
        print(f"Total Revenue: ${total_amount:.2f}")
        print()
    
    return created_orders

if __name__ == '__main__':
    import sys
    
    # Check if user wants to create multiple orders
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            if count < 1:
                print("❌ Error: Please provide a positive number")
                sys.exit(1)
            create_multiple_orders(count)
        except ValueError:
            print("❌ Error: Please provide a valid number")
            print("Usage: python adminpanel/create_instances/create_orders.py [number_of_orders]")
            sys.exit(1)
    else:
        # Create single order
        create_single_order()