const NotificationSystem = {
    websocket: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 3000, // 3 seconds
    reconnectTimeout: null,
    isDropdownOpen: false,
    lastNotificationCount: null,
    hasShownInitialToast: false,
    hideTimeout: null,
    DROPDOWN_DELAY: 300, // Same delay as profile dropdown
    useWebSocket: true, // Flag to enable/disable WebSocket
    fallbackPolling: false, // Fallback to polling if WebSocket fails
    pollInterval: null,
    checkInterval: 30000, // Check every 30 seconds (fallback only)
    
    init() {
        this.updateBadge();
        this.attachEventListeners();
        
        // Try WebSocket first, fallback to polling if it fails
        if (this.useWebSocket) {
            this.connectWebSocket();
        } else {
            this.startPolling();
        }
    },
    
    attachEventListeners() {
        const bell = document.getElementById('notification-bell');
        const dropdown = document.getElementById('notification-dropdown');
        const container = document.getElementById('notification-dropdown-container');
        
        if (!bell || !dropdown || !container) return;
        
        // Function to show dropdown
        const showDropdown = () => {
            clearTimeout(this.hideTimeout);
            dropdown.classList.remove('hidden');
            this.isDropdownOpen = true;
            this.loadNotifications();
        };
        
        // Function to hide dropdown
        const hideDropdown = () => {
            dropdown.classList.add('hidden');
            this.isDropdownOpen = false;
        };
        
        // Function to hide dropdown with delay
        const hideDropdownDelayed = () => {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = setTimeout(() => {
                hideDropdown();
            }, this.DROPDOWN_DELAY);
        };
        
        // Show dropdown on hover over button
        bell.addEventListener('mouseenter', () => {
            showDropdown();
        });
        
        // Hide dropdown with delay when leaving button
        bell.addEventListener('mouseleave', (e) => {
            // Check if moving to dropdown
            const rect = dropdown.getBoundingClientRect();
            const isMovingToDropdown = e.clientY >= rect.top && e.clientY <= rect.bottom;
            
            if (!isMovingToDropdown) {
                hideDropdownDelayed();
            }
        });
        
        // Keep dropdown visible when hovering over it
        dropdown.addEventListener('mouseenter', () => {
            showDropdown();
        });
        
        // Hide dropdown with delay when leaving dropdown
        dropdown.addEventListener('mouseleave', () => {
            hideDropdownDelayed();
        });
        
        // Toggle dropdown on click
        bell.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (dropdown.classList.contains('hidden')) {
                showDropdown();
            } else {
                clearTimeout(this.hideTimeout);
                hideDropdown();
            }
        });
        
        // Mark all as read
        const markAllBtn = document.getElementById('mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target) && this.isDropdownOpen) {
                clearTimeout(this.hideTimeout);
                hideDropdown();
            }
        });
        
        // Close dropdown when pressing Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !dropdown.classList.contains('hidden')) {
                clearTimeout(this.hideTimeout);
                hideDropdown();
            }
        });
    },
    
    openDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) {
            dropdown.classList.remove('hidden');
            this.isDropdownOpen = true;
            this.loadNotifications();
        }
    },
    
    closeDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
            this.isDropdownOpen = false;
        }
    },
    
    async loadNotifications() {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;
        
        try {
            const response = await fetch('/notifications/api/recent/');
            if (response.ok) {
                const data = await response.json();
                this.renderNotifications(data.notifications || []);
            } else {
                listContainer.innerHTML = '<div class="p-4 text-center text-gray-500 text-sm">Failed to load notifications</div>';
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
            listContainer.innerHTML = '<div class="p-4 text-center text-gray-500 text-sm">Error loading notifications</div>';
        }
    },
    
    renderNotifications(notifications) {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;
        
        if (notifications.length === 0) {
            listContainer.innerHTML = `
                <div class="p-8 text-center">
                    <i data-lucide="bell-off" class="w-12 h-12 mx-auto text-gray-300 mb-2"></i>
                    <p class="text-sm text-gray-500">No notifications</p>
                </div>
            `;
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
            return;
        }
        
        listContainer.innerHTML = notifications.map(notif => {
            const iconMap = {
                'message': { icon: 'message-circle', color: 'blue' },
                'sale': { icon: 'tag', color: 'green' },
                'stock': { icon: 'package', color: 'purple' },
                'order': { icon: 'shopping-bag', color: 'yellow' },
                'review': { icon: 'star', color: 'pink' },
                'platform': { icon: 'bell', color: 'gray' }
            };
            const config = iconMap[notif.notification_type] || iconMap['platform'];
            const timeAgo = this.getTimeAgo(notif.created_at);
            
            return `
                <div class="p-3 hover:bg-gray-50 border-b border-gray-100 cursor-pointer ${!notif.is_read ? 'bg-blue-50' : ''}" 
                     onclick="NotificationSystem.handleNotificationClick(${notif.id}, '${notif.link || ''}')">
                    <div class="flex gap-3">
                        <div class="flex-shrink-0">
                            <div class="w-10 h-10 rounded-full bg-${config.color}-100 flex items-center justify-center">
                                <i data-lucide="${config.icon}" class="w-5 h-5 text-${config.color}-600"></i>
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-sm text-gray-900 ${!notif.is_read ? 'font-semibold' : ''}">${this.escapeHtml(notif.message)}</p>
                            <p class="text-xs text-gray-500 mt-1">${timeAgo}</p>
                        </div>
                        ${!notif.is_read ? '<div class="flex-shrink-0"><span class="w-2 h-2 bg-blue-600 rounded-full block"></span></div>' : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },
    
    async handleNotificationClick(notifId, link) {
        // Mark as read
        try {
            await fetch(`/notifications/${notifId}/read/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            // Update badge
            this.updateBadge();
            
            // Navigate if link exists
            if (link) {
                window.location.href = link;
            } else {
                // Reload notifications
                this.loadNotifications();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    },
    
    async markAllAsRead() {
        try {
            const response = await fetch('/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.updateBadge();
                this.loadNotifications();
                if (window.toast) {
                    window.toast.success('All notifications marked as read');
                }
            }
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    },
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : null;
    },
    
    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return date.toLocaleDateString();
    },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    connectWebSocket() {
        // Determine WebSocket URL based on current page
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/notifications/`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.reconnectAttempts = 0;
                this.fallbackPolling = false;
                
                // Stop polling if it was running
                this.stopPolling();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onerror = (error) => {
                // Silently handle WebSocket errors - fallback to polling
                // Errors are handled by onclose event which triggers polling fallback
            };
            
            this.websocket.onclose = () => {
                this.websocket = null;
                
                // Attempt to reconnect silently
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    
                    this.reconnectTimeout = setTimeout(() => {
                        this.connectWebSocket();
                    }, this.reconnectDelay);
                } else {
                    // Fallback to polling after max reconnection attempts
                    this.fallbackPolling = true;
                    this.startPolling();
                }
            };
        } catch (error) {
            // Silently fallback to polling if WebSocket connection fails
            this.fallbackPolling = true;
            this.startPolling();
        }
    },
    
    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
    },
    
    handleWebSocketMessage(data) {
        if (data.type === 'unread_count') {
            const newCount = data.count || 0;
            
            // Initialize lastNotificationCount on first message
            if (this.lastNotificationCount === null) {
                this.lastNotificationCount = newCount;
                this.updateBadgeCount(newCount);
                return;
            }
            
            // Update badge
            this.updateBadgeCount(newCount);
            
            // Only show toast if count increased (new notification arrived)
            if (newCount > this.lastNotificationCount) {
                this.showNewNotificationToast(newCount - this.lastNotificationCount);
            }
            
            this.lastNotificationCount = newCount;
        } else if (data.type === 'notification') {
            // New notification received
            const notification = data.notification;
            
            // Update badge count
            if (notification && !notification.is_read) {
                const currentCount = this.getCurrentBadgeCount();
                this.updateBadgeCount(currentCount + 1);
                this.showNewNotificationToast(1);
            }
            
            // Reload notifications if dropdown is open
            if (this.isDropdownOpen) {
                this.loadNotifications();
            }
        } else if (data.type === 'pong') {
            // Response to ping, connection is alive
            // No action needed
        }
    },
    
    startPolling() {
        // Only start polling if WebSocket is not available
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            return;
        }
        
        // Initial check
        this.checkNotifications();
        
        // Set up polling
        this.pollInterval = setInterval(() => {
            this.checkNotifications();
        }, this.checkInterval);
    },
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },
    
    async checkNotifications() {
        try {
            const response = await fetch('/notifications/api/unread-count/');
            if (response.ok) {
                const data = await response.json();
                const newCount = data.count || 0;
                
                // Initialize lastNotificationCount on first check
                if (this.lastNotificationCount === null) {
                    this.lastNotificationCount = newCount;
                    this.updateBadgeCount(newCount);
                    return;
                }
                
                // Update badge
                this.updateBadgeCount(newCount);
                
                // Only show toast if count increased (new notification arrived)
                if (newCount > this.lastNotificationCount) {
                    this.showNewNotificationToast(newCount - this.lastNotificationCount);
                }
                
                this.lastNotificationCount = newCount;
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    },
    
    getCurrentBadgeCount() {
        // Badge notification removed - always return 0
        return 0;
        // const badge = document.getElementById('notification-count');
        // if (!badge || badge.classList.contains('hidden')) {
        //     return 0;
        // }
        // const count = parseInt(badge.textContent);
        // return isNaN(count) ? 0 : count;
    },
    
    updateBadgeCount(count) {
        // Badge notification removed - no longer showing count
        // const badge = document.getElementById('notification-count');
        // if (!badge) return;
        // 
        // if (count > 0) {
        //     badge.textContent = count > 99 ? '99+' : count;
        //     badge.classList.remove('hidden');
        // } else {
        //     badge.classList.add('hidden');
        // }
    },
    
    async updateBadge() {
        try {
            const response = await fetch('/notifications/api/unread-count/');
            if (response.ok) {
                const data = await response.json();
                this.updateBadgeCount(data.count || 0);
            }
        } catch (error) {
            console.error('Error updating notification badge:', error);
        }
    },
    
    showNewNotificationToast(count) {
        // Only show toast once per session to avoid flashing
        if (!this.hasShownInitialToast) {
            this.hasShownInitialToast = true;
            return;
        }
        
        const message = count === 1 
            ? '🔔 You have 1 new notification' 
            : `🔔 You have ${count} new notifications`;
        
        if (window.toast) {
            window.toast.info(message);
        } else if (window.AuroraMart && window.AuroraMart.toast) {
            window.AuroraMart.toast(message, 'info');
        }
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Initialize for authenticated users (check for notification bell instead of badge)
        const notificationBell = document.getElementById('notification-bell');
        if (notificationBell) {
            NotificationSystem.init();
        }
    });
} else {
    // Initialize for authenticated users (check for notification bell instead of badge)
    const notificationBell = document.getElementById('notification-bell');
    if (notificationBell) {
        NotificationSystem.init();
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    NotificationSystem.disconnectWebSocket();
    NotificationSystem.stopPolling();
});

