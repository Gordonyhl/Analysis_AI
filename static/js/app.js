class ChatInterface {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.threadTitleInput = document.getElementById('threadTitle');
        this.sendButton = document.getElementById('sendButton');
        this.loading = document.getElementById('loading');
        this.fileInput = document.getElementById('fileInput');
        this.fileSelected = document.getElementById('fileSelected');
        this.uploadButton = document.getElementById('uploadButton');
        this.currentMessageElement = null;
        this.selectedFile = null;

        this.initializeEventListeners();
        this.autoResizeTextarea();
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
        contentDiv.textContent = '';

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.currentMessageElement = contentDiv;
        this.scrollToBottom();

        return contentDiv;
    }

    appendToStreamingMessage(chunk) {
        if (this.currentMessageElement) {
            this.currentMessageElement.textContent += chunk;
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
            this.uploadButton.textContent = 'Uploading...';

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
                Upload
            `;

        } catch (error) {
            console.error('Upload error:', error);
            this.showError(error.message || 'Failed to upload file');
            this.uploadButton.disabled = false;
            this.uploadButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z"/>
                </svg>
                Upload
            `;
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        const threadTitle = this.threadTitleInput.value.trim() || null;

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

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            this.setLoading(false);
                            this.currentMessageElement = null;
                            return;
                        }
                        if (data.startsWith('[ERROR]')) {
                            const errorMessage = data.slice(8);
                            this.showError(errorMessage);
                            this.setLoading(false);
                            this.currentMessageElement = null;
                            return;
                        }
                        if (data.trim()) {
                            this.appendToStreamingMessage(data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError(error.message || 'Failed to send message');
        } finally {
            this.setLoading(false);
            this.currentMessageElement = null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
});


