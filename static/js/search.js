/**
 * Live Search Functionality
 * Real-time AJAX product search with debouncing
 */

// Global function to perform live filtering (can be called from anywhere)
window.performLiveFilter = function(urlParams) {
    const searchUrl = `/products/?${urlParams.toString()}`;
    
    // Update browser URL without reload
    history.pushState(null, '', searchUrl);
    
    // Show loading state
    showLoadingState();
    
    // Fetch filtered results
    fetch(searchUrl, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        updateProductDisplay(html);
    })
    .catch(error => {
        console.error('Filter error:', error);
        hideLoadingState();
    });
};

document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('input[name="q"]');
    let searchTimeout = null;
    const DEBOUNCE_DELAY = 300; // milliseconds

    searchInputs.forEach(input => {
        // Handle input changes
        input.addEventListener('input', function(e) {
            const searchQuery = e.target.value.trim();
            
            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }

            // If on product list page, do live search
            if (window.location.pathname.includes('/products/')) {
                // Debounce the search
                searchTimeout = setTimeout(() => {
                    performLiveSearch(searchQuery);
                }, DEBOUNCE_DELAY);
            }
        });

        // Handle Enter key - navigate to products page with search
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const searchQuery = e.target.value.trim();
                
                if (searchQuery) {
                    // If not on products page, navigate there
                    if (!window.location.pathname.includes('/products/')) {
                        window.location.href = `/products/?q=${encodeURIComponent(searchQuery)}`;
                    } else {
                        // If already on products page, trigger search
                        performLiveSearch(searchQuery);
                    }
                }
            }
        });

        // Prevent form submission, handle with AJAX instead
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const searchQuery = input.value.trim();
                
                if (searchQuery) {
                    if (!window.location.pathname.includes('/products/')) {
                        window.location.href = `/products/?q=${encodeURIComponent(searchQuery)}`;
                    } else {
                        performLiveSearch(searchQuery);
                    }
                }
            });
        }
    });

    /**
     * Perform live search using AJAX
     */
    function performLiveSearch(query) {
        // Get current filters from URL
        const urlParams = new URLSearchParams(window.location.search);
        
        // Update query parameter
        if (query) {
            urlParams.set('q', query);
        } else {
            urlParams.delete('q');
        }
        
        // Reset to page 1 when searching
        urlParams.delete('page');
        
        // Use the global filter function
        window.performLiveFilter(urlParams);
        
        // Update search query in all search inputs
        searchInputs.forEach(input => {
            if (input.value !== query) {
                input.value = query;
            }
        });
    }
    
    /**
     * Update product display with new HTML
     */
    function updateProductDisplay(html) {
        // Parse the HTML response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the products grid
        const newProductsGrid = doc.querySelector('.products-grid-container');
        const currentProductsGrid = document.querySelector('.products-grid-container');
        
        if (newProductsGrid && currentProductsGrid) {
            currentProductsGrid.innerHTML = newProductsGrid.innerHTML;
            
            // Reinitialize Lucide icons for new content
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
        
        // Update active filters display
        const newActiveFilters = doc.querySelector('.active-filters-container');
        const currentActiveFilters = document.querySelector('.active-filters-container');
        
        if (newActiveFilters && currentActiveFilters) {
            currentActiveFilters.innerHTML = newActiveFilters.innerHTML;
            
            // Reinitialize Lucide icons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
        
        // Scroll to top of page smoothly
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        hideLoadingState();
    }
    
    // Make updateProductDisplay available globally
    window.updateProductDisplay = updateProductDisplay;

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function() {
        location.reload();
    });
});

/**
 * Show loading state
 */
function showLoadingState() {
    const productsGrid = document.querySelector('.products-grid-container');
    if (productsGrid) {
        productsGrid.style.opacity = '0.5';
        productsGrid.style.pointerEvents = 'none';
        productsGrid.style.transition = 'opacity 0.2s ease';
    }
}

/**
 * Hide loading state
 */
function hideLoadingState() {
    const productsGrid = document.querySelector('.products-grid-container');
    if (productsGrid) {
        productsGrid.style.opacity = '1';
        productsGrid.style.pointerEvents = 'auto';
    }
}
