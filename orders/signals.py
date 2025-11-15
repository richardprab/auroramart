"""
Signals for the orders app.
Handles reward voucher generation when orders are completed.
"""
from django.db.models.signals import post_save
from django.db import transaction
from django.dispatch import receiver
from .models import Order
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def generate_reward_on_order_completion(sender, instance, created, **kwargs):
    """
    Generate reward voucher when an order is completed (delivered or confirmed).
    This signal is triggered after an order is saved.
    """
    from vouchers.rewards import (
        should_generate_reward,
        calculate_reward_voucher_amount,
        get_badge_for_amount,
        create_reward_voucher
    )
    
    # Check if order qualifies for reward
    if not should_generate_reward(instance):
        return
    
    # Use transaction.on_commit to ensure order is fully saved
    def generate_reward():
        try:
            # Calculate voucher amount
            voucher_amount = calculate_reward_voucher_amount(instance.subtotal)
            if voucher_amount is None:
                return
            
            # Get badge info for this purchase
            badge_info = get_badge_for_amount(instance.subtotal)
            
            # Check if user already has a reward voucher for this order
            # (prevent duplicate vouchers if signal fires multiple times)
            existing_vouchers = instance.user.vouchers.filter(
                promo_code__startswith=f"REWARD-{instance.user.id}-"
            )
            
            # Check if we already generated a voucher for this order amount
            # by checking if there's a recent voucher with the same amount
            from django.utils import timezone
            from datetime import timedelta
            recent_vouchers = existing_vouchers.filter(
                discount_value=voucher_amount,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            )
            
            if recent_vouchers.exists():
                logger.info(f"Reward voucher already exists for order {instance.order_number}")
                return
            
            # Create the reward voucher
            voucher = create_reward_voucher(
                user=instance.user,
                amount=voucher_amount,
                order=instance,
                badge_info=badge_info
            )
            
            if voucher:
                logger.info(
                    f"✅ Generated reward voucher {voucher.promo_code} "
                    f"(${voucher_amount}) for order {instance.order_number} "
                    f"(user: {instance.user.username})"
                )
                
                if badge_info:
                    logger.info(
                        f"   Badge earned: {badge_info['name']} "
                        f"(threshold: ${badge_info['threshold']})"
                    )
            else:
                logger.error(
                    f"❌ Failed to create reward voucher for order {instance.order_number}"
                )
                
        except Exception as e:
            logger.error(
                f"❌ Error generating reward voucher for order {instance.order_number}: {str(e)}",
                exc_info=True
            )
    
    # Execute after transaction commits
    transaction.on_commit(generate_reward)

