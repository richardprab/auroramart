/* ========================================
   CART - Shopping cart functionality
   ======================================== */

const CartModule = {
    init() {
        this.updateCartCount();
        this.addToCartButtons();
        this.removeFromCart();
        this.updateQuantity();
        this.clearCart();
    },

    // Update cart count badge
    updateCartCount() {
        fetch('/cart/count/')
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('cart-count');
                if (badge) {
                    badge.textContent = data.count || 0;
                    // Show/hide badge based on count
                    if (data.count > 0) {
                        badge.classList.remove('hidden');
                    } else {
                        badge.classList.add('hidden');
                    }
                }
            })
            .catch(error => console.error('Error fetching cart count:', error));
    },

    // Get cart count
    getCartCount() {
        // This should fetch from your backend
        // For now, using localStorage as example
        const cart = JSON.parse(localStorage.getItem('cart') || '[]');
        return cart.reduce((total, item) => total + item.quantity, 0);
    },

    // Add to cart functionality
    addToCartButtons() {
        const buttons = document.querySelectorAll('[data-add-to-cart]');

        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();

                const productId = button.dataset.productId ||
                    button.closest('form').querySelector('[name="product_id"]')?.value;

                if (!productId) {
                    console.error('Product ID not found');
                    return;
                }

                this.addToCart(productId, button);
            });
        });
    },

    // Add to cart with animation
    addToCart(productId, button) {
        const form = button.closest('form');
        const formData = new FormData(form);

        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="loading-spinner"></span>';
        button.disabled = true;

        // Submit form via AJAX
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Flying cart animation
                    this.flyToCartAnimation(button);

                    // Update cart count
                    this.updateCartCount();
                } else {
                    AuroraMart.toast(data.message || 'Failed to add to cart', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                AuroraMart.toast('Something went wrong', 'error');
            })
            .finally(() => {
                // Restore button
                button.innerHTML = originalText;
                button.disabled = false;
            });
    },

    // Flying cart animation
    flyToCartAnimation(button) {
        const rect = button.getBoundingClientRect();
        const cartBadge = document.querySelector('#cart-count');

        const cartIcon = cartBadge.closest('a');
        const cartRect = cartIcon.getBoundingClientRect();

        const flyingIcon = document.createElement('div');
        flyingIcon.innerHTML = '🛒';
        flyingIcon.style.cssText = `
            position: fixed;
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top + rect.height / 2}px;
            font-size: 30px;
            z-index: 9999;
            pointer-events: none;
            transition: all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        `;

        document.body.appendChild(flyingIcon);

        // Animate to cart
        setTimeout(() => {
            flyingIcon.style.left = `${cartRect.left}px`;
            flyingIcon.style.top = `${cartRect.top}px`;
            flyingIcon.style.transform = 'scale(0)';
            flyingIcon.style.opacity = '0';
        }, 10);

        // Remove after animation
        setTimeout(() => {
            flyingIcon.remove();

            // Pulse cart badge
            if (cartBadge) {
                cartBadge.style.animation = 'none';
                setTimeout(() => {
                    cartBadge.style.animation = 'pulse 0.5s ease';
                }, 10);
            }
        }, 1000);
    },

    // Remove from cart
    removeFromCart() {
        const removeButtons = document.querySelectorAll('[data-remove-from-cart]');

        removeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();

                if (confirm('Remove this item from cart?')) {
                    const form = button.closest('form');
                    const formData = new FormData(form);

                    fetch(form.action, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                        }
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Remove item with animation
                                const cartItem = button.closest('.cart-item');
                                cartItem.style.animation = 'slideOut 0.3s ease-out';

                                setTimeout(() => {
                                    cartItem.remove();
                                    this.updateCartCount();
                                    this.updateCartTotal();
                                    AuroraMart.toast('Item removed', 'info');
                                }, 300);
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            AuroraMart.toast('Failed to remove item', 'error');
                        });
                }
            });
        });
    },

    // Update quantity
    updateQuantity() {
        const quantityInputs = document.querySelectorAll('.cart-item input[type="number"]');

        quantityInputs.forEach(input => {
            input.addEventListener('change', AuroraMart.debounce(() => {
                const form = input.closest('form');
                const formData = new FormData(form);

                fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.updateCartTotal();
                            this.updateCartCount();
                            AuroraMart.toast('Cart updated', 'success');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        AuroraMart.toast('Failed to update quantity', 'error');
                    });
            }, 500));
        });
    },

    // Update cart total
    updateCartTotal() {
        // Calculate and update cart totals
        let subtotal = 0;

        document.querySelectorAll('.cart-item').forEach(item => {
            const price = parseFloat(item.dataset.price || 0);
            const quantity = parseInt(item.querySelector('input[type="number"]')?.value || 0);
            subtotal += price * quantity;
        });

        // Update display
        const subtotalElement = document.querySelector('[data-cart-subtotal]');
        const totalElement = document.querySelector('[data-cart-total]');

        if (subtotalElement) {
            subtotalElement.textContent = AuroraMart.formatCurrency(subtotal);
        }

        if (totalElement) {
            // Add shipping, taxes, etc.
            const shipping = parseFloat(document.querySelector('[data-shipping]')?.textContent || 0);
            const total = subtotal + shipping;
            totalElement.textContent = AuroraMart.formatCurrency(total);
        }
    },

    // Clear cart
    clearCart() {
        const clearButton = document.querySelector('[data-clear-cart]');
        if (!clearButton) return;

        clearButton.addEventListener('click', (e) => {
            e.preventDefault();

            if (confirm('Are you sure you want to clear your cart?')) {
                const form = clearButton.closest('form');

                fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        AuroraMart.toast('Failed to clear cart', 'error');
                    });
            }
        });
    }
};

// Export
window.CartModule = CartModule;

// Update cart count on page load
document.addEventListener('DOMContentLoaded', () => {
    CartModule.updateCartCount();
});

// Listen for "Add to Cart" button clicks
document.addEventListener('click', function (e) {
    const addToCartBtn = e.target.closest('[data-add-to-cart]');
    if (addToCartBtn) {
        // Wait a moment for the form to submit, then update count
        setTimeout(() => {
            CartModule.updateCartCount();
        }, 500);
    }
});