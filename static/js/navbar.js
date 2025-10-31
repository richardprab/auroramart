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