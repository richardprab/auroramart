const ChatWidget = {
    currentSession: null,
    sessions: [],
    unreadCount: 0,
    isOpen: false,
    pollInterval: null,

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
        console.log('ChatWidget initializing...');
        this.attachEventListeners();
        this.loadSessions();
        this.startPolling();
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

        // Minimize button
        const minimizeBtn = document.getElementById('chat-minimize-btn');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.minimizeChat();
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

        // Session selector
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect) {
            sessionSelect.addEventListener('change', (e) => {
                this.switchSession(e.target.value);
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

    minimizeChat() {
        this.closeChat();
    },

    async loadSessions() {
        try {
            const response = await fetch('/chat/api/sessions/', {
                method: 'GET',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin' // Important for session cookies
            });

            if (response.ok) {
                const sessions = await response.json();
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
                    // No sessions, create first one
                    await this.createNewSession();
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

    async createNewSession() {
        try {
            const title = `Chat ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            
            const response = await fetch('/chat/api/sessions/', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify({ title })
            });

            if (response.ok) {
                const newSession = await response.json();
                this.currentSession = newSession;
                this.sessions.unshift(newSession); // Add to beginning of array
                this.updateSessionSelector();
                this.displayWelcomeMessage();
                
                // Show toast notification
                if (window.AuroraMart && window.AuroraMart.toast) {
                    window.AuroraMart.toast('New chat session created', 'success');
                }
            } else {
                console.error('Failed to create session:', response.status);
            }
        } catch (error) {
            console.error('Error creating session:', error);
        }
    },

    async loadMessages() {
        if (!this.currentSession) return;

        try {
            const response = await fetch(`/chat/api/sessions/${this.currentSession.id}/`, {
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
            <div class="text-center text-gray-500 py-4">
                <div class="bg-blue-50 rounded-lg p-4 mb-4">
                    <i data-lucide="headphones" class="w-12 h-12 mx-auto mb-2 text-blue-600"></i>
                    <p class="font-semibold text-gray-700">Welcome to Support Chat!</p>
                    <p class="text-sm mt-2">Our team is here to help you. Send us a message and we'll respond as soon as possible.</p>
                </div>
            </div>
        `;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    appendMessage(message, prepend = false) {
        const container = document.getElementById('chat-messages');
        const isAdmin = message.is_from_admin;
        
        const messageEl = document.createElement('div');
        messageEl.className = `flex ${isAdmin ? 'justify-start' : 'justify-end'}`;
        
        const time = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.innerHTML = `
            <div class="max-w-[75%]">
                <div class="${isAdmin ? 'bg-white' : 'bg-blue-600 text-white'} rounded-lg px-4 py-2 shadow">
                    ${isAdmin ? `<p class="text-xs font-semibold text-blue-600 mb-1">Support Team</p>` : ''}
                    <p class="text-sm break-words">${this.escapeHtml(message.message)}</p>
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
            const response = await fetch(`/chat/api/sessions/${this.currentSession.id}/send_message/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin',
                body: JSON.stringify({ message })
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
            await fetch(`/chat/api/sessions/${this.currentSession.id}/mark_as_read/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'same-origin'
            });
            
            // Update the session's unread count
            if (this.currentSession) {
                this.currentSession.unread_count = 0;
            }
            
            this.updateUnreadCountFromSessions();
        } catch (error) {
            console.error('Error marking as read:', error);
        }
    },

    updateUnreadCountFromSessions() {
        const totalUnread = this.sessions.reduce((sum, session) => sum + (session.unread_count || 0), 0);
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
        const select = document.getElementById('session-select');
        const indicator = document.getElementById('session-indicator');
        
        if (!select) return;
        
        select.innerHTML = '';
        
        if (this.sessions.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No conversations yet';
            select.appendChild(option);
            if (indicator) indicator.textContent = '';
            return;
        }
        
        this.sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.id;
            option.textContent = session.title || `Chat ${session.id}`;
            
            if (session.unread_count > 0) {
                option.textContent += ` (${session.unread_count} new)`;
            }
            
            option.selected = this.currentSession && session.id === this.currentSession.id;
            select.appendChild(option);
        });
        
        // Update indicator
        if (indicator) {
            indicator.textContent = `${this.sessions.length} ${this.sessions.length === 1 ? 'chat' : 'chats'}`;
        }
    },

    async switchSession(sessionId) {
        if (!sessionId) return;
        
        const session = this.sessions.find(s => s.id === parseInt(sessionId));
        if (session) {
            this.currentSession = session;
            await this.loadMessages();
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ChatWidget.init());
} else {
    ChatWidget.init();
}
