const CartModule = {
    init() {
        this.updateCartCount();
        this.addToCartButtons();
    },

    // Get CSRF token helper
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : null;
    },

    // Update cart count badge
    updateCartCount() {
        const url = '/api/cart/count/';
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };
        
        fetch(url, { 
            headers,
            credentials: 'same-origin'
        })
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
        const variantId = form.querySelector('[name="variant_id"]')?.value;
        const quantity = form.querySelector('[name="quantity"]')?.value || 1;

        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="loading-spinner"></span>';
        button.disabled = true;

        // Prepare API request
        const url = '/api/cart/add_item/';
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };

        // Submit to API
        fetch(url, {
            method: 'POST',
            headers: headers,
            credentials: 'same-origin',
            body: JSON.stringify({
                product_id: productId,
                product_variant_id: variantId,
                quantity: parseInt(quantity)
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Flying cart animation
                    this.flyToCartAnimation(button);

                    // Update cart count
                    this.updateCartCount();
                }
            })
            .catch(error => {
                console.error('Error:', error);
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