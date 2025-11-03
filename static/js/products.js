const ProductsModule = {
    init() {
        this.filterProducts();
        this.sortProducts();
        this.productGallery();
        this.quantityControls();
        this.priceRange();
        this.quickView();
    },

    // Filter products
    filterProducts() {
        const filterButtons = document.querySelectorAll('[data-filter]');
        const products = document.querySelectorAll('[data-product]');

        if (filterButtons.length === 0) return;

        filterButtons.forEach(button => {
            button.addEventListener('click', function () {
                const filter = this.dataset.filter;

                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Filter products
                products.forEach(product => {
                    const category = product.dataset.category;

                    if (filter === 'all' || category === filter) {
                        product.style.display = 'block';
                        product.style.animation = 'fadeIn 0.5s ease-out';
                    } else {
                        product.style.display = 'none';
                    }
                });

                // Update URL without reload
                const url = new URL(window.location);
                if (filter === 'all') {
                    url.searchParams.delete('category');
                } else {
                    url.searchParams.set('category', filter);
                }
                window.history.pushState({}, '', url);
            });
        });
    },

    // Sort products
    sortProducts() {
        const sortSelect = document.querySelector('[data-sort]');
        if (!sortSelect) return;

        sortSelect.addEventListener('change', function () {
            const sortBy = this.value;
            const container = document.querySelector('[data-products-container]');
            if (!container) return;

            const products = Array.from(container.querySelectorAll('[data-product]'));

            products.sort((a, b) => {
                switch (sortBy) {
                    case 'price-low':
                        return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
                    case 'price-high':
                        return parseFloat(b.dataset.price) - parseFloat(a.dataset.price);
                    case 'name':
                        return a.dataset.name.localeCompare(b.dataset.name);
                    case 'rating':
                        return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
                    default:
                        return 0;
                }
            });

            // Re-append in sorted order
            products.forEach(product => {
                container.appendChild(product);
                product.style.animation = 'fadeIn 0.3s ease-out';
            });

            // Update URL
            const url = new URL(window.location);
            url.searchParams.set('sort', sortBy);
            window.history.pushState({}, '', url);
        });
    },

    // Product gallery
    productGallery() {
        const thumbnails = document.querySelectorAll('.thumbnail');
        const mainImage = document.querySelector('.gallery-main img');

        if (!mainImage || thumbnails.length === 0) return;

        thumbnails.forEach(thumb => {
            thumb.addEventListener('click', function () {
                // Update active state
                thumbnails.forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // Update main image with fade effect
                mainImage.style.opacity = '0';

                setTimeout(() => {
                    mainImage.src = this.querySelector('img').dataset.fullsize ||
                        this.querySelector('img').src;
                    mainImage.style.opacity = '1';
                }, 200);
            });
        });

        // Image zoom on hover
        mainImage.addEventListener('mousemove', function (e) {
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;

            this.style.transformOrigin = `${x}% ${y}%`;
            this.style.transform = 'scale(2)';
        });

        mainImage.addEventListener('mouseleave', function () {
            this.style.transform = 'scale(1)';
            this.style.transformOrigin = 'center';
        });
    },

    // Quantity controls
    quantityControls() {
        const controls = document.querySelectorAll('.quantity-control');

        controls.forEach(control => {
            const input = control.querySelector('input[type="number"]');
            const decreaseBtn = control.querySelector('.quantity-btn.decrease');
            const increaseBtn = control.querySelector('.quantity-btn.increase');

            if (!input) return;

            const min = parseInt(input.min) || 1;
            const max = parseInt(input.max) || 999;

            if (decreaseBtn) {
                decreaseBtn.addEventListener('click', () => {
                    const currentValue = parseInt(input.value) || min;
                    if (currentValue > min) {
                        input.value = currentValue - 1;
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            }

            if (increaseBtn) {
                increaseBtn.addEventListener('click', () => {
                    const currentValue = parseInt(input.value) || min;
                    if (currentValue < max) {
                        input.value = currentValue + 1;
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            }

            // Validate on input
            input.addEventListener('change', function () {
                let value = parseInt(this.value);
                if (isNaN(value) || value < min) value = min;
                if (value > max) value = max;
                this.value = value;
            });
        });
    },

    // Price range filter
    priceRange() {
        const minInput = document.querySelector('[data-price-min]');
        const maxInput = document.querySelector('[data-price-max]');
        const applyButton = document.querySelector('[data-apply-price]');

        if (!minInput || !maxInput || !applyButton) return;

        applyButton.addEventListener('click', () => {
            const min = parseFloat(minInput.value) || 0;
            const max = parseFloat(maxInput.value) || Infinity;

            const products = document.querySelectorAll('[data-product]');

            products.forEach(product => {
                const price = parseFloat(product.dataset.price);

                if (price >= min && price <= max) {
                    product.style.display = 'block';
                } else {
                    product.style.display = 'none';
                }
            });

            // Update URL
            const url = new URL(window.location);
            url.searchParams.set('min_price', min);
            url.searchParams.set('max_price', max);
            window.history.pushState({}, '', url);
        });
    },

    // Quick view modal
    quickView() {
        const quickViewButtons = document.querySelectorAll('[data-quick-view]');

        quickViewButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const productId = button.dataset.productId;
                this.showQuickView(productId);
            });
        });
    },

    showQuickView(productId) {
        // Fetch product data
        fetch(`/api/products/${productId}/`)
            .then(response => response.json())
            .then(data => {
                // Create modal
                const modal = document.createElement('div');
                modal.className = 'modal-overlay';
                modal.innerHTML = `
                    <div class="modal-content" style="max-width: 800px;">
                        <div class="modal-header">
                            <h3>${data.name}</h3>
                            <button onclick="this.closest('.modal-overlay').remove()">×</button>
                        </div>
                        <div class="modal-body">
                            <div class="grid grid-cols-2 gap-6">
                                <img src="${data.image}" alt="${data.name}" class="w-full rounded-lg">
                                <div>
                                    <p class="text-2xl font-bold mb-4">$${data.price}</p>
                                    <p class="text-gray-600 mb-4">${data.description}</p>
                                    <button class="btn btn-primary w-full" data-add-to-cart data-product-id="${productId}">
                                        Add to Cart
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                document.body.appendChild(modal);

                // Re-initialize cart buttons
                CartModule.addToCartButtons();
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
};

// Export
window.ProductsModule = ProductsModule;