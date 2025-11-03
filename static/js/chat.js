const ChatWidget = {
    currentSession: null,
    sessions: [],
    unreadCount: 0,
    isOpen: false,
    pollInterval: null,

    init() {
        this.attachEventListeners();
        this.loadUnreadCount();
        this.startPolling();
    },

    attachEventListeners() {
        // Attach click handler to FAB button
        const fabButton = document.getElementById('chat-fab-button');
        if (fabButton) {
            fabButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleChat();
            });
        }

        // Attach minimize button handler
        const minimizeBtn = document.getElementById('chat-minimize-btn');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.minimizeChat();
            });
        }

        // Attach close button handler
        const closeBtn = document.getElementById('chat-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeChat();
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

        if (!this.currentSession) {
            await this.loadOrCreateSession();
        } else {
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

    async loadOrCreateSession() {
        try {
            const response = await fetch('/chat/api/sessions/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const sessions = await response.json();
                this.sessions = sessions;
                
                if (sessions.length > 0) {
                    this.currentSession = sessions[0];
                    await this.loadMessages();
                    this.updateSessionSelector();
                } else {
                    await this.createNewSession();
                }
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    },

    async createNewSession() {
        try {
            const response = await fetch('/chat/api/sessions/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: 'Support Chat' })
            });

            if (response.ok) {
                this.currentSession = await response.json();
                this.displayWelcomeMessage();
            }
        } catch (error) {
            console.error('Error creating session:', error);
        }
    },

    async loadMessages() {
        if (!this.currentSession) return;

        try {
            const response = await fetch(`/chat/api/sessions/${this.currentSession.id}/`, {
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                }
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

    async sendMessage(event) {
        event.preventDefault();
        
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message || !this.currentSession) return;
        
        try {
            const response = await fetch(`/chat/api/sessions/${this.currentSession.id}/send_message/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            if (response.ok) {
                const newMessage = await response.json();
                this.appendMessage(newMessage);
                input.value = '';
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    },

    async markAsRead() {
        if (!this.currentSession) return;

        try {
            await fetch(`/chat/api/sessions/${this.currentSession.id}/mark_as_read/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                }
            });
            
            this.updateUnreadBadge(0);
        } catch (error) {
            console.error('Error marking as read:', error);
        }
    },

    async loadUnreadCount() {
        try {
            const response = await fetch('/chat/api/sessions/unread_count/', {
                headers: {
                    'Authorization': `Bearer ${window.JWTAuth.getAccessToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.updateUnreadBadge(data.unread_count);
            }
        } catch (error) {
            console.error('Error loading unread count:', error);
        }
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
        if (this.sessions.length <= 1) return;

        const selector = document.getElementById('session-selector');
        const select = document.getElementById('session-select');
        
        selector.classList.remove('hidden');
        select.innerHTML = '<option value="">Select a conversation...</option>';
        
        this.sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.id;
            option.textContent = `${session.title} ${session.unread_count > 0 ? `(${session.unread_count})` : ''}`;
            option.selected = this.currentSession && session.id === this.currentSession.id;
            select.appendChild(option);
        });
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
            if (this.isOpen && this.currentSession) {
                await this.loadMessages();
            }
            await this.loadUnreadCount();
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
