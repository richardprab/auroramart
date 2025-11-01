/* ========================================
   NAVBAR - Navigation functionality
   ======================================== */

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
        const searchInput = document.querySelector('input[name="q"]');
        if (!searchInput) return;

        let debounceTimer;

        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);

            debounceTimer = setTimeout(() => {
                const query = this.value.trim();

                if (query.length > 2) {
                    NavbarModule.searchSuggestions(query);
                } else {
                    NavbarModule.hideSuggestions();
                }
            }, 300);
        });

        // Submit on Enter
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchInput.closest('form').submit();
            }
        });
    },

    // Search suggestions (placeholder for API integration)
    searchSuggestions(query) {
        console.log('Searching for:', query);
        // TODO: Implement API call for suggestions
        // Example:
        // fetch(`/api/search?q=${query}`)
        //     .then(res => res.json())
        //     .then(data => this.displaySuggestions(data));
    },

    displaySuggestions(suggestions) {
        // TODO: Display search suggestions dropdown
        console.log('Suggestions:', suggestions);
    },

    hideSuggestions() {
        const suggestionsBox = document.getElementById('search-suggestions');
        if (suggestionsBox) {
            suggestionsBox.remove();
        }
    },

    // Sticky navbar on scroll
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
    console.log('🚀 Navbar script loaded');

    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Profile dropdown with hover delay
    const profileWrapper = document.getElementById('profile-dropdown-wrapper');
    const profileButton = document.getElementById('user-menu-button');
    const profileDropdown = document.getElementById('user-menu');
    let hideTimeout;
    const DROPDOWN_DELAY = 1000;

    if (profileButton && profileDropdown) {
        console.log('✅ Profile dropdown elements found');
        console.log('📋 Dropdown delay:', DROPDOWN_DELAY + 'ms');

        // Function to show dropdown
        function showDropdown() {
            clearTimeout(hideTimeout);
            profileDropdown.classList.remove('hidden');
            console.log('👁️ Dropdown shown');
        }

        // Function to hide dropdown
        function hideDropdown() {
            profileDropdown.classList.add('hidden');
            console.log('🙈 Dropdown hidden');
        }

        // Function to hide dropdown with delay
        function hideDropdownDelayed() {
            console.log('⏰ Starting hide delay (' + (DROPDOWN_DELAY / 1000) + 's)');
            clearTimeout(hideTimeout);
            hideTimeout = setTimeout(function () {
                hideDropdown();
            }, DROPDOWN_DELAY);
        }

        // Show dropdown on hover over button
        profileButton.addEventListener('mouseenter', function () {
            console.log('🖱️ Mouse entered profile button');
            showDropdown();
        });

        // Hide dropdown with delay when leaving button
        profileButton.addEventListener('mouseleave', function () {
            console.log('🖱️ Mouse left profile button');
            hideDropdownDelayed();
        });

        // Keep dropdown visible when hovering over it
        profileDropdown.addEventListener('mouseenter', function () {
            console.log('🖱️ Mouse entered dropdown');
            showDropdown();
        });

        // Hide dropdown with delay when leaving dropdown
        profileDropdown.addEventListener('mouseleave', function () {
            console.log('🖱️ Mouse left dropdown');
            hideDropdownDelayed();
        });

        // Toggle dropdown on click
        profileButton.addEventListener('click', function (e) {
            console.log('👆 Profile button clicked');
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
                console.log('👆 Clicked outside - closing dropdown');
                clearTimeout(hideTimeout);
                hideDropdown();
            }
        });

        // Close dropdown when pressing Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !profileDropdown.classList.contains('hidden')) {
                console.log('⌨️ Escape pressed - closing dropdown');
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