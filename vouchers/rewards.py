"""
Rewards system utility functions for generating vouchers and badges.
"""
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid


def generate_reward_voucher_code(user):
    """
    Generate a unique reward voucher code for a user.
    
    Args:
        user: Customer instance
        
    Returns:
        str: Unique voucher code (e.g., "REWARD-{user_id}-{timestamp}")
    """
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8].upper()
    return f"REWARD-{user.id}-{unique_id}"


def calculate_reward_voucher_amount(subtotal):
    """
    Determine voucher amount based on subtotal and configured thresholds.
    Returns the highest threshold amount the subtotal qualifies for.
    
    Args:
        subtotal: Decimal - Order subtotal amount
        
    Returns:
        Decimal: Voucher amount, or None if no threshold is met
    """
    if not hasattr(settings, 'REWARD_THRESHOLDS'):
        return None
    
    thresholds = settings.REWARD_THRESHOLDS
    if not thresholds:
        return None
    
    # Find the highest threshold that the subtotal meets
    qualifying_threshold = None
    for threshold_amount in sorted(thresholds.keys(), reverse=True):
        if subtotal >= Decimal(str(threshold_amount)):
            qualifying_threshold = threshold_amount
            break
    
    if qualifying_threshold:
        return Decimal(str(thresholds[qualifying_threshold]))
    
    return None


def get_badge_for_amount(amount):
    """
    Get badge information for a purchase amount.
    
    Args:
        amount: Decimal - Purchase amount
        
    Returns:
        dict: Badge information or None if no badge qualifies
    """
    if not hasattr(settings, 'REWARD_BADGES'):
        return None
    
    badges = settings.REWARD_BADGES
    if not badges:
        return None
    
    # Find the highest badge threshold that the amount meets
    qualifying_threshold = None
    for threshold_amount in sorted(badges.keys(), reverse=True):
        if amount >= Decimal(str(threshold_amount)):
            qualifying_threshold = threshold_amount
            break
    
    if qualifying_threshold:
        badge_info = badges[qualifying_threshold].copy()
        badge_info['threshold'] = qualifying_threshold
        return badge_info
    
    return None


def create_reward_voucher(user, amount, order, badge_info=None):
    """
    Create a reward voucher for a user.
    
    Args:
        user: Customer instance
        amount: Decimal - Voucher amount
        order: Order instance that triggered the reward
        badge_info: Optional dict with badge information
        
    Returns:
        Voucher: Created voucher instance or None if creation fails
    """
    from vouchers.models import Voucher
    from accounts.models import Superuser
    
    # Generate unique voucher code
    voucher_code = generate_reward_voucher_code(user)
    
    # Ensure code is unique (try up to 10 times)
    attempts = 0
    while Voucher.objects.filter(promo_code=voucher_code).exists() and attempts < 10:
        voucher_code = generate_reward_voucher_code(user)
        attempts += 1
    
    if attempts >= 10:
        # Failed to generate unique code, log error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate unique voucher code for user {user.id}")
        return None
    
    # Get or create a superuser for created_by (or use None)
    superuser = Superuser.objects.filter(is_superuser=True).first()
    
    # Build description with badge info if available
    description = f"Reward voucher for your ${order.subtotal} purchase!"
    if badge_info:
        description += f" You earned the {badge_info['name']} badge!"
    
    # Create voucher with effectively no expiration (10 years)
    voucher = Voucher.objects.create(
        name=f"Reward Voucher - ${amount}",
        promo_code=voucher_code,
        description=description,
        discount_type='fixed',
        discount_value=amount,
        min_purchase=Decimal(str(settings.REWARD_VOUCHER_MIN_PURCHASE)),
        first_time_only=False,
        max_uses=None,  # Unlimited total uses (but per-user limit applies)
        max_uses_per_user=1,  # Each user can only use this voucher once
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=365*10),  # 10 years (effectively no expiration)
        is_active=True,
        user=user,  # User-specific voucher
        created_by=superuser,
    )
    
    return voucher


def should_generate_reward(order):
    """
    Check if an order qualifies for reward generation.
    Excludes cancelled and refunded orders.
    
    Args:
        order: Order instance
        
    Returns:
        bool: True if order qualifies for reward
    """
    # Don't generate rewards for cancelled or refunded orders
    if order.status in ['cancelled', 'refunded']:
        return False
    
    # Only generate rewards for delivered or confirmed orders
    if order.status not in ['delivered', 'confirmed']:
        return False
    
    # Check if subtotal meets any threshold
    voucher_amount = calculate_reward_voucher_amount(order.subtotal)
    if voucher_amount is None:
        return False
    
    return True


def get_user_badges(user):
    """
    Get all badges earned by a user based on their order history.
    Badges are earned based on single order purchase amounts.
    
    Args:
        user: Customer instance
        
    Returns:
        list: List of badge dictionaries (highest badge only, or all earned badges)
    """
    from orders.models import Order
    
    if not hasattr(settings, 'REWARD_BADGES'):
        return []
    
    badges = settings.REWARD_BADGES
    if not badges:
        return []
    
    # Get all delivered/confirmed orders (non-cancelled, non-refunded)
    orders = Order.objects.filter(
        user=user,
        status__in=['delivered', 'confirmed']
    ).exclude(status__in=['cancelled', 'refunded'])
    
    # Find the highest badge threshold achieved across all orders
    highest_threshold = None
    for order in orders:
        for threshold_amount in sorted(badges.keys(), reverse=True):
            if order.subtotal >= Decimal(str(threshold_amount)):
                if highest_threshold is None or threshold_amount > highest_threshold:
                    highest_threshold = threshold_amount
                break
    
    # Return all badges up to and including the highest threshold achieved
    earned_badges = []
    if highest_threshold:
        for threshold_amount in sorted(badges.keys()):
            if threshold_amount <= highest_threshold:
                badge_info = badges[threshold_amount].copy()
                badge_info['threshold'] = threshold_amount
                earned_badges.append(badge_info)
    
    return earned_badges


def get_milestone_progress(user):
    """
    Get user's progress towards the next milestone badge.
    
    Args:
        user: Customer instance
        
    Returns:
        dict: Progress information with:
            - current_badge: Highest badge earned (or None)
            - next_badge: Next badge to earn (or None)
            - progress_percentage: Percentage towards next badge (0-100)
            - current_amount: Highest single order amount
            - next_threshold: Next threshold to reach
            - amount_needed: Amount needed to reach next threshold
    """
    from orders.models import Order
    
    if not hasattr(settings, 'REWARD_BADGES'):
        return {
            'current_badge': None,
            'next_badge': None,
            'progress_percentage': 0,
            'current_amount': 0,
            'next_threshold': None,
            'amount_needed': 0
        }
    
    badges = settings.REWARD_BADGES
    if not badges:
        return {
            'current_badge': None,
            'next_badge': None,
            'progress_percentage': 0,
            'current_amount': 0,
            'next_threshold': None,
            'amount_needed': 0
        }
    
    # Get all delivered/confirmed orders (non-cancelled, non-refunded)
    orders = Order.objects.filter(
        user=user,
        status__in=['delivered', 'confirmed']
    ).exclude(status__in=['cancelled', 'refunded'])
    
    # Find the highest single order amount
    highest_order_amount = Decimal('0')
    for order in orders:
        if order.subtotal > highest_order_amount:
            highest_order_amount = order.subtotal
    
    # Get reward thresholds to include voucher amounts
    reward_thresholds = getattr(settings, 'REWARD_THRESHOLDS', {})
    
    # Find current badge (highest threshold achieved)
    current_badge = None
    current_threshold = None
    sorted_thresholds = sorted(badges.keys())
    
    for threshold_amount in sorted_thresholds:
        if highest_order_amount >= Decimal(str(threshold_amount)):
            current_threshold = threshold_amount
            badge_info = badges[threshold_amount].copy()
            badge_info['threshold'] = threshold_amount
            # Add voucher reward information
            if threshold_amount in reward_thresholds:
                badge_info['voucher_amount'] = float(reward_thresholds[threshold_amount])
            current_badge = badge_info
    
    # Find next badge to earn
    next_badge = None
    next_threshold = None
    for threshold_amount in sorted_thresholds:
        if highest_order_amount < Decimal(str(threshold_amount)):
            next_threshold = threshold_amount
            badge_info = badges[threshold_amount].copy()
            badge_info['threshold'] = threshold_amount
            # Add voucher reward information
            if threshold_amount in reward_thresholds:
                badge_info['voucher_amount'] = float(reward_thresholds[threshold_amount])
            next_badge = badge_info
            break
    
    # Calculate progress
    progress_percentage = 0
    amount_needed = 0
    
    if next_badge and next_threshold:
        amount_needed = Decimal(str(next_threshold)) - highest_order_amount
        if amount_needed < 0:
            amount_needed = Decimal('0')
        
        # Calculate percentage (0-100)
        if next_threshold > 0:
            progress_percentage = float((highest_order_amount / Decimal(str(next_threshold))) * 100)
            if progress_percentage > 100:
                progress_percentage = 100
            if progress_percentage < 0:
                progress_percentage = 0
    
    return {
        'current_badge': current_badge,
        'next_badge': next_badge,
        'progress_percentage': round(progress_percentage, 1),
        'current_amount': float(highest_order_amount),
        'next_threshold': next_threshold,
        'amount_needed': float(amount_needed) if amount_needed else 0
    }


def get_all_milestones_progress(user):
    """
    Get progress for all milestone badges.
    
    Args:
        user: Customer instance
        
    Returns:
        list: List of milestone progress dictionaries, one for each badge threshold
    """
    from orders.models import Order
    
    if not hasattr(settings, 'REWARD_BADGES'):
        return []
    
    badges = settings.REWARD_BADGES
    if not badges:
        return []
    
    # Get all delivered/confirmed orders (non-cancelled, non-refunded)
    orders = Order.objects.filter(
        user=user,
        status__in=['delivered', 'confirmed']
    ).exclude(status__in=['cancelled', 'refunded'])
    
    # Find the highest single order amount
    highest_order_amount = Decimal('0')
    for order in orders:
        if order.subtotal > highest_order_amount:
            highest_order_amount = order.subtotal
    
    # Get progress for each milestone
    milestones = []
    sorted_thresholds = sorted(badges.keys())
    
    for threshold_amount in sorted_thresholds:
        badge_info = badges[threshold_amount].copy()
        badge_info['threshold'] = threshold_amount
        
        # Check if earned
        is_earned = highest_order_amount >= Decimal(str(threshold_amount))
        
        # Calculate progress percentage
        if is_earned:
            progress_percentage = 100.0
            amount_needed = 0
        else:
            # Calculate progress towards this milestone
            if threshold_amount > 0:
                progress_percentage = float((highest_order_amount / Decimal(str(threshold_amount))) * 100)
                if progress_percentage > 100:
                    progress_percentage = 100
                if progress_percentage < 0:
                    progress_percentage = 0
            else:
                progress_percentage = 0
            
            amount_needed = float(Decimal(str(threshold_amount)) - highest_order_amount)
            if amount_needed < 0:
                amount_needed = 0
        
        milestones.append({
            'badge': badge_info,
            'is_earned': is_earned,
            'progress_percentage': round(progress_percentage, 1),
            'current_amount': float(highest_order_amount),
            'threshold': threshold_amount,
            'amount_needed': amount_needed if not is_earned else 0
        })
    
    return milestones

