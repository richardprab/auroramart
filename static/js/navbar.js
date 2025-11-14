const NavbarModule = {
    init() {
        this.mobileMenu();
        this.dropdowns();
        this.searchBar();
        this.stickyNav();
    },

    // Mobile menu toggle
    mobileMenu() {
        const menuButton = document.getElementById('mobile-menu-button');
        const mobileMenu = document.getElementById('mobile-menu');

        if (!menuButton || !mobileMenu) return;

        menuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');

            // Animate hamburger icon
            const icon = menuButton.querySelector('svg');
            if (icon) {
                icon.style.transform = mobileMenu.classList.contains('hidden')
                    ? 'rotate(0deg)'
                    : 'rotate(90deg)';
            }
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!menuButton.contains(e.target) && !mobileMenu.contains(e.target)) {
                mobileMenu.classList.add('hidden');
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                mobileMenu.classList.add('hidden');
            }
        });
    },

    // Dropdown menus
    dropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown');

        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle, button');
            const menu = dropdown.querySelector('.dropdown-menu');

            if (!toggle || !menu) return;

            // Toggle on click
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();

                // Close other dropdowns
                document.querySelectorAll('.dropdown-menu').forEach(m => {
                    if (m !== menu) m.classList.remove('show');
                });

                menu.classList.toggle('show');
            });

            // Close on outside click
            document.addEventListener('click', (e) => {
                if (!dropdown.contains(e.target)) {
                    menu.classList.remove('show');
                }
            });
        });
    },

    // Search bar functionality
    searchBar() {
        const searchInputs = document.querySelectorAll('input[name="q"]');
        if (searchInputs.length === 0) return;

        // Initialize for each search input (desktop and mobile)
        searchInputs.forEach(searchInput => {
        let debounceTimer;

            // Create suggestions container if it doesn't exist
            // The input is inside a div.relative, so we append to that
            const inputWrapper = searchInput.parentElement; // The div.relative
            if (inputWrapper && !inputWrapper.querySelector('.search-suggestions')) {
                const suggestionsContainer = document.createElement('div');
                suggestionsContainer.className = 'search-suggestions absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto hidden';
                // Ensure parent has relative positioning
                if (window.getComputedStyle(inputWrapper).position === 'static') {
                    inputWrapper.style.position = 'relative';
                }
                inputWrapper.appendChild(suggestionsContainer);
            }

        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);

            debounceTimer = setTimeout(() => {
                    const query = searchInput.value.trim();

                if (query.length > 2) {
                        NavbarModule.searchSuggestions(query, searchInput);
                } else {
                    NavbarModule.hideSuggestions();
                }
            }, 300);
        });

            // Hide suggestions when clicking outside
            document.addEventListener('click', (e) => {
                if (!inputWrapper.contains(e.target)) {
                    NavbarModule.hideSuggestions();
                }
            });

            // Handle keyboard navigation
            searchInput.addEventListener('keydown', function(e) {
                const suggestions = inputWrapper.querySelector('.search-suggestions');
                const items = suggestions?.querySelectorAll('.suggestion-item');
                
                if (e.key === 'ArrowDown' && items && items.length > 0) {
                    e.preventDefault();
                    const current = suggestions.querySelector('.suggestion-item.highlighted');
                    if (current) {
                        current.classList.remove('highlighted');
                        const next = current.nextElementSibling;
                        if (next) {
                            next.classList.add('highlighted');
                        } else {
                            items[0].classList.add('highlighted');
                        }
                    } else {
                        items[0].classList.add('highlighted');
                    }
                } else if (e.key === 'ArrowUp' && items && items.length > 0) {
                    e.preventDefault();
                    const current = suggestions.querySelector('.suggestion-item.highlighted');
                    if (current) {
                        current.classList.remove('highlighted');
                        const prev = current.previousElementSibling;
                        if (prev) {
                            prev.classList.add('highlighted');
                        } else {
                            items[items.length - 1].classList.add('highlighted');
                        }
                    } else {
                        items[items.length - 1].classList.add('highlighted');
                    }
                } else if (e.key === 'Enter') {
                    const highlighted = suggestions?.querySelector('.suggestion-item.highlighted a');
                    if (highlighted) {
                e.preventDefault();
                        window.location.href = highlighted.href;
                    } else {
                        // Normal form submission
                searchInput.closest('form').submit();
                    }
                } else if (e.key === 'Escape') {
                    NavbarModule.hideSuggestions();
                }
            });
        });
    },

    // Show search suggestions
    searchSuggestions(query, searchInput = null) {
        // If no specific input provided, find the active one (the one with the query)
        if (!searchInput) {
            const inputs = document.querySelectorAll('input[name="q"]');
            searchInput = Array.from(inputs).find(input => input.value.trim() === query) || inputs[0];
        }
        
        if (!searchInput) {
            console.error('Search input not found');
            return;
        }
        
        const inputWrapper = searchInput.parentElement;
        if (!inputWrapper) {
            console.error('Input wrapper not found');
            return;
        }
        
        // Ensure suggestions container exists
        let suggestionsContainer = inputWrapper.querySelector('.search-suggestions');
        if (!suggestionsContainer) {
            suggestionsContainer = document.createElement('div');
            suggestionsContainer.className = 'search-suggestions absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto hidden';
            if (window.getComputedStyle(inputWrapper).position === 'static') {
                inputWrapper.style.position = 'relative';
            }
            inputWrapper.appendChild(suggestionsContainer);
        }

        // Show loading state
        suggestionsContainer.innerHTML = '<div class="p-4 text-center text-gray-500">Searching...</div>';
        suggestionsContainer.classList.remove('hidden');
        suggestionsContainer.style.display = 'block';

        // Fetch suggestions
        fetch(`/products/search-suggestions/?q=${encodeURIComponent(query)}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.suggestions && data.suggestions.length > 0) {
                let html = '';
                const self = this;
                data.suggestions.forEach(product => {
                    html += `
                        <a href="/products/${product.sku}/" class="suggestion-item flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
                            ${product.image ? `
                                <img src="${product.image}" alt="${self.escapeHtml(product.name)}" class="w-12 h-12 object-cover rounded">
                            ` : `
                                <div class="w-12 h-12 bg-gray-200 rounded flex items-center justify-center">
                                    <i data-lucide="package" class="w-6 h-6 text-gray-400"></i>
                                </div>
                            `}
                            <div class="flex-1 min-w-0">
                                <div class="font-medium text-gray-900 truncate">${self.escapeHtml(product.name)}</div>
                                ${product.brand ? `<div class="text-sm text-gray-500">${self.escapeHtml(product.brand)}</div>` : ''}
                                ${product.category ? `<div class="text-xs text-gray-400">${self.escapeHtml(product.category)}</div>` : ''}
                            </div>
                            <div class="text-right">
                                <div class="font-semibold text-gray-900">$${product.price.toFixed(2)}</div>
                            </div>
                        </a>
                    `;
                });
                suggestionsContainer.innerHTML = html;
                suggestionsContainer.style.display = 'block';
                
                // Reinitialize Lucide icons
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }
            } else {
                suggestionsContainer.innerHTML = '<div class="p-4 text-center text-gray-500">No products found</div>';
                suggestionsContainer.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error fetching suggestions:', error);
            suggestionsContainer.classList.add('hidden');
            suggestionsContainer.style.display = 'none';
        });
    },

    // Hide search suggestions
    hideSuggestions() {
        const searchInputs = document.querySelectorAll('input[name="q"]');
        searchInputs.forEach(searchInput => {
            const inputWrapper = searchInput.parentElement;
            const suggestionsContainer = inputWrapper?.querySelector('.search-suggestions');
            
            if (suggestionsContainer) {
                suggestionsContainer.classList.add('hidden');
                suggestionsContainer.style.display = 'none';
                // Remove highlighted class
                suggestionsContainer.querySelectorAll('.suggestion-item.highlighted').forEach(item => {
                    item.classList.remove('highlighted');
                });
            }
        });
    },

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    stickyNav() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        let lastScroll = 0;

        window.addEventListener('scroll', AuroraMart.throttle(() => {
            const currentScroll = window.pageYOffset;

            // Add shadow when scrolled
            if (currentScroll > 50) {
                navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
            } else {
                navbar.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
            }

            // Hide/show on scroll (optional)
            // if (currentScroll > lastScroll && currentScroll > 100) {
            //     navbar.style.transform = 'translateY(-100%)';
            // } else {
            //     navbar.style.transform = 'translateY(0)';
            // }

            lastScroll = currentScroll;
        }, 100));
    }
};

// Export
window.NavbarModule = NavbarModule;

/**
 * Navbar functionality
 * Handles mobile menu toggle and profile dropdown with hover delay
 */

document.addEventListener('DOMContentLoaded', function () {
    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Profile dropdown with hover delay
    const profileButton = document.getElementById('user-menu-button');
    const profileDropdown = document.getElementById('user-menu');
    const profileWrapper = profileButton?.parentElement; // Get the wrapper element
    let hideTimeout;
    const DROPDOWN_DELAY = 300; // Reduced delay for better UX

    if (profileButton && profileDropdown) {

        // Function to show dropdown
        function showDropdown() {
            clearTimeout(hideTimeout);
            profileDropdown.classList.remove('hidden');
        }

        // Function to hide dropdown
        function hideDropdown() {
            profileDropdown.classList.add('hidden');
        }

        // Function to hide dropdown with delay
        function hideDropdownDelayed() {
            clearTimeout(hideTimeout);
            hideTimeout = setTimeout(function () {
                hideDropdown();
            }, DROPDOWN_DELAY);
        }

        // Show dropdown on hover over button
        profileButton.addEventListener('mouseenter', function () {
            showDropdown();
        });

        // Hide dropdown with delay when leaving button
        profileButton.addEventListener('mouseleave', function (e) {
            // Check if moving to dropdown
            const rect = profileDropdown.getBoundingClientRect();
            const isMovingToDropdown = e.clientY >= rect.top && e.clientY <= rect.bottom;
            
            if (!isMovingToDropdown) {
                hideDropdownDelayed();
            }
        });

        // Keep dropdown visible when hovering over it
        profileDropdown.addEventListener('mouseenter', function () {
            showDropdown();
        });

        // Hide dropdown with delay when leaving dropdown
        profileDropdown.addEventListener('mouseleave', function () {
            hideDropdownDelayed();
        });

        // Toggle dropdown on click
        profileButton.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (profileDropdown.classList.contains('hidden')) {
                showDropdown();
            } else {
                clearTimeout(hideTimeout);
                hideDropdown();
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (profileWrapper && !profileWrapper.contains(e.target)) {
                clearTimeout(hideTimeout);
                hideDropdown();
            }
        });

        // Close dropdown when pressing Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !profileDropdown.classList.contains('hidden')) {
                clearTimeout(hideTimeout);
                hideDropdown();
            }
        });

    } else {
        console.warn('❌ Profile dropdown elements not found!');
        if (!profileButton) console.warn('Missing: #user-menu-button');
        if (!profileDropdown) console.warn('Missing: #user-menu');
    }

    // Search functionality
    const searchForms = document.querySelectorAll('form[action*="products"]');

    searchForms.forEach(form => {
        const searchInput = form.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter' && !this.value.trim()) {
                    e.preventDefault();
                }
            });
        }
    });

    // Active link highlighting
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a[href]');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('text-blue-600', 'font-semibold');
        }
    });

    // Sticky navbar on scroll
    const navbar = document.querySelector('nav');

    if (navbar) {
        let lastScrollTop = 0;

        window.addEventListener('scroll', function () {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

            // Add shadow when scrolled
            if (scrollTop > 50) {
                navbar.classList.add('shadow-xl');
            } else {
                navbar.classList.remove('shadow-xl');
            }

            lastScrollTop = scrollTop;
        });
    }

    // Update cart count on page load
    updateCartCount();
});

/**
 * Update cart count badge
 */
function updateCartCount() {
    // Check if cart count is stored in session/local storage
    const cartCount = sessionStorage.getItem('cart_count') || 0;
    const cartBadge = document.getElementById('cart-count');

    if (cartBadge) {
        cartBadge.textContent = cartCount;
        if (cartCount > 0) {
            cartBadge.classList.remove('hidden');
        } else {
            cartBadge.classList.add('hidden');
        }
    }
}

/**
 * Show notification in navbar
 */
function showNavNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `fixed top-20 right-4 z-50 px-6 py-3 rounded-lg shadow-lg transition-all duration-300 ${type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
            'bg-blue-500'
        } text-white font-medium`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateY(0)';
    }, 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Export functions for use in other scripts
window.navbarUtils = {
    updateCartCount,
    showNavNotification
};