const ChatWidget = {
    currentSession: null,
    sessions: [],
    unreadCount: 0,
    isOpen: false,
    pollInterval: null,
    sessionListOpen: true,
    sessionToDelete: null,

    // Get CSRF token for session authentication
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : null;
    },

    // Get authentication headers for session auth
    getAuthHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };
    },

    init() {
        // Get current user ID from chat window data attribute
        const chatWindow = document.getElementById('chat-window');
        if (chatWindow) {
            const userId = chatWindow.getAttribute('data-user-id');
            this.currentUserId = userId ? parseInt(userId) : null;
        }
        
        this.attachEventListeners();
        this.attachProductChatListeners();
        this.loadSessions();
        this.startPolling();
    },

    attachProductChatListeners() {
        // Listen for "Chat with Seller" button clicks
        document.addEventListener('click', (e) => {
            const chatWithSellerBtn = e.target.closest('#chat-with-seller-btn');
            if (chatWithSellerBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                const productId = chatWithSellerBtn.dataset.productId;
                const productUrl = chatWithSellerBtn.dataset.productUrl;
                const productName = chatWithSellerBtn.dataset.productName;
                
                if (productId && productUrl) {
                    this.createProductChat(productId, productUrl, productName);
                }
            }
        });
    },

    attachEventListeners() {
        // FAB button
        const fabButton = document.getElementById('chat-fab-button');
        if (fabButton) {
            fabButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleChat();
            });
        }

        // New chat button
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.createNewSession();
            });
        }

        // Close button
        const closeBtn = document.getElementById('chat-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeChat();
            });
        }

        // Session list will be handled by click delegation in updateSessionSelector

        // Session toggle
        const sessionToggle = document.getElementById('session-toggle');
        if (sessionToggle) {
            sessionToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleSessionList();
            });
        }

        // Chat form
        const chatForm = document.getElementById('chat-form');
        if (chatForm) {
            chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // Close chat when clicking outside
        document.addEventListener('click', (e) => {
            const chatWindow = document.getElementById('chat-window');
            const chatFab = document.getElementById('chat-fab');
            
            if (this.isOpen && chatWindow && !chatWindow.contains(e.target) && !chatFab.contains(e.target)) {
                this.closeChat();
            }
        });

        // Close delete modal when clicking outside
        const deleteModal = document.getElementById('delete-chat-modal');
        if (deleteModal) {
            deleteModal.addEventListener('click', (e) => {
                if (e.target === deleteModal) {
                    this.hideDeleteModal();
                }
            });
        }

        // Close delete modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideDeleteModal();
            }
        });
    },

    async toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            await this.openChat();
        }
    },

    async openChat() {
        this.isOpen = true;
        const chatWindow = document.getElementById('chat-window');
        chatWindow.classList.remove('hidden');
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Ensure session list is visible when opening chat
        const sessionList = document.getElementById('session-list');
        const chevron = document.getElementById('session-chevron');
        if (sessionList && this.sessionListOpen) {
            sessionList.style.display = 'block';
            if (chevron) chevron.style.transform = 'rotate(0deg)';
        }

        // Load sessions if not loaded
        if (this.sessions.length === 0) {
            await this.loadSessions();
        }

        // Load messages if we have a current session
        if (this.currentSession) {
            await this.loadMessages();
        }
    },

    closeChat() {
        this.isOpen = false;
        document.getElementById('chat-window').classList.add('hidden');
    },

    async loadSessions() {
        try {
            const response = await fetch('/chat/ajax/conversations/', {
                method: 'GET',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin' // Important for session cookies
            });

            if (response.ok) {
                // Check if response is actually JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    // Not JSON response, probably HTML redirect or error page
                    return;
                }
                
                let data;
                try {
                    data = await response.json();
                } catch (jsonError) {
                    // Response is not valid JSON, skip
                    console.warn('Response is not valid JSON, skipping session load');
                    return;
                }
                
                // Handle paginated response - extract results array
                const sessions = Array.isArray(data) ? data : (data.results || []);
                this.sessions = sessions;
                
                if (sessions.length > 0) {
                    // Set current session to the first one if not set
                    if (!this.currentSession) {
                        this.currentSession = sessions[0];
                    }
                    this.updateSessionSelector();
                    
                    // Load messages if chat is open
                    if (this.isOpen) {
                        await this.loadMessages();
                    }
                } else {
                    // No sessions exist - just update the UI, don't auto-create
                    this.updateSessionSelector();
                }
                
                // Update unread count
                this.updateUnreadCountFromSessions();
            } else {
                console.error('Failed to load sessions:', response.status);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    },

    async createNewSession(productId = null, productUrl = null, productName = null) {
        try {
            let title = `Chat ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            if (productName) {
                title = `Product Inquiry: ${productName}`;
            }
            
            const requestBody = { subject: title };
            if (productId) {
                requestBody.product_id = productId;
            }
            if (productUrl) {
                // Make product_url absolute if it's relative
                const absoluteUrl = productUrl.startsWith('http') ? productUrl : `${window.location.origin}${productUrl}`;
                requestBody.product_url = absoluteUrl;
            }
            
            const response = await fetch('/chat/ajax/conversations/create/', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                const newSession = await response.json();
                this.currentSession = newSession;
                this.sessions.unshift(newSession); // Add to beginning of array
                this.updateSessionSelector();
                
                // Load messages to show the initial product link message
                await this.loadMessages();
                
                // Show toast notification
                if (window.AuroraMart && window.AuroraMart.toast) {
                    window.AuroraMart.toast('Chat session created', 'success');
                }
            } else {
                console.error('Failed to create session:', response.status);
            }
        } catch (error) {
            console.error('Error creating session:', error);
        }
    },

    async createProductChat(productId, productUrl, productName) {
        // Open chat widget first
        if (!this.isOpen) {
            await this.openChat();
        }
        
        // Create new session with product info
        await this.createNewSession(productId, productUrl, productName);
    },

    async loadMessages() {
        if (!this.currentSession) return;

        try {
            const response = await fetch(`/chat/ajax/conversations/${this.currentSession.id}/`, {
                headers: this.getAuthHeaders(),
                credentials: 'same-origin'
            });

            if (response.ok) {
                const session = await response.json();
                this.displayMessages(session.messages);
                await this.markAsRead();
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    },

    displayMessages(messages) {
        const container = document.getElementById('chat-messages');
        
        if (messages.length === 0) {
            this.displayWelcomeMessage();
            return;
        }

        container.innerHTML = '';
        messages.forEach(msg => {
            this.appendMessage(msg);
        });

        this.scrollToBottom();
    },

    displayWelcomeMessage() {
        const container = document.getElementById('chat-messages');
        container.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <i data-lucide="headphones" class="w-12 h-12 mx-auto mb-2 text-blue-600"></i>
                <p class="font-semibold text-gray-700">Welcome to Support Chat!</p>
                <p class="text-sm mt-2">Our team is here to help you. Send us a message and we'll respond as soon as possible.</p>
            </div>
        `;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    appendMessage(message, prepend = false) {
        const container = document.getElementById('chat-messages');
        // Check if sender is admin/staff by checking if sender ID differs from current user
        // If currentUserId is not set, try to get it from chat window
        if (!this.currentUserId) {
            const chatWindow = document.getElementById('chat-window');
            if (chatWindow) {
                const userId = chatWindow.getAttribute('data-user-id');
                this.currentUserId = userId ? parseInt(userId) : null;
            }
        }
        // Determine if message is from staff/admin
        // Check both the explicit is_staff flag and the sender ID comparison
        const isAdmin = message.is_staff || (message.sender && this.currentUserId && message.sender !== this.currentUserId);
        
        // Get user's first name from chat window data attribute
        const chatWindow = document.getElementById('chat-window');
        const userFirstName = chatWindow ? (chatWindow.getAttribute('data-user-first-name') || 'You') : 'You';
        
        const messageEl = document.createElement('div');
        // Staff messages should be on the left (justify-start), customer messages on the right (justify-end)
        messageEl.className = `flex ${isAdmin ? 'justify-start' : 'justify-end'}`;
        
        const time = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.innerHTML = `
            <div class="max-w-[75%]">
                <div class="${isAdmin ? 'bg-white' : 'bg-blue-600 text-white'} rounded-lg px-4 py-2 shadow">
                    ${isAdmin ? `<p class="text-xs font-semibold text-blue-600 mb-1">Support Team</p>` : `<p class="text-xs font-semibold text-blue-100 mb-1">${this.escapeHtml(userFirstName)}</p>`}
                    <p class="text-sm break-words">${this.escapeHtml(message.content || message.message)}</p>
                </div>
                <p class="text-xs text-gray-500 mt-1 ${isAdmin ? 'text-left' : 'text-right'}">${time}</p>
            </div>
        `;
        
        if (prepend) {
            container.insertBefore(messageEl, container.firstChild);
        } else {
            container.appendChild(messageEl);
        }
    },

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Create session if doesn't exist
        if (!this.currentSession) {
            await this.createNewSession();
        }
        
        if (!this.currentSession) {
            console.error('No current session');
            return;
        }
        
        try {
            const response = await fetch(`/chat/ajax/conversations/${this.currentSession.id}/send/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify({ content: message })
            });

            if (response.ok) {
                const newMessage = await response.json();
                
                // Clear welcome message if it exists
                const container = document.getElementById('chat-messages');
                const welcomeMsg = container.querySelector('.bg-blue-50');
                if (welcomeMsg && welcomeMsg.parentElement) {
                    welcomeMsg.parentElement.remove();
                }
                
                this.appendMessage(newMessage);
                input.value = '';
                this.scrollToBottom();
            } else {
                console.error('Failed to send message:', response.status);
                if (window.AuroraMart && window.AuroraMart.toast) {
                    window.AuroraMart.toast('Failed to send message', 'error');
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            if (window.AuroraMart && window.AuroraMart.toast) {
                window.AuroraMart.toast('Failed to send message', 'error');
            }
        }
    },

    async markAsRead() {
        if (!this.currentSession) return;

        try {
            await fetch(`/chat/ajax/conversations/${this.currentSession.id}/mark-read/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin'
            });
            
            // Update the session's unread count
            if (this.currentSession) {
                this.currentSession.user_has_unread = false;
            }
            
            this.updateUnreadCountFromSessions();
        } catch (error) {
            console.error('Error marking as read:', error);
        }
    },

    updateUnreadCountFromSessions() {
        const totalUnread = this.sessions.reduce((sum, session) => sum + (session.user_has_unread ? 1 : 0), 0);
        this.updateUnreadBadge(totalUnread);
    },

    updateUnreadBadge(count) {
        const badge = document.getElementById('chat-badge');
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
        this.unreadCount = count;
    },

    updateSessionSelector() {
        const sessionList = document.getElementById('session-list');
        const indicator = document.getElementById('session-indicator');
        
        if (!sessionList) return;
        
        sessionList.innerHTML = '';
        
        if (this.sessions.length === 0) {
            sessionList.innerHTML = '<div class="text-xs text-gray-500 text-center py-2">No conversations yet</div>';
            if (indicator) indicator.textContent = '';
            return;
        }
        
        // Update indicator
        if (indicator) {
            indicator.textContent = `${this.sessions.length} ${this.sessions.length === 1 ? 'chat' : 'chats'}`;
        }
        
        // Build session items
        this.sessions.forEach(session => {
            const isActive = this.currentSession && session.id === this.currentSession.id;
            
            const sessionItem = document.createElement('div');
            sessionItem.className = `flex items-center gap-2 p-2 rounded transition group ${
                isActive ? 'bg-blue-100 hover:bg-blue-200' : 'hover:bg-gray-100'
            }`;
            sessionItem.dataset.sessionId = session.id;
            
            // Session title and info (clickable area)
            const sessionInfo = document.createElement('div');
            sessionInfo.className = 'flex-1 min-w-0 cursor-pointer';
            sessionInfo.onclick = (e) => {
                e.stopPropagation();
                this.switchSession(session.id);
            };
            
            const titleEl = document.createElement('div');
            titleEl.className = 'text-sm font-medium truncate';
            titleEl.textContent = session.subject || `Chat ${session.id}`;
            
            // Unread badge
            if (session.user_has_unread) {
                const badge = document.createElement('span');
                badge.className = 'inline-block ml-2 bg-red-600 text-white text-xs px-2 py-0.5 rounded-full';
                badge.textContent = 'New';
                titleEl.appendChild(badge);
            }
            
            sessionInfo.appendChild(titleEl);
            sessionItem.appendChild(sessionInfo);
            
            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'p-1 text-red-600 hover:bg-transparent rounded opacity-0 group-hover:opacity-100 transition flex-shrink-0';
            deleteBtn.title = 'Delete chat';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                this.deleteSession(session.id);
            };
            deleteBtn.innerHTML = '<i data-lucide="trash-2" class="w-4 h-4"></i>';
            
            sessionItem.appendChild(deleteBtn);
            sessionList.appendChild(sessionItem);
        });
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    async switchSession(sessionId) {
        if (!sessionId) return;
        
        const session = this.sessions.find(s => s.id === parseInt(sessionId));
        if (session) {
            this.currentSession = session;
            await this.loadMessages();
            // Update UI to reflect the active session
            this.updateSessionSelector();
        }
    },

    deleteSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) return;

        // Store session to delete and show modal
        this.sessionToDelete = sessionId;
        
        // Update modal message with session title
        const messageEl = document.getElementById('delete-chat-message');
        if (messageEl) {
            messageEl.textContent = `This will permanently delete all messages in "${session.subject || 'this conversation'}". This action cannot be undone.`;
        }
        
        this.showDeleteModal();
    },

    showDeleteModal() {
        const modal = document.getElementById('delete-chat-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.style.overflow = 'hidden';
            
            // Initialize Lucide icons in modal
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    },

    hideDeleteModal() {
        const modal = document.getElementById('delete-chat-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.style.overflow = '';
        }
        this.sessionToDelete = null;
    },

    async confirmDeleteSession() {
        if (!this.sessionToDelete) return;
        
        const sessionId = this.sessionToDelete;
        this.hideDeleteModal();

        try {
            const response = await fetch(`/chat/ajax/conversations/${sessionId}/delete/`, {
                method: 'DELETE',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin'
            });

            if (response.ok || response.status === 204) {
                // Remove from sessions array
                this.sessions = this.sessions.filter(s => s.id !== sessionId);

                // If we deleted the current session, switch to another
                if (this.currentSession && this.currentSession.id === sessionId) {
                    this.currentSession = null;
                    
                    // Set to first remaining session or null
                    if (this.sessions.length > 0) {
                        this.currentSession = this.sessions[0];
                        await this.loadMessages();
                    } else {
                        // No sessions left, show welcome message
                        this.displayWelcomeMessage();
                    }
                }

                // Update UI
                this.updateSessionSelector();
                this.updateUnreadCountFromSessions();

                if (window.AuroraMart && window.AuroraMart.toast) {
                    window.AuroraMart.toast('Chat session deleted', 'success');
                }
            } else {
                console.error('Failed to delete session:', response.status);
                if (window.AuroraMart && window.AuroraMart.toast) {
                    window.AuroraMart.toast('Failed to delete chat session', 'error');
                }
            }
        } catch (error) {
            console.error('Error deleting session:', error);
            if (window.AuroraMart && window.AuroraMart.toast) {
                window.AuroraMart.toast('Failed to delete chat session', 'error');
            }
        }
    },

    toggleSessionList() {
        const sessionList = document.getElementById('session-list');
        const chevron = document.getElementById('session-chevron');
        
        if (!sessionList || !chevron) return;
        
        this.sessionListOpen = !this.sessionListOpen;
        
        if (this.sessionListOpen) {
            sessionList.style.display = 'block';
            chevron.style.transform = 'rotate(0deg)';
        } else {
            sessionList.style.display = 'none';
            chevron.style.transform = 'rotate(-90deg)';
        }
    },

    startPolling() {
        // Poll for new messages every 5 seconds
        this.pollInterval = setInterval(async () => {
            await this.loadSessions();
        }, 5000);
    },

    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize when DOM is ready (skip if flag is set)
if (!window.skipChatInit) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ChatWidget.init());
    } else {
        ChatWidget.init();
    }
}
