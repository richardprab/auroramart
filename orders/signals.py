"""
Signals for the orders app.
Handles reward voucher generation when orders are completed.
"""
from django.db.models.signals import post_save
from django.db import transaction
from django.dispatch import receiver
from decimal import Decimal
from .models import Order
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def generate_reward_on_order_completion(sender, instance, created, **kwargs):
    """
    Generate reward voucher when a milestone is reached through cumulative spending.
    Uses cumulative spending (like XP system) - vouchers are given once per milestone.
    This signal is triggered after an order is saved.
    """
    from vouchers.rewards import (
        get_cumulative_spending,
        get_earned_milestones,
        get_badge_for_cumulative_amount,
        create_reward_voucher
    )
    from django.conf import settings
    
    # Only process delivered/confirmed orders (non-cancelled, non-refunded)
    if instance.status not in ['delivered', 'confirmed']:
        return
    if instance.status in ['cancelled', 'refunded']:
        return
    
    # Use transaction.on_commit to ensure order is fully saved
    def generate_reward():
        try:
            # Calculate cumulative spending after this order
            cumulative_spending = get_cumulative_spending(instance.user)
            
            # Get milestones already earned
            earned_milestones = get_earned_milestones(instance.user)
            
            # Check if user reached a new milestone
            badge_info = get_badge_for_cumulative_amount(cumulative_spending, earned_milestones)
            
            if badge_info is None:
                # No new milestone reached
                return
            
            # Get voucher amount for this milestone
            reward_thresholds = getattr(settings, 'REWARD_THRESHOLDS', {})
            threshold_amount = badge_info['threshold']
            voucher_amount = reward_thresholds.get(threshold_amount)
            
            if voucher_amount is None:
                return
            
            voucher_amount = Decimal(str(voucher_amount))
            
            # Double-check: verify user doesn't already have a voucher for this milestone
            # (prevent duplicate vouchers if signal fires multiple times)
            existing_vouchers = instance.user.vouchers.filter(
                promo_code__startswith=f"REWARD-{instance.user.id}-",
                discount_value=voucher_amount
            )
            
            if existing_vouchers.exists():
                logger.info(
                    f"Milestone voucher already exists for threshold ${threshold_amount} "
                    f"(user: {instance.user.username})"
                )
                return
            
            # Create the reward voucher for this milestone
            voucher = create_reward_voucher(
                user=instance.user,
                amount=voucher_amount,
                order=instance,
                badge_info=badge_info
            )
            
            if voucher:
                logger.info(
                    f"Generated milestone voucher {voucher.promo_code} "
                    f"(${voucher_amount}) for reaching {badge_info['name']} milestone "
                    f"(threshold: ${threshold_amount}, cumulative: ${cumulative_spending}) "
                    f"for order {instance.order_number} "
                    f"(user: {instance.user.username})"
                    )
            else:
                logger.error(
                    f"Failed to create milestone voucher for order {instance.order_number}"
                )
                
        except Exception as e:
            logger.error(
                f"Error generating milestone voucher for order {instance.order_number}: {str(e)}",
                exc_info=True
            )
    
    # Execute after transaction commits
    transaction.on_commit(generate_reward)
