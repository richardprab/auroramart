
// Global function to perform live filtering (can be called from anywhere)
window.performLiveFilter = function(urlParams) {
    // Only run if we're on the products page
    if (!window.location.pathname.includes('/products/')) {
        return;
    }
    
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text();
    })
    .then(html => {
        updateProductDisplay(html);
    })
    .catch(error => {
        // Only log if it's not a connection refused error (server might not be running)
        if (error.message && !error.message.includes('Failed to fetch') && !error.message.includes('ERR_CONNECTION_REFUSED')) {
        console.error('Filter error:', error);
        }
        hideLoadingState();
    });
};

document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('input[name="q"]');
    let searchTimeout = null;
    const DEBOUNCE_DELAY = 300; // milliseconds

    searchInputs.forEach(input => {
        // Handle input changes
        // Only attach if we're on the products page to avoid conflicts with navbar suggestions
        if (window.location.pathname.includes('/products/')) {
        input.addEventListener('input', function(e) {
            const searchQuery = e.target.value.trim();
            
            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }

            // If on product list page, do live search
                // Debounce the search
                searchTimeout = setTimeout(() => {
                    performLiveSearch(searchQuery);
                }, DEBOUNCE_DELAY);
            });
            }

        // Handle Enter key - navigate to products page with search
        // Only prevent default and handle on products page, otherwise let navbar handle it
        if (window.location.pathname.includes('/products/')) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const searchQuery = e.target.value.trim();
                
                if (searchQuery) {
                        // If already on products page, trigger search
                        performLiveSearch(searchQuery);
                }
            }
        });

            // Prevent form submission, handle with AJAX instead (only on products page)
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const searchQuery = input.value.trim();
                
                if (searchQuery) {
                        performLiveSearch(searchQuery);
                    }
                });
                }
        }
    });

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
    
    function updateProductDisplay(html) {
        // Parse the HTML response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update product count
        const newProductCount = doc.querySelector('#product-count-text');
        const currentProductCount = document.querySelector('#product-count-text');
        
        if (newProductCount && currentProductCount) {
            currentProductCount.textContent = newProductCount.textContent;
        }
        
        // Extract the products grid
        const newProductsGrid = doc.querySelector('.products-grid-container');
        const currentProductsGrid = document.querySelector('.products-grid-container');
        
        if (newProductsGrid && currentProductsGrid) {
            currentProductsGrid.innerHTML = newProductsGrid.innerHTML;
            
            // Reinitialize Lucide icons for new content
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
            
            // Re-render star ratings for new products
            if (typeof StarRating !== 'undefined') {
                StarRating.render(currentProductsGrid);
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

function showLoadingState() {
    const productsGrid = document.querySelector('.products-grid-container');
    if (productsGrid) {
        productsGrid.style.opacity = '0.5';
        productsGrid.style.pointerEvents = 'none';
        productsGrid.style.transition = 'opacity 0.2s ease';
    }
}

function hideLoadingState() {
    const productsGrid = document.querySelector('.products-grid-container');
    if (productsGrid) {
        productsGrid.style.opacity = '1';
        productsGrid.style.pointerEvents = 'auto';
    }
}
