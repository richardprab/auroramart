/* ========================================
   UTILS - Helper functions
   ======================================== */

const Utils = {
    // Format date
    formatDate(date, format = 'short') {
        const d = new Date(date);

        if (format === 'short') {
            return d.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } else if (format === 'long') {
            return d.toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        } else {
            return d.toLocaleDateString();
        }
    },

    // Truncate text
    truncate(text, length = 100, suffix = '...') {
        if (text.length <= length) return text;
        return text.substring(0, length).trim() + suffix;
    },

    // Get cookie
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },

    // Set cookie
    setCookie(name, value, days = 7) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
    },

    // Generate random ID
    generateId(prefix = 'id') {
        return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
    },

    // Check if mobile
    isMobile() {
        return window.innerWidth < 768;
    },

    // Copy to clipboard
    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                AuroraMart.toast('Copied to clipboard!', 'success');
            });
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            AuroraMart.toast('Copied to clipboard!', 'success');
        }
    },

    // Smooth scroll to element
    scrollTo(selector, offset = 0) {
        const element = document.querySelector(selector);
        if (!element) return;

        const top = element.getBoundingClientRect().top + window.pageYOffset - offset;

        window.scrollTo({
            top: top,
            behavior: 'smooth'
        });
    },

    // Check if element is in viewport
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },

    // Local storage wrapper
    storage: {
        get(key) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch {
                return null;
            }
        },

        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch {
                return false;
            }
        },

        remove(key) {
            localStorage.removeItem(key);
        },

        clear() {
            localStorage.clear();
        }
    }
};

// Toast Notification System

// Create toast container if it doesn't exist
function getToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Type of toast: 'success', 'error', 'info', 'warning'
 * @param {number} duration - Duration in milliseconds (default: 5000)
 * @param {string} title - Optional title for the toast
 */
function showToast(message, type = 'success', duration = 5000, title = null) {
    const container = getToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✓',
        error: '✕',
        info: 'ℹ',
        warning: '⚠'
    };

    const titles = {
        success: 'Success',
        error: 'Error',
        info: 'Info',
        warning: 'Warning'
    };

    const icon = icons[type] || icons.success;
    const toastTitle = title || titles[type];

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            <div class="toast-title">${toastTitle}</div>
            <div class="toast-message">${message}</div>
        </div>
        <div class="toast-close">✕</div>
        <div class="toast-progress"></div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        removeToast(toast);
    });

    if (duration > 0) {
        setTimeout(() => {
            removeToast(toast);
        }, duration);
    }

    return toast;
}

function removeToast(toast) {
    toast.classList.remove('show');
    toast.classList.add('hide');

    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

window.toast = {
    success: (message, duration, title) => showToast(message, 'success', duration, title),
    error: (message, duration, title) => showToast(message, 'error', duration, title),
    info: (message, duration, title) => showToast(message, 'info', duration, title),
    warning: (message, duration, title) => showToast(message, 'warning', duration, title)
};

/**
 * Show Django messages as toasts on page load
 */
document.addEventListener('DOMContentLoaded', function () {
    // Check for Django messages in the page
    const messageElements = document.querySelectorAll('.alert:not(.toast)');

    messageElements.forEach(element => {
        const message = element.textContent.trim();
        let type = 'info';

        // Determine type from class
        if (element.classList.contains('alert-success') || element.classList.contains('success')) {
            type = 'success';
        } else if (element.classList.contains('alert-error') || element.classList.contains('error')) {
            type = 'error';
        } else if (element.classList.contains('alert-warning') || element.classList.contains('warning')) {
            type = 'warning';
        }

        // Show toast
        showToast(message, type);

        // Hide the original message
        element.style.display = 'none';
    });
});

// Export
window.Utils = Utils;

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showToast, toast };
}