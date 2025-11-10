/**
 * Star Rating Module
 * Renders star ratings with half-star support
 * Used across product cards, product detail pages, and home page
 */

const StarRating = {
    /**
     * Render star ratings for all elements with class 'product-rating-stars'
     * @param {HTMLElement|Document} container - Container to search within (defaults to document)
     */
    render(container = document) {
        const ratingContainers = container.querySelectorAll ? 
            container.querySelectorAll('.product-rating-stars') : 
            document.querySelectorAll('.product-rating-stars');
        
        ratingContainers.forEach((ratingContainer) => {
            // Skip if already rendered
            if (ratingContainer.dataset.rendered === 'true') {
                return;
            }
            
            const rating = parseFloat(ratingContainer.dataset.rating) || 0;
            const fullStars = Math.floor(rating);
            const hasHalfStar = (rating - fullStars) >= 0.5;
            
            let starsHtml = '';
            
            for (let i = 1; i <= 5; i++) {
                if (i <= fullStars) {
                    // Full star
                    starsHtml += '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>';
                } else if (i === fullStars + 1 && hasHalfStar) {
                    // Half star
                    starsHtml += '<div class="relative w-5 h-5"><svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 absolute text-yellow-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg><svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 absolute text-yellow-400" viewBox="0 0 24 24" fill="currentColor" style="clip-path: inset(0 50% 0 0);"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg></div>';
                } else {
                    // Empty star
                    starsHtml += '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>';
                }
            }
            
            ratingContainer.innerHTML = starsHtml;
            ratingContainer.dataset.rendered = 'true';
        });
    },

    /**
     * Initialize star ratings on page load
     */
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.render());
        } else {
            this.render();
        }
    }
};

// Export to window object for global access
window.StarRating = StarRating;

// Auto-initialize on page load
StarRating.init();

