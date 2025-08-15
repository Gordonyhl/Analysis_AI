class ChatInterface {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.threadTitleInput = document.getElementById('threadTitle');
        this.newThreadButton = document.getElementById('newThreadButton');
        this.sendButton = document.getElementById('sendButton');
        this.loading = document.getElementById('loading');
        this.fileInput = document.getElementById('fileInput');
        this.fileSelected = document.getElementById('fileSelected');
        this.uploadButton = document.getElementById('uploadButton');
        this.threadList = document.getElementById('thread-list');
        this.currentMessageElement = null;
        this.currentStreamingContent = null; // To hold the full Markdown content
        this.selectedFile = null;
        this.currentThreadTitle = '';

        this.initializeEventListeners();
        this.autoResizeTextarea();
        this.loadThreads();
        this.ensureThreadTitle();
        this.initializeThemeListener();
    }

    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());

        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });

        this.fileInput.addEventListener('change', (e) => this.handleFileSelection(e));
        this.uploadButton.addEventListener('click', () => this.uploadFile());

        this.threadList.addEventListener('click', (e) => {
            const target = e.target.closest('li');
            if (target) {
                const title = target.dataset.title;
                const threadId = target.dataset.id;
                this.currentThreadTitle = title || '';
                if (this.threadTitleInput) this.threadTitleInput.value = this.currentThreadTitle;
                if (threadId) {
                    this.loadConversation(threadId);
                }
            }
        });

        if (this.newThreadButton) {
            this.newThreadButton.addEventListener('click', () => this.startNewConversation());
        }
    }

    ensureThreadTitle() {
        const current = (this.threadTitleInput ? (this.threadTitleInput.value || '').trim() : this.currentThreadTitle.trim());
        if (!current) {
            const auto = this.generateTimestampTitle();
            this.currentThreadTitle = auto;
            if (this.threadTitleInput) this.threadTitleInput.value = auto;
        }
    }

    // Removed pre-creation to avoid creating threads on page refresh or button click

    generateTimestampTitle() {
        const now = new Date();
        const dd = String(now.getDate()).padStart(2, '0');
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const yyyy = String(now.getFullYear());
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        const ss = String(now.getSeconds()).padStart(2, '0');
        // Format: DDMMYYYY_HHMMSS
        return `${dd}${mm}${yyyy}_${hh}${min}${ss}`;
    }

    startNewConversation() {
        // Set a fresh auto title and clear current messages view (keep welcome hidden by clearing all)
        const auto = this.generateTimestampTitle();
        this.currentThreadTitle = auto;
        if (this.threadTitleInput) this.threadTitleInput.value = auto;
        this.messagesContainer.innerHTML = '';
        this.currentMessageElement = null;
        this.currentStreamingContent = null;
        // Optionally focus the message box
        this.messageInput.focus();
        // Do not create thread yet; it will be created on first send
    }

    initializeThemeListener() {
        // Listen for theme changes and update message styles accordingly
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                // Small delay to ensure CSS classes are updated
                setTimeout(() => {
                    // Re-render all markdown messages to apply new theme styles
                    this.refreshMarkdownMessages();
                }, 10);
            });
        }
    }

    refreshMarkdownMessages() {
        // Re-render all assistant messages with markdown to apply new theme styles
        const assistantMessages = this.messagesContainer.querySelectorAll('.message.assistant .message-content');
        assistantMessages.forEach(contentDiv => {
            // Get the original markdown content
            const markdownContent = contentDiv.textContent || contentDiv.innerText;
            // Re-render with marked
            contentDiv.innerHTML = marked.parse(markdownContent);
        });
    }

    async loadThreads() {
        try {
            const response = await fetch('/api/threads');
            if (!response.ok) {
                throw new Error(`Failed to load threads: ${response.status}`);
            }
            const threads = await response.json();
            this.threadList.innerHTML = '';
            threads.forEach(thread => {
                const li = document.createElement('li');
                li.textContent = thread.title || '(untitled)';
                li.dataset.title = thread.title || '';
                li.dataset.id = thread.id;
                this.threadList.appendChild(li);
            });
        } catch (error) {
            console.error('Error loading threads:', error);
            this.showError('Could not load conversation history.');
        }
    }

    async loadConversation(threadId) {
        try {
            // Clear current messages except the initial system welcome
            this.messagesContainer.innerHTML = '';
            const response = await fetch(`/api/threads/${threadId}/messages`);
            if (!response.ok) {
                throw new Error(`Failed to load conversation: ${response.status}`);
            }
            const data = await response.json();
            const messages = Array.isArray(data.messages) ? data.messages : [];
            messages.forEach(m => {
                const role = m.role === 'assistant' ? 'assistant' : (m.role === 'system' ? 'system' : 'user');
                // Use markdown rendering for assistant messages; plain text for user/system
                if (role === 'assistant') {
                    this.addMessageWithHTML(m.content || '', 'assistant');
                } else {
                    this.addMessage(m.content || '', role);
                }
            });
            this.scrollToBottom();
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Could not load conversation.');
        }
    }

    addMessageWithHTML(content, type = 'assistant') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'user' ? 'You' :
                           type === 'assistant' ? 'AI' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = marked.parse(content);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        return contentDiv;
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 128) + 'px';
    }

    addMessage(content, type = 'user') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'user' ? 'You' :
                           type === 'assistant' ? 'AI' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        return contentDiv;
    }

    addStreamingMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = ''; // Start with empty HTML

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.currentMessageElement = contentDiv;
        this.currentStreamingContent = ''; // Reset content holder
        this.scrollToBottom();

        return contentDiv;
    }

    appendToStreamingMessage(chunk) {
        if (this.currentMessageElement) {
            this.currentStreamingContent += chunk; // Append markdown chunk
            this.currentMessageElement.innerHTML = marked.parse(this.currentStreamingContent); // Re-render
            this.scrollToBottom();
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `Error: ${message}`;
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }

    setLoading(isLoading) {
        this.loading.classList.toggle('show', isLoading);
        this.sendButton.disabled = isLoading;
        this.messageInput.disabled = isLoading;
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    clearInput() {
        this.messageInput.value = '';
        this.autoResizeTextarea();
    }

    handleFileSelection(event) {
        const file = event.target.files[0];
        if (file) {
            this.selectedFile = file;
            this.fileSelected.textContent = `Selected: ${file.name}`;
            this.uploadButton.disabled = false;
        } else {
            this.selectedFile = null;
            this.fileSelected.textContent = '';
            this.uploadButton.disabled = true;
        }
    }

    async uploadFile() {
        if (!this.selectedFile) return;

        const formData = new FormData();
        formData.append('file', this.selectedFile);

        try {
            this.uploadButton.disabled = true;

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }

            const result = await response.json();

            this.addMessage(
                `You have uploaded "${result.filename}". You can now ask questions about it.`,
                'system'
            );

            this.fileInput.value = '';
            this.selectedFile = null;
            this.fileSelected.textContent = '';
            this.uploadButton.disabled = true;
            this.uploadButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z"/>
                </svg>
            `;

        } catch (error) {
            console.error('Upload error:', error);
            this.showError(error.message || 'Failed to upload file');
            this.uploadButton.disabled = false;
            this.uploadButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z"/>
                </svg>
            `;
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Ensure a title at send-time; create-on-send behavior
        const threadTitle = (this.currentThreadTitle && this.currentThreadTitle.trim()) ? this.currentThreadTitle.trim() : this.generateTimestampTitle();
        this.currentThreadTitle = threadTitle;

        this.addMessage(message, 'user');
        this.clearInput();
        this.setLoading(true);

        try {
            this.addStreamingMessage();

            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    thread_title: threadTitle
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Robust SSE parsing with buffering across chunk boundaries
            let textBuffer = '';
            let eventDataLines = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                textBuffer += decoder.decode(value, { stream: true });

                // Process complete lines only; keep the remainder in buffer
                let newlineIndex;
                while ((newlineIndex = textBuffer.indexOf('\n')) !== -1) {
                    const line = textBuffer.slice(0, newlineIndex);
                    textBuffer = textBuffer.slice(newlineIndex + 1);

                    // Empty line denotes end of an SSE event
                    if (line === '') {
                        const dataPayload = eventDataLines.join('\n');
                        eventDataLines = [];

                        if (!dataPayload) continue;

                        if (dataPayload === '[DONE]') {
                            this.setLoading(false);
                            this.currentMessageElement = null;
                            this.currentStreamingContent = null;
                            // Refresh thread list so the new conversation appears immediately
                            this.loadThreads();
                            return;
                        }
                        if (dataPayload.startsWith('[ERROR]')) {
                            const errorMessage = dataPayload.slice(8);
                            this.showError(errorMessage);
                            this.setLoading(false);
                            this.currentMessageElement = null;
                            this.currentStreamingContent = null;
                            return;
                        }
                        this.appendToStreamingMessage(dataPayload);
                        continue;
                    }

                    // Only process data fields; ignore id:, event:, retry:
                    if (line.startsWith('data:')) {
                        // Per SSE spec, a single optional space may follow the colon
                        const afterColon = line.slice(5);
                        const valuePart = afterColon.startsWith(' ') ? afterColon.slice(1) : afterColon;
                        eventDataLines.push(valuePart);
                    }
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError(error.message || 'Failed to send message');
        } finally {
            this.setLoading(false);
            this.currentMessageElement = null;
            this.currentStreamingContent = null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
});


