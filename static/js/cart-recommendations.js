/**
 * Cart Recommendations Module
 * Handles ML-powered product recommendations on the cart page
 */
const CartRecommendationsModule = {
    // Configuration
    config: {
        initialDisplayCount: 8
    },

    // State
    state: {
        allRecommendations: [],
        isExpanded: false
    },

    // DOM Elements cache
    elements: {},

    /**
     * Initialize the module
     */
    init() {
        if (!this.hasCartItems()) {
            this.hideRecommendations();
            return;
        }

        this.cacheElements();
        this.loadRecommendations();
    },

    /**
     * Check if cart has items
     */
    hasCartItems() {
        return document.querySelectorAll('[data-remove-item]').length > 0;
    },

    /**
     * Cache DOM elements for performance
     */
    cacheElements() {
        this.elements = {
            section: document.getElementById('cart-recommendations-section'),
            loading: document.getElementById('cart-recommendations-loading'),
            content: document.getElementById('cart-recommendations-content'),
            empty: document.getElementById('cart-recommendations-empty'),
            grid: document.getElementById('cart-recommendations-grid'),
            viewAllContainer: document.getElementById('cart-recommendations-view-all'),
            viewAllBtn: document.getElementById('view-all-recommendations-btn')
        };
    },

    /**
     * Hide recommendations section
     */
    hideRecommendations() {
        Object.values(this.elements).forEach(el => {
            if (el) el.classList.add('hidden');
        });
    },

    /**
     * Load recommendations from API
     */
    async loadRecommendations() {
        this.showLoading();

        try {
            const response = await fetch('/recommendations/cart-recommendations/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.handleRecommendationsResponse(data);
        } catch (error) {
            console.error('Error loading recommendations:', error);
            this.hideRecommendations();
        }
    },

    /**
     * Handle recommendations API response
     */
    handleRecommendationsResponse(data) {
        this.hideLoading();

        if (!data.recommendations || data.recommendations.length === 0) {
            this.hideRecommendations();
            return;
        }

        this.state.allRecommendations = data.recommendations;
        this.showRecommendations();
    },

    /**
     * Show loading state
     */
    showLoading() {
        if (this.elements.loading) this.elements.loading.classList.remove('hidden');
        if (this.elements.content) this.elements.content.classList.add('hidden');
        if (this.elements.empty) this.elements.empty.classList.add('hidden');
        if (this.elements.viewAllContainer) this.elements.viewAllContainer.classList.add('hidden');
        if (this.elements.grid) this.elements.grid.innerHTML = '';
        
        this.state.isExpanded = false;
    },

    /**
     * Hide loading state
     */
    hideLoading() {
        if (this.elements.loading) this.elements.loading.classList.add('hidden');
    },

    /**
     * Show recommendations
     */
    showRecommendations() {
        if (this.elements.section) this.elements.section.classList.remove('hidden');
        if (this.elements.content) this.elements.content.classList.remove('hidden');

        this.displayRecommendations(this.config.initialDisplayCount);

        if (this.state.allRecommendations.length > this.config.initialDisplayCount) {
            this.showViewAllButton();
        }
    },

    /**
     * Display recommendations in grid
     */
    displayRecommendations(count) {
        if (!this.elements.grid) return;

        this.elements.grid.innerHTML = '';

        const productsToShow = this.state.isExpanded
            ? this.state.allRecommendations
            : this.state.allRecommendations.slice(0, count);

        productsToShow.forEach(product => {
            try {
                this.elements.grid.innerHTML += this.createProductCard(product);
            } catch (err) {
                console.error('Error creating product card:', err);
            }
        });

        this.initializeCardFeatures();
    },

    /**
     * Initialize features for dynamically added cards
     */
    initializeCardFeatures() {
        // Reinitialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Render star ratings
        if (typeof StarRating !== 'undefined') {
            StarRating.render(this.elements.grid);
        }

        // Attach event listeners
        this.attachEventListeners();
    },

    /**
     * Attach event listeners to cards
     */
    attachEventListeners() {
        if (window.WishlistModule) {
            window.WishlistModule.attachEventListeners();
        }
        this.attachAddToCartHandlers();
    },

    /**
     * Attach add to cart handlers with cart page specific behavior
     */
    attachAddToCartHandlers() {
        const buttons = this.elements.grid?.querySelectorAll('[data-add-to-cart]') || [];
        
        buttons.forEach(button => {
            if (button.hasAttribute('data-handler-attached')) return;
            button.setAttribute('data-handler-attached', 'true');

            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleAddToCart(button);
            });
        });
    },

    /**
     * Handle add to cart action
     */
    async handleAddToCart(button) {
        const form = button.closest('form');
        if (!form) return;

        const variantId = form.querySelector('[name="variant_id"]')?.value;
        const productId = button.getAttribute('data-product-id');

        if (!variantId) {
            if (window.toast) {
                window.toast.error('Please select a variant');
            }
            return;
        }

        this.setButtonLoading(button, true);

        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.handleAddToCartSuccess(productId, variantId);
                this.setButtonLoading(button, false);
            } else {
                this.handleAddToCartError(data.message || 'Failed to add to cart', button);
            }
        } catch (error) {
            console.error('Error:', error);
            this.handleAddToCartError('An error occurred. Please try again.', button);
        }
    },

    /**
     * Handle successful add to cart - update UI without page refresh
     */
    async handleAddToCartSuccess(productId, variantId) {
        // Update cart count
        if (window.CartModule) {
            window.CartModule.updateCartCount();
        }

        // Fetch updated cart data and add item to cart list
        await this.updateCartUI(productId, variantId);
    },

    /**
     * Update cart UI with new item - fetch updated cart and update DOM
     */
    async updateCartUI(productId, variantId) {
        try {
            // Fetch the cart page HTML to get updated cart
            const response = await fetch('/cart/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                // If fetch fails, silently continue (cart count already updated)
                return;
            }

            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update cart items section
            const cartItemsContainer = document.querySelector('.lg\\:col-span-2.space-y-4');
            const newCartItemsContainer = doc.querySelector('.lg\\:col-span-2.space-y-4');
            
            if (cartItemsContainer && newCartItemsContainer) {
                // Find the "Continue Shopping" button container (insert before this)
                const continueShoppingContainer = cartItemsContainer.querySelector('.flex.justify-between.items-center.bg-white');
                const insertBeforeElement = continueShoppingContainer || null;
                
                // Get existing item IDs
                const existingItemIds = new Set(
                    Array.from(document.querySelectorAll('[data-remove-item]'))
                        .map(btn => btn.dataset.removeItem)
                );

                // Find new items in the fetched HTML
                const newItems = Array.from(newCartItemsContainer.children);
                newItems.forEach(newItem => {
                    const removeBtn = newItem.querySelector('[data-remove-item]');
                    if (removeBtn && !existingItemIds.has(removeBtn.dataset.removeItem)) {
                        // This is a new item - add it with animation above "Continue Shopping"
                        const clonedItem = newItem.cloneNode(true);
                        clonedItem.style.opacity = '0';
                        clonedItem.style.transform = 'translateY(-20px)';
                        
                        // Insert before "Continue Shopping" button, or append if not found
                        if (insertBeforeElement) {
                            cartItemsContainer.insertBefore(clonedItem, insertBeforeElement);
                        } else {
                            cartItemsContainer.appendChild(clonedItem);
                        }
                        
                        // Animate in
                        requestAnimationFrame(() => {
                            clonedItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            clonedItem.style.opacity = '1';
                            clonedItem.style.transform = 'translateY(0)';
                        });

                        // Reattach event listeners
                        this.reattachCartItemListeners(clonedItem);
                    }
                });
            }

            // Update order summary
            const orderSummaryContainer = document.querySelector('.lg\\:col-span-1');
            const newOrderSummary = doc.querySelector('.lg\\:col-span-1');
            
            if (orderSummaryContainer && newOrderSummary) {
                orderSummaryContainer.innerHTML = newOrderSummary.innerHTML;
            }

        } catch (error) {
            console.error('Error updating cart UI:', error);
            // Silently fail - cart count is already updated
        }
    },

    /**
     * Reattach event listeners for a cart item
     */
    reattachCartItemListeners(cartItem) {
        // Reattach quantity controls
        const decreaseBtn = cartItem.querySelector('button[data-action="decrease"]');
        const increaseBtn = cartItem.querySelector('button[data-action="increase"]');
        const quantityInput = cartItem.querySelector('input[name="quantity"]');
        const removeBtn = cartItem.querySelector('[data-remove-item]');

        // Quantity controls trigger the input's change event (handler attached below)
        if (decreaseBtn) {
            decreaseBtn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.getElementById('quantity-' + itemId);
                if (!input) return;
                
                const currentValue = parseInt(input.value);
                const newValue = Math.max(parseInt(input.min), currentValue - 1);
                input.value = newValue;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        if (increaseBtn) {
            increaseBtn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.getElementById('quantity-' + itemId);
                if (!input) return;
                
                const currentValue = parseInt(input.value);
                const newValue = Math.min(parseInt(input.max), currentValue + 1);
                input.value = newValue;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        if (quantityInput) {
            // Attach change handler for quantity input (same as in cart.html)
            quantityInput.addEventListener('change', function() {
                const itemId = this.id.replace('quantity-', '');
                const form = document.getElementById('cart-form-' + itemId);
                if (!form) return;
                
                const currentValue = parseInt(this.value);
                const min = parseInt(this.min);
                const max = parseInt(this.max);
                
                // Validate
                if (currentValue < min) {
                    this.value = min;
                } else if (currentValue > max) {
                    this.value = max;
                }
                
                // Update via AJAX
                const cartItem = form.closest('.bg-white');
                cartItem.style.opacity = '0.6';
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: new URLSearchParams({
                        'csrfmiddlewaretoken': csrfToken,
                        'quantity': this.value
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const lineTotalEl = document.getElementById('line-total-' + itemId);
                        if (lineTotalEl && data.line_total) {
                            lineTotalEl.textContent = '$' + parseFloat(data.line_total).toFixed(2);
                        }
                        if (typeof updateOrderSummary === 'function') {
                            updateOrderSummary(data);
                        }
                        if (window.CartModule) {
                            window.CartModule.updateCartCount();
                        }
                    }
                })
                .catch(error => console.error('Error:', error))
                .finally(() => {
                    cartItem.style.opacity = '1';
                });
            });
        }

        if (removeBtn) {
            // Attach remove button handler (same as in cart.html)
            const itemId = removeBtn.dataset.removeItem;
            const removeUrl = removeBtn.dataset.removeUrl;
            
            removeBtn.addEventListener('click', function() {
                const cartItem = this.closest('.bg-white');
                cartItem.style.opacity = '0.6';
                cartItem.style.pointerEvents = 'none';
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                fetch(removeUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: new URLSearchParams({
                        'csrfmiddlewaretoken': csrfToken
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        cartItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        cartItem.style.opacity = '0';
                        cartItem.style.transform = 'translateX(-20px)';
                        
                        setTimeout(() => {
                            cartItem.remove();
                            
                            // Update order summary if function exists
                            if (typeof updateOrderSummary === 'function') {
                                updateOrderSummary(data);
                            }
                            
                            // Update cart count
                            if (window.CartModule) {
                                window.CartModule.updateCartCount();
                            }
                            
                            // Reload cart recommendations
                            if (window.CartRecommendationsModule) {
                                window.CartRecommendationsModule.init();
                            }
                            
                            // Check if cart is empty
                            const remainingItems = document.querySelectorAll('[data-remove-item]').length;
                            if (remainingItems === 0) {
                                window.location.reload();
                            }
                        }, 300);
                    } else {
                        alert(data.error || 'Failed to remove item');
                        cartItem.style.opacity = '1';
                        cartItem.style.pointerEvents = '';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Failed to remove item. Please try again.');
                    cartItem.style.opacity = '1';
                    cartItem.style.pointerEvents = '';
                });
            });
            
            // Re-initialize Lucide icons for the new item
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    },

    /**
     * Handle add to cart error
     */
    handleAddToCartError(message, button) {
        // Only show error toast, not success toast
        if (window.toast) {
            window.toast.error(message);
        }
        this.setButtonLoading(button, false);
    },

    /**
     * Set button loading state
     */
    setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.dataset.originalHTML = button.innerHTML;
            button.innerHTML = '<span class="animate-spin">⏳</span>';
            button.disabled = true;
        } else {
            button.innerHTML = button.dataset.originalHTML || '';
            button.disabled = false;
        }
    },

    /**
     * Show view all button
     */
    showViewAllButton() {
        if (this.elements.viewAllContainer) {
            this.elements.viewAllContainer.classList.remove('hidden');
            this.attachViewAllListener();
        }
    },

    /**
     * Attach view all button listener
     */
    attachViewAllListener() {
        if (!this.elements.viewAllBtn || this.elements.viewAllBtn.hasAttribute('data-listener-attached')) {
            return;
        }

        this.elements.viewAllBtn.setAttribute('data-listener-attached', 'true');
        this.elements.viewAllBtn.addEventListener('click', () => {
            this.state.isExpanded = true;
            this.displayRecommendations(this.state.allRecommendations.length);
            
            if (this.elements.viewAllContainer) {
                this.elements.viewAllContainer.classList.add('hidden');
            }
        });
    },

    /**
     * Create product card HTML
     */
    createProductCard(product) {
        const variant = product.lowest_variant || {};
        const image = product.primary_image;
        const price = variant.price || '0.00';
        const comparePrice = variant.compare_price;
        const hasDiscount = comparePrice && parseFloat(comparePrice) > parseFloat(price);
        const discountPercent = hasDiscount 
            ? Math.round(((parseFloat(comparePrice) - parseFloat(price)) / parseFloat(comparePrice)) * 100) 
            : 0;
        const stock = variant.stock || 0;
        const variantId = variant.id || null;
        const rating = product.rating || 0;
        const reviewCount = product.review_count || 0;
        const csrfToken = this.getCSRFToken();

        return `
            <div class="product-card bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition duration-300 relative flex flex-col h-full">
                <div class="relative shrink-0">
                    <a href="/products/${product.sku}/" class="block relative z-0">
                        ${image?.url 
                            ? `<img src="${image.url}" alt="${image.alt_text || product.name}" class="w-full h-64 object-cover">`
                            : `<div class="w-full h-64 bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
                                <i data-lucide="package" class="w-16 h-16 text-gray-400"></i>
                            </div>`
                        }
                    </a>
                    
                    ${hasDiscount ? `
                        <div class="absolute top-0 left-0 w-32 h-32 overflow-hidden pointer-events-none z-10">
                            <div class="absolute top-6 -left-8 w-40 bg-green-500 text-white text-center text-xs font-bold py-1 transform -rotate-45 shadow-lg">
                                SALE
                            </div>
                        </div>
                    ` : ''}
                    
                    ${this.getWishlistButton(product.id, csrfToken)}
                </div>
                
                <div class="p-4 flex flex-col grow">
                    ${product.brand ? `<p class="text-xs text-gray-500 mb-1 uppercase tracking-wide">${product.brand}</p>` : ''}
                    
                    <a href="/products/${product.sku}/" class="block">
                        <h3 class="text-lg font-semibold text-gray-800 hover:text-blue-600 transition line-clamp-2 min-h-[3.5rem]">${product.name}</h3>
                    </a>
                    
                    ${this.getRatingHTML(rating, reviewCount)}
                    
                    <div class="mt-auto pt-3 border-t border-gray-100">
                        <div class="flex items-baseline gap-2 mb-3">
                            <span class="text-2xl font-bold text-blue-600">$${parseFloat(price).toFixed(2)}</span>
                            ${hasDiscount ? `
                                <span class="text-sm text-gray-400 line-through">$${parseFloat(comparePrice).toFixed(2)}</span>
                                <span class="text-xs bg-green-100 text-green-600 px-2 py-1 rounded-full font-semibold">-${discountPercent}%</span>
                            ` : ''}
                        </div>
                        
                        ${this.getAddToCartButton(product.id, variantId, stock, csrfToken)}
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Get wishlist button HTML
     */
    getWishlistButton(productId, csrfToken) {
        // Always show wishlist button - authentication check happens on server
        return `
            <form method="POST" action="/accounts/wishlist/add/${productId}/" class="absolute top-2 right-2 z-20" data-wishlist-toggle>
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <button type="submit" class="bg-white p-2 rounded-full shadow-md hover:bg-red-50 transition" data-product-id="${productId}">
                    <i data-lucide="heart" class="w-5 h-5 text-gray-600 hover:text-red-500"></i>
                </button>
            </form>
        `;
    },

    /**
     * Get rating HTML
     */
    getRatingHTML(rating, reviewCount) {
        if (rating <= 0) return '<div class="mt-1 mb-2 h-6"></div>';

        return `
            <div class="mt-1 mb-2 h-6">
                <div class="flex items-center gap-1">
                    <div class="flex text-yellow-400 product-rating-stars" data-rating="${rating}"></div>
                    <span class="text-sm font-medium text-gray-700">${rating.toFixed(1)}</span>
                    ${reviewCount > 0 ? `<span class="text-xs text-gray-500">(${reviewCount})</span>` : ''}
                </div>
            </div>
        `;
    },

    /**
     * Get add to cart button HTML
     */
    getAddToCartButton(productId, variantId, stock, csrfToken) {
        // Always show button - check variantId as number or string
        const hasVariant = variantId !== null && variantId !== undefined && variantId !== '';
        
        if (hasVariant) {
            const isOutOfStock = stock <= 0;
            return `
                <form method="POST" action="/cart/add/${productId}/" class="ajax-add-to-cart">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken || ''}">
                    <input type="hidden" name="quantity" value="1">
                    <input type="hidden" name="variant_id" value="${variantId}">
                    <button type="submit" 
                            class="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold flex items-center justify-center gap-2 transition ${isOutOfStock ? 'opacity-50 cursor-not-allowed' : ''}"
                            data-add-to-cart 
                            data-product-id="${productId}"
                            ${isOutOfStock ? 'disabled' : ''}>
                        <i data-lucide="shopping-cart" class="w-5 h-5"></i>
                        ${isOutOfStock ? 'Out of Stock' : 'Add to Cart'}
                    </button>
                </form>
            `;
        }

        return `
            <button disabled class="w-full bg-gray-300 text-gray-500 px-4 py-2 rounded-lg font-semibold cursor-not-allowed text-sm">
                No Variant Available
            </button>
        `;
    },

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }
};

// Export
window.CartRecommendationsModule = CartRecommendationsModule;

