console.log("🚀 Cypher script.js loaded - SPOTIFY INTEGRATION ACTIVE");

let chats = {};
let currentChatId = null;
let chatHistory = [];
let webSearchEnabled = false;
let spotifyEnabled = false;
let currentTrack = null;

document.addEventListener('DOMContentLoaded', () => {
    loadChats();
    setupEventListeners();
    createNewChat();
    setupVoiceResponseListener();
    showListeningStatus();
    initSpotifyControls();
});

function loadChats() {
    const savedChats = localStorage.getItem('cypherChats');
    if (savedChats) {
        chats = JSON.parse(savedChats);
        renderChatList();
    }
}

function saveChats() {
    localStorage.setItem('cypherChats', JSON.stringify(chats));
}

function setupEventListeners() {
    document.querySelector('.new-chat-btn').addEventListener('click', createNewChat);
    document.getElementById('jarvisForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('webSearchBtn').addEventListener('click', toggleWebSearch);
    document.getElementById('pdfUploadBtn').addEventListener('click', () => {
        document.getElementById('pdfInput').click();
    });
    document.getElementById('pdfInput').addEventListener('change', handlePdfUpload);
    
    document.getElementById('userInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('jarvisForm').dispatchEvent(new Event('submit'));
        }
    });
}

// Create a new chat
function createNewChat() {
    const chatId = Date.now().toString();
    const timestamp = new Date().toLocaleString();
    
    chats[chatId] = {
        id: chatId,
        title: `Chat ${Object.keys(chats).length + 1}`,
        timestamp: timestamp,
        messages: []
    };
    
    switchToChat(chatId);
    saveChats();
    renderChatList();
}

// Switch to a specific chat
function switchToChat(chatId) {
    if (currentChatId) {
        chats[currentChatId].messages = [...chatHistory];
    }
    
    currentChatId = chatId;
    chatHistory = [...chats[chatId].messages];
    renderChat();
    renderChatList();
}

function renderChatList() {
    const chatListElement = document.getElementById('chatList');
    chatListElement.innerHTML = '';
    
    Object.values(chats).reverse().forEach(chat => {
        const chatElement = document.createElement('div');
        chatElement.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        chatElement.innerHTML = `
            <span>${chat.title}</span>
            <button class="delete-btn" data-id="${chat.id}">
                <i class="fas fa-trash"></i>
            </button>
        `;
        chatElement.addEventListener('click', (e) => {
            if (!e.target.classList.contains('delete-btn') && 
                !e.target.parentElement.classList.contains('delete-btn')) {
                switchToChat(chat.id);
            }
        });
        
        chatElement.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        });
        
        chatListElement.appendChild(chatElement);
    });
}

// Delete a chat
function deleteChat(chatId) {
    if (Object.keys(chats).length <= 1) {
        alert('You must have at least one chat!');
        return;
    }
    
    delete chats[chatId];
    saveChats();
    renderChatList();
    
    if (currentChatId === chatId) {
        const remainingChatId = Object.keys(chats)[0];
        switchToChat(remainingChatId);
    }
}

// Render current chat
function renderChat() {
    const chatDisplay = document.getElementById('chatDisplay');
    chatDisplay.innerHTML = '';
    
    chatHistory.forEach(message => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        messageDiv.innerHTML = `
            <div class="message-avatar">${message.role === 'user' ? 'U' : 'C'}</div>
            <div class="message-content">${marked.parse(message.content)}</div>
        `;
        chatDisplay.appendChild(messageDiv);
    });
    
    Prism.highlightAll();
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
}

// Add system message to chat
function addSystemMessage(message) {
    const chatDisplay = document.getElementById('chatDisplay');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message cypher system';
    msgDiv.innerHTML = `
        <div class="message-avatar">C</div>
        <div class="message-content">${message}</div>
    `;
    chatDisplay.appendChild(msgDiv);
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
}


function initSpotifyControls() {
    console.log("🎵 Initializing Spotify controls...");
    updateCurrentTrack();
    setInterval(updateCurrentTrack, 3000);
}

async function updateCurrentTrack() {
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/current', { method: 'GET' });
        if (res.status === 200) {
            const data = await res.json();
            if (data.track) {
                currentTrack = data;
                console.log(`🎵 Now playing: ${data.track} by ${data.artist}`);
            }
        }
    } catch (e) {
        // Spotify not responding
    }
}

async function spotifyPlay(query) {
    console.log(`🎵 Playing: ${query}`);
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        return data.status === 'playing' ? `Now playing **${data.track}** by ${data.artist} 🎵` : `Error: ${data.error}`;
    } catch (e) {
        return `❌ Couldn't reach Spotify backend`;
    }
}

async function spotifyPause() {
    console.log("⏸️ Pausing Spotify");
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/pause', { method: 'POST' });
        const data = await res.json();
        return "⏸️ Paused";
    } catch (e) {
        return "❌ Pause failed";
    }
}

async function spotifyResume() {
    console.log("▶️ Resuming Spotify");
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/resume', { method: 'POST' });
        const data = await res.json();
        return "▶️ Resumed";
    } catch (e) {
        return "❌ Resume failed";
    }
}

async function spotifyNext() {
    console.log("⏭️ Next track");
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/next', { method: 'POST' });
        const data = await res.json();
        return "⏭️ Skipped to next";
    } catch (e) {
        return "❌ Skip failed";
    }
}

async function spotifyPrevious() {
    console.log("⏮️ Previous track");
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/previous', { method: 'POST' });
        const data = await res.json();
        return "⏮️ Went to previous";
    } catch (e) {
        return "❌ Previous failed";
    }
}

async function spotifyPlaylist(playlistName) {
    console.log(`🎵 Playing playlist: ${playlistName}`);
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/playlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist: playlistName })
        });
        const data = await res.json();
        return data.status === 'playing' ? `Now playing playlist **${data.playlist}** 🎵` : `Error: ${data.error}`;
    } catch (e) {
        return `❌ Couldn't reach Spotify`;
    }
}

async function spotifyVolume(volume) {
    console.log(`🔊 Setting volume to ${volume}`);
    try {
        const res = await fetch('http://127.0.0.1:5000/spotify/volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume: parseInt(volume) })
        });
        const data = await res.json();
        return `🔊 Volume set to ${volume}%`;
    } catch (e) {
        return "❌ Volume control failed";
    }
}

async function getWeather(city) {
    console.log(`🌤️ Getting weather for: ${city}`);
    try {
        const res = await fetch('http://127.0.0.1:5000/weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city })
        });
        const data = await res.json();
        
        if (!res.ok) {
            return `⚠️ ${data.error}`;
        }
        
        return data.weather;
    } catch (e) {
        return `❌ Couldn't reach weather backend`;
    }
}


function showListeningStatus() {
    setInterval(async () => {
        try {
            const res = await fetch('http://127.0.0.1:5000/voice_status', { method: 'GET' });
            const data = await res.json();
            
            const statusIndicator = document.getElementById('listeningIndicator');
            if (statusIndicator) {
                if (data.in_conversation) {
                    statusIndicator.className = 'listening-indicator active';
                    statusIndicator.textContent = '🎤 IN CONVERSATION';
                } else {
                    statusIndicator.className = 'listening-indicator';
                    statusIndicator.textContent = '🎤 LISTENING...';
                }
            }
        } catch (e) {
            // Backend not responding
        }
    }, 1000);
}

function setupVoiceResponseListener() {
    setInterval(async () => {
        try {
            const res = await fetch('http://127.0.0.1:5000/get_voice_response', { method: 'GET' });
            
            if (res.status === 200) {
                const data = await res.json();
                
                if (data.user && data.response) {
                    console.log("🎤 Voice response received:", data);
                    
                    const userMsg = { role: 'user', content: data.user };
                    chatHistory.push(userMsg);
                    
                    const aiMsg = { role: 'assistant', content: data.response };
                    chatHistory.push(aiMsg);
                    
                    chats[currentChatId].messages = [...chatHistory];
                    renderChat();
                    saveChats();
                }
            }
        } catch (e) {
        }
    }, 500);
}


async function performWebSearch(query) {
    try {
        const res = await fetch('http://127.0.0.1:5000/web_search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            return `⚠️ Search failed: ${data.error}. Check your Serper API key!`;
        }
        
        let results = "🔍 **Web Search Results:**\n\n";
        
        if (data.results && data.results.length > 0) {
            data.results.forEach((result, idx) => {
                const title = result.title || 'No title';
                const content = result.content || 'No description';
                const url = result.url || '#';
                
                results += `**${idx + 1}. ${title}**\n`;
                results += `${content}\n`;
                if (url !== '#') {
                    results += `[Link](${url})\n`;
                }
                results += `\n`;
            });
        } else {
            results += `⚠️ No results found for "${query}". Try rephrasing!`;
        }
        
        return results;
    } catch (err) {
        console.error("Web search error:", err);
        return `⚠️ Couldn't reach backend on port 5000. Is it running?`;
    }
}

function toggleWebSearch() {
    webSearchEnabled = !webSearchEnabled;
    const btn = document.getElementById('webSearchBtn');
    btn.classList.toggle('active');
    btn.title = webSearchEnabled ? 'Web search: ON' : 'Web search: OFF';
}


async function handleFormSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('userInput').value.trim();
    
    if (!input) {
        document.getElementById('userInput').focus();
        return;
    }

    const userMessage = { role: 'user', content: input };
    chatHistory.push(userMessage);
    chats[currentChatId].messages = [...chatHistory];
    
    document.getElementById('userInput').value = '';
    renderChat();
    
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message cypher thinking';
    thinkingDiv.innerHTML = `
        <div class="message-avatar">C</div>
        <div class="message-content">Cypher is thinking...</div>
    `;
    document.getElementById('chatDisplay').appendChild(thinkingDiv);
    document.getElementById('chatDisplay').scrollTop = document.getElementById('chatDisplay').scrollHeight;

    let aiResponse = "";

    try {
        const userLower = input.toLowerCase();

        if (userLower.includes('play') && userLower.includes('spotify')) {
            const query = input.replace(/play|spotify/gi, '').trim();
            aiResponse = await spotifyPlay(query);
        }
        else if (userLower.includes('pause') && (userLower.includes('spotify') || userLower.includes('music'))) {
            aiResponse = await spotifyPause();
        }
        else if ((userLower.includes('resume') || userLower.includes('unpause')) && (userLower.includes('spotify') || userLower.includes('music'))) {
            aiResponse = await spotifyResume();
        }
        else if ((userLower.includes('next') || userLower.includes('skip')) && (userLower.includes('spotify') || userLower.includes('song') || userLower.includes('track'))) {
            aiResponse = await spotifyNext();
        }
        else if ((userLower.includes('previous') || userLower.includes('back')) && (userLower.includes('song') || userLower.includes('track'))) {
            aiResponse = await spotifyPrevious();
        }
        else if (userLower.includes('playlist') && userLower.includes('play')) {
            const playlistName = input.replace(/playlist|play/gi, '').trim();
            aiResponse = await spotifyPlaylist(playlistName);
        }
        else if (userLower.includes('volume')) {
            const volumeMatch = input.match(/(\d+)/);
            const volume = volumeMatch ? volumeMatch[1] : 50;
            aiResponse = await spotifyVolume(volume);
        }
        else if ((["open", "launch", "run"].some(word => userLower.includes(word))) && userLower.includes("spotify")) {
            await fetch('http://127.0.0.1:5000/exec', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: userLower })
            });
            aiResponse = "✅ Spotify launched, Boss.";
        }

        //weather
        else if (userLower.includes('weather') || userLower.includes('temperature')) {
            const cityMatch = input.match(/in\s+([a-zA-Z\s]+)/i) || input.match(/for\s+([a-zA-Z\s]+)/i);
            const city = cityMatch ? cityMatch[1].trim() : 'Sarajevo';
            aiResponse = await getWeather(city);
        }

        else if (webSearchEnabled) {
            thinkingDiv.querySelector('.message-content').textContent = "Searching the web... 🔍";
            const searchResults = await performWebSearch(input);
            aiResponse = searchResults;
        }

        else if ((["open", "launch", "run"].some(word => userLower.includes(word))) && 
            (["discord", "youtube", "google", "steam", "roblox", "code", "calculator", "notepad"].some(app => userLower.includes(app)))) {
            await fetch('http://127.0.0.1:5000/exec', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: userLower })
            });
            aiResponse = "✅ Command executed, Boss.";
        }

        else {
            try {
                const res = await fetch('http://127.0.0.1:8080/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        model: 'cypher', 
                        messages: chatHistory, 
                        stream: false,
                        options: {
                            temperature: 0.7,
                            repeat_penalty: 1.1,
                            top_p: 0.9,
                            top_k: 40
                        }
                    })
                });
                const data = await res.json();
                aiResponse = data.message?.content || "No response received.";
            } catch {
                aiResponse = "⚠️ Ollama is offline. Check if it's running on port 8080!";
            }
        }

        document.getElementById('chatDisplay').removeChild(thinkingDiv);
        const aiMessage = { role: 'assistant', content: aiResponse };
        chatHistory.push(aiMessage);
        chats[currentChatId].messages = [...chatHistory];
        
        renderChat();
        saveChats();
    } catch (err) {
        thinkingDiv.querySelector('.message-content').textContent = "Something went wrong. Check the backend!";
        console.error(err);
    }
}

async function handlePdfUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message cypher thinking';
    thinkingDiv.innerHTML = `
        <div class="message-avatar">C</div>
        <div class="message-content">Reading PDF... analyzing with mBart...</div>
    `;
    document.getElementById('chatDisplay').appendChild(thinkingDiv);
    document.getElementById('chatDisplay').scrollTop = document.getElementById('chatDisplay').scrollHeight;

    try {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('http://127.0.0.1:5000/summarize_pdf', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        
        document.getElementById('chatDisplay').removeChild(thinkingDiv);
        
        if (!res.ok) {
            const errorMsg = { role: 'assistant', content: `❌ Error: ${data.error}` };
            chatHistory.push(errorMsg);
        } else {
            const summaryMsg = { role: 'assistant', content: `📄 **PDF Summary:**\n\n${data.summary}` };
            chatHistory.push(summaryMsg);
        }
        
        chats[currentChatId].messages = [...chatHistory];
        renderChat();
        saveChats();

    } catch (err) {
        console.error("PDF upload failed", err);
        thinkingDiv.querySelector('.message-content').textContent = "❌ PDF upload failed. Check if backend is running.";
    }

    document.getElementById('pdfInput').value = '';
}