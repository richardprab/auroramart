/**
 * Wishlist Module
 * Handles wishlist operations including add, remove, and UI updates
 */
const WishlistModule = {
    // Constants
    ANIMATION_DURATION: 500,
    FLYING_ANIMATION_DURATION: 800,
    CARD_REMOVE_DELAY: 300,
    
    // Icon templates
    ICONS: {
        WISHLISTED: '<i data-lucide="heart" class="w-5 h-5 text-red-500 fill-current"></i>',
        NOT_WISHLISTED: '<i data-lucide="heart" class="w-5 h-5 text-gray-600 hover:text-red-500"></i>'
    },

    /**
     * Initialize wishlist module
     */
    init() {
        this.attachEventListeners();
        this.updateWishlistCount();
    },

    /**
     * Get CSRF token from cookies
     * @returns {string|null} CSRF token
     */
    getCSRFToken() {
        return Utils?.getCookie('csrftoken') || this.getCookieFallback('csrftoken');
    },

    /**
     * Fallback method to get cookie if Utils not available
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value
     */
    getCookieFallback(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    },

    /**
     * Attach event listeners to wishlist toggle buttons
     */
    attachEventListeners() {
        const forms = document.querySelectorAll('[data-wishlist-toggle]');

        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const button = form.querySelector('button[type="submit"]');
                const productId = button?.dataset.productId;
                
                if (!productId) {
                    console.error('Product ID not found');
                    return;
                }

                const isWishlisted = button.classList.contains('in-wishlist');

                if (isWishlisted) {
                    this.removeFromWishlist(productId, button, form);
                } else {
                    this.addToWishlist(productId, button, form);
                }
            });
        });
    },

    /**
     * Add product to wishlist
     * @param {string} productId - Product ID
     * @param {HTMLElement} button - Button element
     * @param {HTMLElement} form - Form element
     */
    addToWishlist(productId, button, form) {
        // Optimistic UI update
        this.updateButtonState(button, true);

        const formData = new FormData(form);
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': this.getCSRFToken()
        };

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: headers,
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.handleAddSuccess(button);
                } else {
                    this.handleAddError(button, data.message);
                }
            })
            .catch(error => {
                console.error('Error adding to wishlist:', error);
                this.handleAddError(button);
            });
    },

    /**
     * Remove product from wishlist
     * @param {string} productId - Product ID
     * @param {HTMLElement} button - Button element
     * @param {HTMLElement} form - Form element
     */
    removeFromWishlist(productId, button, form) {
        // Optimistic UI update
        this.updateButtonState(button, false);

        const formData = new FormData(form);
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': this.getCSRFToken()
        };

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: headers,
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.handleRemoveSuccess(button);
                } else {
                    this.handleRemoveError(button);
                }
            })
            .catch(error => {
                console.error('Error removing from wishlist:', error);
                this.handleRemoveError(button);
            });
    },

    /**
     * Update button visual state
     * @param {HTMLElement} button - Button element
     * @param {boolean} isWishlisted - Whether item is wishlisted
     */
    updateButtonState(button, isWishlisted) {
        if (isWishlisted) {
            button.classList.add('in-wishlist');
            button.innerHTML = this.ICONS.WISHLISTED;
        } else {
            button.classList.remove('in-wishlist');
            button.innerHTML = this.ICONS.NOT_WISHLISTED;
        }
        this.reinitializeLucideIcons();
    },

    /**
     * Handle successful add to wishlist
     * @param {HTMLElement} button - Button element
     */
    handleAddSuccess(button) {
        this.playHeartAnimation(button);
        this.playFlyingAnimation(button);
        this.updateWishlistCount();
    },

    /**
     * Handle failed add to wishlist
     * @param {HTMLElement} button - Button element
     * @param {string} message - Error message
     */
    handleAddError(button, message = 'Failed to add to wishlist') {
        console.error(message);
        this.updateButtonState(button, false);
    },

    /**
     * Handle successful remove from wishlist
     * @param {HTMLElement} button - Button element
     */
    handleRemoveSuccess(button) {
        this.updateWishlistCount();
        this.handleWishlistPageRemoval(button);
    },

    /**
     * Handle failed remove from wishlist
     * @param {HTMLElement} button - Button element
     */
    handleRemoveError(button) {
        this.updateButtonState(button, true);
    },

    /**
     * Handle product card removal on wishlist page
     * @param {HTMLElement} button - Button element
     */
    handleWishlistPageRemoval(button) {
        if (!window.location.pathname.includes('wishlist')) return;

        const productCard = button.closest('.product-card');
        if (!productCard) return;

        // Animate card removal
        productCard.style.transition = 'all 0.3s ease-out';
        productCard.style.transform = 'scale(0.9)';
        productCard.style.opacity = '0';

        setTimeout(() => {
            productCard.remove();
            this.checkEmptyWishlist();
        }, this.CARD_REMOVE_DELAY);
    },

    /**
     * Check if wishlist is empty and show empty state
     */
    checkEmptyWishlist() {
        const remainingCards = document.querySelectorAll('.product-card');
        if (remainingCards.length === 0) {
            this.showEmptyWishlist();
        }
    },

    /**
     * Play heart pulse animation
     * @param {HTMLElement} button - Button element
     */
    playHeartAnimation(button) {
        button.style.animation = `pulse ${this.ANIMATION_DURATION}ms ease`;
        setTimeout(() => {
            button.style.animation = '';
        }, this.ANIMATION_DURATION);
    },

    /**
     * Play flying heart animation to navbar
     * @param {HTMLElement} button - Button element
     */
    playFlyingAnimation(button) {
        const buttonRect = button.getBoundingClientRect();
        const wishlistIcon = document.querySelector('a[href*="wishlist"]');
        
        if (!wishlistIcon) return;
        
        const iconRect = wishlistIcon.getBoundingClientRect();
        const flyingHeart = this.createFlyingHeart(buttonRect);

        document.body.appendChild(flyingHeart);

        // Trigger animation
        requestAnimationFrame(() => {
            flyingHeart.style.left = `${iconRect.left + iconRect.width / 2}px`;
            flyingHeart.style.top = `${iconRect.top + iconRect.height / 2}px`;
            flyingHeart.style.transform = 'scale(0)';
            flyingHeart.style.opacity = '0';
        });

        // Remove element after animation
        setTimeout(() => {
            if (flyingHeart.parentNode) {
                document.body.removeChild(flyingHeart);
            }
        }, this.FLYING_ANIMATION_DURATION + 200);
    },

    /**
     * Create flying heart element
     * @param {DOMRect} rect - Starting position rectangle
     * @returns {HTMLElement} Flying heart element
     */
    createFlyingHeart(rect) {
        const flyingHeart = document.createElement('div');
        flyingHeart.innerHTML = '❤️';
        flyingHeart.style.cssText = `
            position: fixed;
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top + rect.height / 2}px;
            font-size: 30px;
            z-index: 9999;
            pointer-events: none;
            transition: all ${this.FLYING_ANIMATION_DURATION}ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
        `;
        return flyingHeart;
    },

    /**
     * Update wishlist count badge in navbar
     */
    updateWishlistCount() {
        const badge = document.getElementById('wishlist-count');
        if (!badge) return;

        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };

        fetch('/accounts/ajax/wishlist/count/', {
            headers: headers,
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                badge.textContent = data.count || 0;
                badge.classList.remove('hidden');
            })
            .catch(error => {
                console.error('Error fetching wishlist count:', error);
            });
    },

    /**
     * Show empty wishlist state
     */
    showEmptyWishlist() {
        const container = document.querySelector('.wishlist-container');
        if (!container) {
            // Reload page if container not found (fallback)
            window.location.reload();
            return;
        }

        container.innerHTML = `
            <div class="empty-cart">
                <div class="empty-cart-icon">❤️</div>
                <h2 class="empty-cart-title">Your wishlist is empty</h2>
                <p class="empty-cart-text">Save your favorite items and never lose track of them!</p>
                <a href="/products/" class="btn btn-primary">Start Shopping</a>
            </div>
        `;
    },

    /**
     * Reinitialize Lucide icons after DOM update
     */
    reinitializeLucideIcons() {
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }
};

// Export to window object
window.WishlistModule = WishlistModule;