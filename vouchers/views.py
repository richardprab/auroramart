from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from .models import Voucher, VoucherUsage


@login_required
def my_vouchers(request):
    """
    Display all vouchers available to the current user.
    Shows both public vouchers and user-specific vouchers.
    """
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
    
    # Check usage status for each voucher
    def get_voucher_status(voucher):
        is_valid = voucher.is_valid()
        
        if not is_valid:
            return 'expired'
        
        # Check usage count once and reuse it
        usage_count = VoucherUsage.objects.filter(
            voucher=voucher,
            user=request.user
        ).count()
        
        if usage_count >= voucher.max_uses_per_user:
            return 'used'
        
        # Check other restrictions (user-specific, first-time, etc.)
        # Pass usage_count to avoid duplicate query
        can_use = voucher.can_be_used_by_user(request.user, usage_count=usage_count)
        if not can_use:
            return 'unavailable'
        
        return 'available'
    
    # Add status to each voucher
    def add_status_to_voucher(voucher):
        voucher.status = get_voucher_status(voucher)
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

