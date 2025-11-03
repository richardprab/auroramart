/* ========================================
   WISHLIST - Wishlist functionality
   ======================================== */

const WishlistModule = {
    init() {
        this.toggleWishlist();
        this.updateWishlistCount();
    },

    // Toggle wishlist
    toggleWishlist() {
        const buttons = document.querySelectorAll('[data-wishlist-toggle]');

        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const productId = button.dataset.productId;
                const isAdded = button.classList.contains('in-wishlist');

                if (isAdded) {
                    this.removeFromWishlist(productId, button);
                } else {
                    this.addToWishlist(productId, button);
                }
            });
        });
    },

    // Add to wishlist
    addToWishlist(productId, button) {
        const form = button.closest('form');
        const formData = new FormData(form);

        // Optimistic UI update
        button.classList.add('in-wishlist');
        button.innerHTML = '❤️';

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
                    this.updateWishlistCount();

                    // Heart animation
                    button.style.animation = 'pulse 0.5s ease';
                    setTimeout(() => {
                        button.style.animation = '';
                    }, 500);
                } else {
                    // Revert on error
                    button.classList.remove('in-wishlist');
                    button.innerHTML = '🤍';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.classList.remove('in-wishlist');
                button.innerHTML = '🤍';
            });
    },

    // Remove from wishlist
    removeFromWishlist(productId, button) {
        const form = button.closest('form');
        const formData = new FormData(form);

        // Optimistic UI update
        button.classList.remove('in-wishlist');
        button.innerHTML = '🤍';

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
                    this.updateWishlistCount();

                    // If on wishlist page, remove the card
                    const productCard = button.closest('.product-card');
                    if (productCard && window.location.pathname.includes('wishlist')) {
                        productCard.style.animation = 'fadeOut 0.3s ease-out';
                        setTimeout(() => {
                            productCard.remove();

                            // Show empty state if no items left
                            if (document.querySelectorAll('.product-card').length === 0) {
                                this.showEmptyWishlist();
                            }
                        }, 300);
                    }
                } else {
                    // Revert on error
                    button.classList.add('in-wishlist');
                    button.innerHTML = '❤️';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.classList.add('in-wishlist');
                button.innerHTML = '❤️';
            });
    },

    // Update wishlist count
    updateWishlistCount() {
        const badge = document.querySelector('.wishlist-badge');
        if (!badge) return;

        // This should fetch from your backend
        fetch('/api/wishlist/count/')
            .then(response => response.json())
            .then(data => {
                badge.textContent = data.count;
                if (data.count > 0) {
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            })
            .catch(error => console.error('Error:', error));
    },

    // Show empty wishlist state
    showEmptyWishlist() {
        const container = document.querySelector('.wishlist-container');
        if (!container) return;

        container.innerHTML = `
            <div class="empty-cart">
                <div class="empty-cart-icon">❤️</div>
                <h2 class="empty-cart-title">Your wishlist is empty</h2>
                <p class="empty-cart-text">Save your favorite items and never lose track of them!</p>
                <a href="/products/" class="btn btn-primary">Start Shopping</a>
            </div>
        `;
    }
};

// Export
window.WishlistModule = WishlistModule;