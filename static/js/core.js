const AuroraMart = {
    // Configuration
    config: {
        apiUrl: '/api',
        cartUpdateDelay: 300,
        toastDuration: 3000
    },

    // Initialize all modules
    init() {

        // Initialize modules when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initModules();
            });
        } else {
            this.initModules();
        }
    },

    // Initialize all modules
    initModules() {
        // Check if modules exist before initializing
        if (window.NavbarModule) NavbarModule.init();
        if (window.CartModule) CartModule.init();
        if (window.WishlistModule) WishlistModule.init();
        if (window.ProductsModule) ProductsModule.init();
        if (window.FormsModule) FormsModule.init();
        if (window.AnimationsModule) AnimationsModule.init();
    },

    // Show toast notification
    toast(message, type = 'success', duration = null) {
        duration = duration || this.config.toastDuration;

        const toast = document.createElement('div');
        toast.className = `toast alert alert-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            animation: slideIn 0.3s ease-out;
        `;

        toast.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; font-size: 1.5rem; cursor: pointer; margin-left: 1rem;">
                    ×
                </button>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    // Show loading spinner
    showLoading(element) {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.style.cssText = 'margin: 2rem auto;';
        element.innerHTML = '';
        element.appendChild(spinner);
    },

    // Format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function () {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize
AuroraMart.init();

// Export to window
window.AuroraMart = AuroraMart;