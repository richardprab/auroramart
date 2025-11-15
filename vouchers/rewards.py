from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)


def generate_reward_voucher_code(user):
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


def get_cumulative_spending(user):
    """
    Calculate cumulative spending across all completed orders.
    
    Args:
        user: Customer instance
        
    Returns:
        Decimal: Total cumulative spending
    """
    from orders.models import Order
    
    orders = Order.objects.filter(
        user=user,
        status__in=['delivered', 'confirmed']
    ).exclude(status__in=['cancelled', 'refunded'])
    
    total_spending = Decimal('0')
    for order in orders:
        total_spending += order.subtotal
    
    return total_spending


def get_earned_milestones(user):
    """
    Get list of milestone thresholds that the user has already earned.
    This is determined by checking existing milestone vouchers.
    
    Args:
        user: Customer instance
        
    Returns:
        set: Set of threshold amounts (as integers) that have been earned
    """
    from vouchers.models import Voucher
    
    if not hasattr(settings, 'REWARD_BADGES'):
        return set()
    
    badges = settings.REWARD_BADGES
    if not badges:
        return set()
    
    reward_thresholds = getattr(settings, 'REWARD_THRESHOLDS', {})
    earned_milestones = set()
    
    # Check user's existing vouchers to see which milestones they've earned
    # Milestone vouchers have descriptions containing badge names
    user_vouchers = Voucher.objects.filter(
        user=user,
        promo_code__startswith=f"REWARD-{user.id}-"
    )
    
    # Check each threshold to see if user has a voucher for it
    for threshold_amount in badges.keys():
        threshold_voucher_amount = reward_thresholds.get(threshold_amount)
        if threshold_voucher_amount:
            # Check if user has a voucher with this amount (indicating they earned this milestone)
            has_voucher = user_vouchers.filter(
                discount_value=Decimal(str(threshold_voucher_amount))
            ).exists()
            if has_voucher:
                earned_milestones.add(threshold_amount)
    
    return earned_milestones


def get_badge_for_cumulative_amount(cumulative_amount, earned_milestones=None):
    """
    Get badge information for cumulative spending amount.
    Only returns badges that haven't been earned yet.
    
    Args:
        cumulative_amount: Decimal - Cumulative spending amount
        earned_milestones: Optional set of already earned milestone thresholds
        
    Returns:
        dict: Badge information for the highest unearned milestone, or None
    """
    if not hasattr(settings, 'REWARD_BADGES'):
        return None
    
    badges = settings.REWARD_BADGES
    if not badges:
        return None
    
    if earned_milestones is None:
        earned_milestones = set()
    
    # Find the highest badge threshold that the cumulative amount meets
    # but hasn't been earned yet
    qualifying_threshold = None
    for threshold_amount in sorted(badges.keys(), reverse=True):
        if cumulative_amount >= Decimal(str(threshold_amount)):
            # Only return if this milestone hasn't been earned yet
            if threshold_amount not in earned_milestones:
                qualifying_threshold = threshold_amount
                break
    
    if qualifying_threshold:
        badge_info = badges[qualifying_threshold].copy()
        badge_info['threshold'] = qualifying_threshold
        return badge_info
    
    return None


def get_badge_for_amount(amount):
    """
    Get badge information for a purchase amount.
    DEPRECATED: Use get_badge_for_cumulative_amount instead.
    Kept for backward compatibility.
    
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
        logger.error(f"Failed to generate unique voucher code for user {user.id}")
        return None
    
    # Get or create a superuser for created_by (or use None)
    superuser = Superuser.objects.filter(is_superuser=True).first()
    
    # Build accurate description based on milestone achievement
    if badge_info:
        threshold = badge_info.get('threshold', 0)
        badge_name = badge_info.get('name', 'milestone')
        description = (
            f"Congratulations! You've reached ${threshold:,.0f} in total spending and earned the "
            f"{badge_name} badge! As a reward, you've received a ${amount} discount voucher. "
            f"Use this voucher on your next purchase!"
        )
    else:
        # Fallback description if no badge info
        description = (
            f"Reward voucher for reaching a spending milestone! "
            f"You've received a ${amount} discount voucher as a reward."
        )
    
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
    Get all badges earned by a user based on cumulative spending.
    Badges are earned based on cumulative spending (like XP system).
    Only returns badges that have been earned (user has voucher for them).
    
    Args:
        user: Customer instance
        
    Returns:
        list: List of badge dictionaries for all earned badges
    """
    if not hasattr(settings, 'REWARD_BADGES'):
        return []
    
    badges = settings.REWARD_BADGES
    if not badges:
        return []
    
    # Get milestones that have already been earned (have vouchers)
    earned_milestones = get_earned_milestones(user)
    
    # Return all badges that have been earned
    earned_badges = []
    for threshold_amount in sorted(badges.keys()):
        if threshold_amount in earned_milestones:
            badge_info = badges[threshold_amount].copy()
            badge_info['threshold'] = threshold_amount
            earned_badges.append(badge_info)
    
    return earned_badges


def get_milestone_progress(user):
    """
    Get user's progress towards the next milestone badge.
    Uses cumulative spending (like XP system) instead of highest single order.
    
    Args:
        user: Customer instance
        
    Returns:
        dict: Progress information with:
            - current_badge: Highest badge earned (or None)
            - next_badge: Next badge to earn (or None)
            - progress_percentage: Percentage towards next badge (0-100)
            - current_amount: Cumulative spending amount
            - next_threshold: Next threshold to reach
            - amount_needed: Amount needed to reach next threshold
    """
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
    
    # Calculate cumulative spending (sum of all order subtotals)
    cumulative_spending = get_cumulative_spending(user)
    
    # Get reward thresholds to include voucher amounts
    reward_thresholds = getattr(settings, 'REWARD_THRESHOLDS', {})
    
    # Find current badge (highest threshold achieved)
    # Show the highest milestone reached, even if voucher hasn't been created yet
    # (voucher will be created by the signal when order is processed)
    current_badge = None
    current_threshold = None
    sorted_thresholds = sorted(badges.keys())
    
    # Iterate in reverse to find the highest threshold achieved
    for threshold_amount in reversed(sorted_thresholds):
        threshold_decimal = Decimal(str(threshold_amount))
        if cumulative_spending >= threshold_decimal:
            current_threshold = threshold_amount
            badge_info = badges[threshold_amount].copy()
            badge_info['threshold'] = threshold_amount
            if threshold_amount in reward_thresholds:
                badge_info['voucher_amount'] = float(reward_thresholds[threshold_amount])
            current_badge = badge_info
            break
    
  
    next_badge = None
    next_threshold = None
    
    # If user has no current badge, next badge is always the first (lowest) threshold
    if current_badge is None:
        if sorted_thresholds:
            next_threshold = sorted_thresholds[0]
            badge_info = badges[next_threshold].copy()
            badge_info['threshold'] = next_threshold
            if next_threshold in reward_thresholds:
                badge_info['voucher_amount'] = float(reward_thresholds[next_threshold])
            next_badge = badge_info
    else:
        # User has a badge, find the next one they haven't reached
        for threshold_amount in sorted_thresholds:
            threshold_decimal = Decimal(str(threshold_amount))
            if cumulative_spending < threshold_decimal:
                next_threshold = threshold_amount
                badge_info = badges[threshold_amount].copy()
                badge_info['threshold'] = threshold_amount
                if threshold_amount in reward_thresholds:
                    badge_info['voucher_amount'] = float(reward_thresholds[threshold_amount])
                next_badge = badge_info
                break
    
    # Calculate progress towards next badge
    progress_percentage = 0
    amount_needed = 0
    
    if next_badge and next_threshold:
        amount_needed = Decimal(str(next_threshold)) - cumulative_spending
        if amount_needed < 0:
            amount_needed = Decimal('0')
        
        # Calculate percentage (0-100)
        if next_threshold > 0:
            progress_percentage = float((cumulative_spending / Decimal(str(next_threshold))) * 100)
            if progress_percentage > 100:
                progress_percentage = 100
            if progress_percentage < 0:
                progress_percentage = 0
    
    return {
        'current_badge': current_badge,
        'next_badge': next_badge,
        'progress_percentage': round(progress_percentage, 1),
        'current_amount': float(cumulative_spending),
        'next_threshold': next_threshold,
        'amount_needed': float(amount_needed) if amount_needed else 0
    }


def get_all_milestones_progress(user):
    """
    Get progress for all milestone badges.
    Uses cumulative spending (like XP system) instead of highest single order.
    
    Args:
        user: Customer instance
        
    Returns:
        list: List of milestone progress dictionaries, one for each badge threshold
    """
    if not hasattr(settings, 'REWARD_BADGES'):
        return []
    
    badges = settings.REWARD_BADGES
    if not badges:
        return []
    
    # Calculate cumulative spending (like XP system)
    cumulative_spending = get_cumulative_spending(user)
    
    # Get milestones that have already been earned
    earned_milestones = get_earned_milestones(user)
    
    # Get progress for each milestone
    milestones = []
    sorted_thresholds = sorted(badges.keys())
    
    for threshold_amount in sorted_thresholds:
        badge_info = badges[threshold_amount].copy()
        badge_info['threshold'] = threshold_amount
        
        # Check if earned (both reached threshold and has voucher)
        is_earned = threshold_amount in earned_milestones
        
        # Calculate progress percentage
        if is_earned:
            progress_percentage = 100.0
            amount_needed = 0
        else:
            # Calculate progress towards this milestone
            if threshold_amount > 0:
                progress_percentage = float((cumulative_spending / Decimal(str(threshold_amount))) * 100)
                if progress_percentage > 100:
                    progress_percentage = 100
                if progress_percentage < 0:
                    progress_percentage = 0
            else:
                progress_percentage = 0
            
            amount_needed = float(Decimal(str(threshold_amount)) - cumulative_spending)
            if amount_needed < 0:
                amount_needed = 0
        
        milestones.append({
            'badge': badge_info,
            'is_earned': is_earned,
            'progress_percentage': round(progress_percentage, 1),
            'current_amount': float(cumulative_spending),
            'threshold': threshold_amount,
            'amount_needed': amount_needed if not is_earned else 0
        })
    
    return milestones
