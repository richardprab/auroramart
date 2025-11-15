from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from .models import Voucher, VoucherUsage
from .rewards import get_milestone_progress
import math


def get_voucher_status(voucher, user):
    is_valid = voucher.is_valid()
    
    if not is_valid:
        return 'expired'
    
    usage_count = VoucherUsage.objects.filter(
        voucher=voucher,
        user=user
    ).count()
    
    if usage_count >= voucher.max_uses_per_user:
        return 'used'
    
    can_use = voucher.can_be_used_by_user(user, usage_count=usage_count)
    if not can_use:
        return 'unavailable'
    
    return 'available'


@login_required
def my_vouchers(request):
    """
    Display all vouchers available to the current user.
    Shows both public vouchers and user-specific vouchers.
    """
    from vouchers.rewards import check_and_grant_milestone_vouchers
    from django.contrib import messages
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        newly_created = check_and_grant_milestone_vouchers(request.user)
        if newly_created:
            messages.success(
                request, 
                f"Congratulations! You've earned {len(newly_created)} new milestone voucher(s)!"
            )
    except Exception as e:
        logger.error(f"Error checking milestone vouchers: {str(e)}", exc_info=True)
    
    now = timezone.now()
    
    # Get user-specific vouchers
    user_vouchers = Voucher.objects.filter(
        user=request.user,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at')
    
    # Get public vouchers (no user assigned)
    public_vouchers = Voucher.objects.filter(
        user__isnull=True,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at')
    
    # Get used vouchers for this user
    used_vouchers = Voucher.objects.filter(
        usages__user=request.user
    ).distinct().order_by('-usages__used_at')
    
    # Get expired vouchers
    expired_vouchers = Voucher.objects.filter(
        Q(user=request.user) | Q(user__isnull=True),
        is_active=True
    ).filter(
        Q(end_date__lt=now) | Q(start_date__gt=now)
    ).order_by('-end_date')
    
    # Add status to each voucher
    def add_status_to_voucher(voucher):
        voucher.status = get_voucher_status(voucher, request.user)
        return voucher
    
    user_vouchers = [add_status_to_voucher(v) for v in user_vouchers]
    public_vouchers = [add_status_to_voucher(v) for v in public_vouchers]
    used_vouchers = [add_status_to_voucher(v) for v in used_vouchers]
    expired_vouchers = [add_status_to_voucher(v) for v in expired_vouchers]
    
    context = {
        'user_vouchers': user_vouchers,
        'public_vouchers': public_vouchers,
        'used_vouchers': used_vouchers,
        'expired_vouchers': expired_vouchers,
    }
    
    return render(request, 'vouchers/my_vouchers.html', context)


@login_required
def voucher_detail(request, voucher_id):
    """
    Display details of a specific voucher.
    """
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    # Check if user can access this voucher
    if voucher.user and voucher.user != request.user:
        return redirect('vouchers:my_vouchers')
    
    # Get usage history for this user
    usage_history = VoucherUsage.objects.filter(
        voucher=voucher,
        user=request.user
    ).order_by('-used_at')
    
    # Check if user can use this voucher
    is_valid = voucher.is_valid()
    usage_count = VoucherUsage.objects.filter(
        voucher=voucher,
        user=request.user
    ).count()
    
    # Pass usage_count to avoid duplicate query
    can_use = voucher.can_be_used_by_user(request.user, usage_count=usage_count)
    
    context = {
        'voucher': voucher,
        'usage_history': usage_history,
        'can_use': can_use,
        'is_valid': is_valid,
        'usage_count': usage_count,
        'remaining_uses': max(0, voucher.max_uses_per_user - usage_count),
    }
    
    return render(request, 'vouchers/voucher_detail.html', context)


@login_required
def my_vouchers_json(request):
    """
    AJAX endpoint to get all vouchers for the current user (for popup display).
    Returns available, used, and expired vouchers.
    """
    from vouchers.rewards import check_and_grant_milestone_vouchers
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        check_and_grant_milestone_vouchers(request.user)
    except Exception as e:
        logger.error(f"Error checking milestone vouchers: {str(e)}", exc_info=True)
    
    now = timezone.now()
    
    # Get user-specific vouchers
    user_vouchers = Voucher.objects.filter(
        user=request.user,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at')
    
    # Get public vouchers (no user assigned)
    public_vouchers = Voucher.objects.filter(
        user__isnull=True,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at')
    
    # Get used vouchers for this user
    used_vouchers = Voucher.objects.filter(
        usages__user=request.user
    ).distinct().order_by('-usages__used_at')
    
    # Get expired vouchers
    expired_vouchers = Voucher.objects.filter(
        Q(user=request.user) | Q(user__isnull=True),
        is_active=True
    ).filter(
        Q(end_date__lt=now) | Q(start_date__gt=now)
    ).order_by('-end_date')
    
    def voucher_to_dict(voucher):
        usage_count = VoucherUsage.objects.filter(
            voucher=voucher,
            user=request.user
        ).count()
        
        return {
            'id': voucher.id,
            'promo_code': voucher.promo_code,
            'name': voucher.name,
            'description': voucher.description or '',
            'discount_type': voucher.discount_type,
            'discount_value': str(voucher.discount_value),
            'max_discount': str(voucher.max_discount) if voucher.max_discount else None,
            'end_date': voucher.end_date.strftime('%b %d, %Y'),
            'status': get_voucher_status(voucher, request.user),
            'remaining_uses': max(0, voucher.max_uses_per_user - usage_count),
        }
    
    # Filter used vouchers to only include those that are completely used up
    def is_fully_used(voucher):
        usage_count = VoucherUsage.objects.filter(
            voucher=voucher,
            user=request.user
        ).count()
        return usage_count >= voucher.max_uses_per_user
    
    # Combine all vouchers and categorize them properly
    all_vouchers_list = list(user_vouchers) + list(public_vouchers) + list(used_vouchers) + list(expired_vouchers)
    seen_ids = set()
    unique_vouchers = []
    for v in all_vouchers_list:
        if v.id not in seen_ids:
            seen_ids.add(v.id)
            unique_vouchers.append(v)
    
    # Categorize vouchers
    available_list = []
    used_list = []
    expired_list = []
    
    for voucher in unique_vouchers:
        status = get_voucher_status(voucher, request.user)
        if status == 'available':
            available_list.append(voucher_to_dict(voucher))
        elif status == 'used':
            # Only include if fully used up
            if is_fully_used(voucher):
                used_list.append(voucher_to_dict(voucher))
        elif status == 'expired':
            expired_list.append(voucher_to_dict(voucher))
    
    return JsonResponse({
        'success': True,
        'available': available_list,
        'used': used_list,
        'expired': expired_list,
    })


@login_required
def voucher_detail_json(request, voucher_id):
    """
    AJAX endpoint to get detailed voucher information for modal display.
    """
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    # Check if user can access this voucher
    if voucher.user and voucher.user != request.user:
        return JsonResponse({'success': False, 'error': 'You do not have access to this voucher.'}, status=403)
    
    # Get usage history for this user
    usage_history = VoucherUsage.objects.filter(
        voucher=voucher,
        user=request.user
    ).order_by('-used_at').select_related('order')[:10]  # Limit to last 10
    
    # Check if user can use this voucher
    is_valid = voucher.is_valid()
    usage_count = VoucherUsage.objects.filter(
        voucher=voucher,
        user=request.user
    ).count()
    
    can_use = voucher.can_be_used_by_user(request.user, usage_count=usage_count)
    
    # Get applicable products/categories
    applicable_products = list(voucher.applicable_products.values_list('name', flat=True)[:5])
    applicable_categories = list(voucher.applicable_categories.values_list('name', flat=True)[:5])
    
    return JsonResponse({
        'success': True,
        'voucher': {
            'id': voucher.id,
            'name': voucher.name,
            'promo_code': voucher.promo_code,
            'description': voucher.description or '',
            'discount_type': voucher.discount_type,
            'discount_value': str(voucher.discount_value),
            'max_discount': str(voucher.max_discount) if voucher.max_discount else None,
            'min_purchase': str(voucher.min_purchase) if voucher.min_purchase else None,
            'start_date': voucher.start_date.strftime('%b %d, %Y'),
            'end_date': voucher.end_date.strftime('%b %d, %Y'),
            'is_valid': is_valid,
            'can_use': can_use,
            'usage_count': usage_count,
            'max_uses_per_user': voucher.max_uses_per_user,
            'remaining_uses': max(0, voucher.max_uses_per_user - usage_count),
            'first_time_only': voucher.first_time_only,
            'exclude_sale_items': voucher.exclude_sale_items,
            'applicable_products': applicable_products,
            'applicable_categories': applicable_categories,
        },
        'usage_history': [
            {
                'order_number': usage.order.order_number if usage.order else 'N/A',
                'order_id': usage.order.id if usage.order else None,
                'discount_amount': str(usage.discount_amount),
                'used_at': usage.used_at.strftime('%b %d, %Y %I:%M %p'),
            }
            for usage in usage_history
        ],
    })


@login_required
def get_milestone_progress_api(request):
    """API endpoint for milestone progress (badge and progress bar)"""
    from vouchers.rewards import check_and_grant_milestone_vouchers
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        check_and_grant_milestone_vouchers(request.user)
    except Exception as e:
        logger.error(f"Error checking milestone vouchers: {str(e)}", exc_info=True)
    
    try:
        progress = get_milestone_progress(request.user)
        
        # Calculate circular progress offset for donut-style progress bar
        if progress.get('next_badge') and progress.get('progress_percentage') is not None:
            # Full circle circumference: 2 * π * r (for radius 50)
            circumference = 2 * math.pi * 50  # ≈ 314.16
            # Calculate offset: when progress is 0%, show nothing (offset = full circumference)
            # When progress is 100%, show full circle (offset = 0)
            progress['circular_offset'] = round(
                circumference - (progress['progress_percentage'] / 100 * circumference), 
                2
            )
        else:
            progress['circular_offset'] = 314.16  # Full offset (no progress)
        
        return JsonResponse({
            'success': True,
            'milestone_progress': progress
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'milestone_progress': {
                'current_badge': None,
                'next_badge': None,
                'progress_percentage': 0,
                'current_amount': 0,
                'next_threshold': None,
                'amount_needed': 0,
                'circular_offset': 314.16  # For radius 50
            },
            'error': str(e)
        })

