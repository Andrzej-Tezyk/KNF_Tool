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
    let rawAIMessageText = '';

    // Define the page-specific "send" function
    function sendChatMessage() {
        const formData = getChatFormData();

        if (!formData.input || !formData.contentId) {
            console.error("Cannot send message: Input or ContentID is missing.");
            socket.emit('stream_stopped'); // Reset UI
            return;
        }

        // Display user's message immediately for better UX
        displayMessage('You', formData.input, true);

        socket.emit('send_chat_message', formData);

        // Clear input after sending
        document.getElementById('input').value = '';
        document.getElementById('input').dispatchEvent(new Event('input'));
    }

    // Helper to render a complete message (user or non-streamed error)
    function displayMessage(sender, message, isUser) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `output-content ${isUser ? 'user-message' : 'ai-message'}`;
        const header = document.createElement('div');
        header.className = 'output-header';
        header.textContent = sender;
        const body = document.createElement('div');
        body.className = 'markdown-body';
        body.innerHTML = marked.parse(message); // Using marked.js library
        messageWrapper.append(header, body);
        outputDiv.appendChild(messageWrapper);
        outputDiv.scrollTop = outputDiv.scrollHeight;
    }

    // Define page-specific socket event handlers
    const eventHandlers = {
        'receive_chat_message': (data) => {
            // This is the start of a new AI message stream
            if (!currentAIMessageDiv) {
                rawAIMessageText = '';
                const messageWrapper = document.createElement('div');
                messageWrapper.className = 'output-content ai-message';
                const header = document.createElement('div');
                header.className = 'output-header';
                header.textContent = 'AI';
                currentAIMessageDiv = document.createElement('div');
                currentAIMessageDiv.className = 'markdown-body';
                messageWrapper.append(header, currentAIMessageDiv);
                outputDiv.appendChild(messageWrapper);
            }

            // Append chunk and re-render markdown
            rawAIMessageText += data.message;
            currentAIMessageDiv.innerHTML = marked.parse(rawAIMessageText);
            outputDiv.scrollTop = outputDiv.scrollHeight;
        },
        'stream_stopped': () => {
            currentAIMessageDiv = null;
            rawAIMessageText = '';
        }
    };
    

    // Initialize the socket manager
    initSocketManager({
        sendHandler: sendChatMessage,
        eventHandlers: eventHandlers
    });
});