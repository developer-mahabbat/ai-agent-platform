document.addEventListener('alpine:init', () => {
    Alpine.data('chatApp', () => ({
        chats: [],
        currentChatId: null,
        messages: [],
        input: '',
        streaming: false,
        model: 'gpt-4o',
        provider: 'openai',
        sessionId: 'session_' + Math.random().toString(36).slice(2, 14),
        sidebarOpen: window.innerWidth > 768,
        providers: [],

        thinkingContent: '',
        isThinking: false,
        thinkingOpen: true,
        thinkingDone: false,

        searchEnabled: false,
        agentsEnabled: false,
        isSearching: false,

        showSourcesModal: false,
        activeSources: [],

        init() {
            this.loadChats();
            this.loadProviders();
            this.checkUrlForChat();
            this.setupCopyButtons();
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 768 && !e.target.closest('.sidebar') && !e.target.closest('header button')) {
                    this.sidebarOpen = false;
                }
            });
        },

        setupCopyButtons() {
            document.addEventListener('click', (e) => {
                const btn = e.target.closest('.copy-btn');
                if (!btn) return;
                const wrapper = btn.closest('.code-block-wrapper');
                if (!wrapper) return;
                const code = wrapper.querySelector('pre code');
                if (!code) return;
                const text = code.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    btn.classList.add('copied');
                    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg> Copied';
                    setTimeout(() => {
                        btn.classList.remove('copied');
                        btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy';
                    }, 2000);
                }).catch(() => {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    btn.classList.add('copied');
                    btn.textContent = 'Copied!';
                    setTimeout(() => {
                        btn.classList.remove('copied');
                        btn.textContent = 'Copy';
                    }, 2000);
                });
            });
        },

        checkUrlForChat() {
            const match = window.location.pathname.match(/\/chat\/(.+)/);
            if (match) {
                this.currentChatId = match[1];
                this.loadChat(match[1]);
            }
        },

        async loadChats() {
            try {
                const resp = await fetch(`/api/chats?session_id=${this.sessionId}`);
                this.chats = await resp.json();
            } catch (e) {
                console.error('Failed to load chats:', e);
            }
        },

        async loadProviders() {
            try {
                const resp = await fetch('/api/providers');
                this.providers = await resp.json();
            } catch (e) {
                console.error('Failed to load providers:', e);
            }
        },

        async newChat() {
            try {
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        title: 'New Chat',
                        model: this.model,
                    }),
                });
                const chat = await resp.json();
                this.currentChatId = chat.id;
                this.messages = [];
                this.loadChats();
                window.history.pushState({}, '', `/chat/${chat.id}`);
                this.resetThinking();
            } catch (e) {
                console.error('Failed to create chat:', e);
            }
        },

        async loadChat(chatId) {
            try {
                const resp = await fetch(`/api/chat/${chatId}`);
                const data = await resp.json();
                this.messages = (data.messages || []).map(m => ({
                    ...m,
                    sources: m.sources || [],
                }));
                this.currentChatId = chatId;
                this.resetThinking();
            } catch (e) {
                console.error('Failed to load chat:', e);
            }
        },

        selectChat(chatId) {
            this.currentChatId = chatId;
            this.loadChat(chatId);
            window.history.pushState({}, '', `/chat/${chatId}`);
            if (window.innerWidth <= 768) this.sidebarOpen = false;
        },

        async deleteChat(chatId, e) {
            e.stopPropagation();
            try {
                await fetch(`/api/chat/${chatId}`, { method: 'DELETE' });
                if (this.currentChatId === chatId) {
                    this.currentChatId = null;
                    this.messages = [];
                }
                this.loadChats();
            } catch (e) {
                console.error('Failed to delete chat:', e);
            }
        },

        resetThinking() {
            this.thinkingContent = '';
            this.isThinking = false;
            this.thinkingOpen = true;
            this.thinkingDone = false;
            this.isSearching = false;
        },

        async sendMessage() {
            const text = this.input.trim();
            if (!text || this.streaming) return;

            if (!this.currentChatId) await this.newChat();

            this.input = '';
            this.streaming = true;
            this.resetThinking();

            this.messages = [...this.messages, {
                role: 'user', content: text,
                id: 'msg_' + Math.random().toString(36).slice(2, 14),
            }];

            const msgIdx = this.messages.length;
            this.messages = [...this.messages, {
                role: 'assistant', content: '',
                sources: [],
                id: 'msg_' + Math.random().toString(36).slice(2, 14),
            }];

            this.$nextTick(() => this.scrollToBottom());

            try {
                const resp = await fetch(`/api/chat/${this.currentChatId}/message`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chat_id: this.currentChatId,
                        role: 'user',
                        content: text,
                        stream: true,
                        search: this.searchEnabled,
                        agents: this.agentsEnabled,
                    }),
                });

                if (!resp.ok) throw new Error('Request failed');

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let currentEvent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split('\n');
                    buffer = parts.pop() || '';

                    for (const part of parts) {
                        if (part.startsWith('event: ')) {
                            currentEvent = part.slice(7).trim();
                        } else if (part.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(part.slice(6));
                                this.appendResponse(data, msgIdx, currentEvent);
                            } catch (e) { }
                            currentEvent = '';
                        }
                    }
                }

                if (this.isThinking) {
                    this.isThinking = false;
                    this.thinkingOpen = false;
                }
                this.isSearching = false;

                this.loadChats();
            } catch (e) {
                this.messages = this.messages.map((m, i) =>
                    i === msgIdx ? { ...m, content: 'Error: ' + e.message } : m
                );
            }

            this.streaming = false;
            this.isSearching = false;
            this.$nextTick(() => this.scrollToBottom());
        },

        appendResponse(data, msgIdx, eventType) {
            if (eventType === 'searching') {
                this.isSearching = true;
                this.isThinking = false;
                this.$nextTick(() => this.scrollToBottom());
                return;
            }

            if (eventType === 'sources') {
                this.isSearching = false;
                this.isThinking = false;
                const results = data.results || [];
                this.messages = this.messages.map((m, i) =>
                    i === msgIdx ? { ...m, sources: results } : m
                );
                this.$nextTick(() => this.scrollToBottom());
                return;
            }

            if (eventType === 'thinking') {
                this.isThinking = true;
                this.thinkingContent = '';
                this.thinkingOpen = true;
                this.isSearching = false;
                this.$nextTick(() => this.scrollToBottom());
                return;
            }

            if (eventType === 'reasoning') {
                this.isThinking = true;
                this.thinkingOpen = true;
                const msg = data.message || '';
                if (msg) {
                    this.thinkingContent = this.thinkingContent
                        ? this.thinkingContent + '\n' + msg
                        : msg;
                }
                this.$nextTick(() => this.scrollToBottom());
                return;
            }

            if (data.token) {
                if (this.isThinking) {
                    this.isThinking = false;
                    this.thinkingOpen = false;
                    this.thinkingDone = true;
                }
                this.isSearching = false;

                this.messages = this.messages.map((m, i) =>
                    i === msgIdx ? { ...m, content: m.content + data.token } : m
                );
                this.$nextTick(() => this.scrollToBottom());
                return;
            }

            if (data.content) {
                this.isSearching = false;
                this.messages = this.messages.map((m, i) =>
                    i === msgIdx ? { ...m, content: m.content + data.content } : m
                );
                this.$nextTick(() => this.scrollToBottom());
            }
        },

        scrollToBottom() {
            this.$nextTick(() => {
                const el = this.$refs.chatContainer;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        selectSuggestion(text) {
            this.input = text;
            this.$nextTick(() => this.$el.querySelector('textarea').focus());
        },

        openSources(sources) {
            this.activeSources = sources || [];
            this.showSourcesModal = true;
            document.body.style.overflow = 'hidden';
        },

        closeSources() {
            this.showSourcesModal = false;
            this.activeSources = [];
            document.body.style.overflow = '';
        },

        retryLast() {
            const lastUserIdx = this.messages.map(m => m.role).lastIndexOf('user');
            if (lastUserIdx === -1) return;
            const lastUserMsg = this.messages[lastUserIdx];
            this.messages = this.messages.slice(0, lastUserIdx);
            this.$nextTick(() => {
                this.input = lastUserMsg.content;
                this.sendMessage();
            });
        },

        retryMessage(msgIdx) {
            const msgs = this.messages.slice(0, msgIdx);
            const lastUserIdx = msgs.map(m => m.role).lastIndexOf('user');
            if (lastUserIdx === -1) return;
            const lastUserMsg = msgs[lastUserIdx];
            this.messages = msgs.slice(0, lastUserIdx);
            this.$nextTick(() => {
                this.input = lastUserMsg.content;
                this.sendMessage();
            });
        },

        regenerateLast() {
            const lastUserIdx = this.messages.map(m => m.role).lastIndexOf('user');
            if (lastUserIdx === -1) return;
            const lastUserMsg = this.messages[lastUserIdx];
            this.messages = this.messages.slice(0, lastUserIdx);
            this.$nextTick(() => {
                this.input = lastUserMsg.content;
            });
        },

        toggleLike(msgIdx) {
            this.messages = this.messages.map((m, i) =>
                i === msgIdx ? { ...m, liked: m.liked === true ? null : true, disliked: null } : m
            );
        },

        toggleDislike(msgIdx) {
            this.messages = this.messages.map((m, i) =>
                i === msgIdx ? { ...m, disliked: m.disliked === true ? null : true, liked: null } : m
            );
        },

        getDomain(url) {
            try { return new URL(url).hostname.replace('www.', ''); } catch { return url; }
        },

        formatContent(content) {
            if (!content) return '';

            const codeBlocks = [];
            let idx = 0;
            let html = this.escapeHtml(content);
            html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
                const key = '%%CODEBLOCK' + (idx++) + '%%';
                const escaped = this.escapeHtml(code);
                const langLabel = lang || 'code';
                codeBlocks.push(`<div class="code-block-wrapper">
                    <div class="code-block-header">
                        <span class="code-lang"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>${this.escapeHtml(langLabel)}</span>
                        <button class="copy-btn" type="button"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy</button>
                    </div>
                    <pre><code>${escaped}</code></pre>
                </div>`);
                return key;
            });

            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

            const lines = html.split('\n');
            const out = [];
            let inUl = false, inOl = false;

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                const ulMatch = line.match(/^[-*] (.+)/);
                const olMatch = line.match(/^\d+\. (.+)/);

                if (ulMatch) {
                    if (inOl) { out.push('</ol>'); inOl = false; }
                    if (!inUl) { out.push('<ul>'); inUl = true; }
                    out.push('<li>' + ulMatch[1] + '</li>');
                } else if (olMatch) {
                    if (inUl) { out.push('</ul>'); inUl = false; }
                    if (!inOl) { out.push('<ol>'); inOl = true; }
                    out.push('<li>' + olMatch[1] + '</li>');
                } else {
                    if (inUl) { out.push('</ul>'); inUl = false; }
                    if (inOl) { out.push('</ol>'); inOl = false; }
                    if (line.trim() === '') {
                        out.push('');
                    } else {
                        out.push('<p>' + line + '</p>');
                    }
                }
            }
            if (inUl) out.push('</ul>');
            if (inOl) out.push('</ol>');

            html = out.join('\n');
            html = html.replace(/%%CODEBLOCK(\d+)%%/g, (_, id) => codeBlocks[parseInt(id)] || '');
            return html;
        },

        escapeHtml(text) {
            const d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        },

        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },
    }));
});
