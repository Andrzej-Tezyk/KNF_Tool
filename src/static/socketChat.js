import { initSocketManager, socket } from './socketManager.js';

// Helper function to get form data (similar to the one in socket.js)
function getChatFormData() {
    const getElementValue = (id, property = 'value') => document.getElementById(id)?.[property];
    const isChecked = (id) => getElementValue(id, 'checked') ?? false;
    const contentId = document.getElementById('output')?.dataset.contentId;

    return {
        input: getElementValue('input') || '',
        contentId: contentId,
        output_size: getElementValue('words-sentence-select') || 'medium',
        show_pages_checkbox: isChecked('show-pages'),
        choosen_model: getElementValue('model-select') || 'gemini-2.0-flash',
        change_length_checkbox: isChecked('change_length'),
        slider_value: getElementValue('myRange') || 0.8,
        ragDocSlider: isChecked('rag-doc-slider-checkbox'),
        prompt_enhancer: isChecked('prompt-enhancer')
    };
}

/**
 * Gathers all form data from the chat page DOM.
 */
document.addEventListener('DOMContentLoaded', function() {
    const outputDiv = document.getElementById('output');
    let currentAIMessageDiv = null;

    // Define the page-specific "send" function
    function sendChatMessage() {
        const formData = getChatFormData();

        if (!formData.input || !formData.contentId) {
            console.warn("Cannot send message: Input is empty or ContentID is missing.");
            return false;
        }

        const userMessageElement = displayMessage('You', formData.input, true);

        if (userMessageElement) {
            userMessageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        createSpinnerPlaceholder();
        socket.emit('send_chat_message', formData);
        document.getElementById('input').value = '';
        document.getElementById('input').dispatchEvent(new Event('input'));

        return true;
    }

    // Helper to render a complete message (user or non-streamed error)
    function displayInitialSummary(title, content) {
        const summaryWrapper = document.createElement('div');
        summaryWrapper.className = 'output-content';
        summaryWrapper.id = 'retrieved-content-section';

        const header = document.createElement('div');
        header.className = 'output-header';
        header.textContent = title;

        const body = document.createElement('div');
        body.className = 'markdown-body';
        body.innerHTML = marked.parse(content);

        summaryWrapper.append(header, body);
        outputDiv.appendChild(summaryWrapper);
    }
    function displayMessage(sender, message, isUser) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `output-content ${isUser ? 'user-message' : 'ai-message'}`;
        const header = document.createElement('div');
        header.className = 'output-header';
        header.textContent = sender;
        const body = document.createElement('div');
        body.className = 'markdown-body';
        body.dataset.rawMarkdown = message;
        body.innerHTML = marked.parse(message);
        messageWrapper.append(header, body);
        outputDiv.appendChild(messageWrapper);
        return messageWrapper;
    }

    function createSpinnerPlaceholder() {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'output-content ai-message';
        messageWrapper.id = 'ai-message-streaming'; // Temporary ID to find it later
        
        const header = document.createElement('div');
        header.className = 'output-header';
        header.textContent = 'AI';

        const spinnerDiv = document.createElement('div');
        spinnerDiv.className = 'icon loading-spinner';
        header.appendChild(spinnerDiv);

        const body = document.createElement('div');
        body.className = 'markdown-body';
        messageWrapper.append(header, body);
        outputDiv.appendChild(messageWrapper);
        messageWrapper.scrollIntoView({ behavior: 'smooth', block: 'end' });
        currentAIMessageDiv = body;
    }

    function autoscroll() {
    const outputDiv = document.getElementById('output');
    if (!outputDiv) return;

    // A threshold in pixels. If the user is within this distance from the bottom, we scroll.
    const scrollThreshold = 100; 

    // Calculate the user's distance from the bottom
    const distanceFromBottom = outputDiv.scrollHeight - outputDiv.scrollTop - outputDiv.clientHeight;

    // If the user is close to the bottom, scroll them down smoothly.
    if (distanceFromBottom <= scrollThreshold) {
        outputDiv.scrollTo({
            top: outputDiv.scrollHeight,
            behavior: 'smooth'
        });
    }
}

    // Define page-specific socket event handlers
    const eventHandlers = {
        'chat_history_loaded': (data) => {
            outputDiv.innerHTML = '';
            
            if (data.chat_history && data.chat_history.length >= 2) {
                const title = data.title;
                const initialAIResponseContent = data.chat_history[1].parts[0];
                displayInitialSummary(title, initialAIResponseContent);
            }

            const remainingHistory = data.chat_history.slice(2);
            for (const message of remainingHistory) {
                const role = message.role;
                const content = message.parts[0];
                const isUser = role === 'user';
                const sender = isUser ? 'You' : 'AI';
                displayMessage(sender, content, isUser);
            }

            const allUserMessages = document.querySelectorAll('.user-message');
            if (allUserMessages.length > 0) {
                const lastUserMessage = allUserMessages[allUserMessages.length - 1];
                lastUserMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        },
        'receive_chat_message': (data) => {
            if (currentAIMessageDiv) {
                if (typeof currentAIMessageDiv.dataset.rawMarkdown === 'undefined') {
                    currentAIMessageDiv.dataset.rawMarkdown = '';
                }
                currentAIMessageDiv.dataset.rawMarkdown += data.message;
                currentAIMessageDiv.innerHTML = marked.parse(currentAIMessageDiv.dataset.rawMarkdown);
                autoscroll(); 
            }
        },
        'stream_stopped': () => {
            const streamingMessage = document.getElementById('ai-message-streaming');
            if (streamingMessage) {
                const spinner = streamingMessage.querySelector('.loading-spinner');
                if (spinner) {
                    spinner.remove();
                }
                streamingMessage.id = '';
            }
            currentAIMessageDiv = null;
        }
    };

    // Initialize the socket manager
    initSocketManager({
        sendHandler: sendChatMessage,
        eventHandlers: eventHandlers
    });
    const finalOutputDiv = document.getElementById('output');
    const contentId = finalOutputDiv ? finalOutputDiv.dataset.contentId : null;

    if (contentId) {
        socket.emit('load_chat_history', { contentId: contentId });
    } else {
        console.error("CRITICAL ERROR: Could not find the contentId on the page.");
    }

    const allUserMessages = document.querySelectorAll('.user-message');
    if (allUserMessages.length > 0) {
        const lastUserMessage = allUserMessages[allUserMessages.length - 1];
        lastUserMessage.scrollIntoView({ behavior: 'smooth', block: 'end'});
    }
});