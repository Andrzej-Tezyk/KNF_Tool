import { initSocketManager, socket } from './socketManager.js';

function getFormData() {
    const getElementValue = (id, property = 'value') => document.getElementById(id)?.[property];
    const isChecked = (id) => getElementValue(id, 'checked') ?? false;

    return {
        input: getElementValue('input') || '',
        output_size: getElementValue('words-sentence-select') || 'medium',
        show_pages_checkbox: isChecked('show-pages'),
        choosen_model: getElementValue('model-select') || 'gemini-2.0-flash',
        change_length_checkbox: isChecked('change_length'),
        slider_value: getElementValue('myRange') || 0.8,
        ragDocSlider: isChecked('rag-doc-slider-checkbox'),
        prompt_enhancer: isChecked('prompt-enhancer'),
        pdfFiles: Array.from(document.querySelectorAll('.file-checkbox:checked')).map(cb => cb.value)
    };
}

/**
 * Gathers all form data from the chat page DOM.
 */
document.addEventListener('DOMContentLoaded', function() {
    const outputDiv = document.getElementById('output'); 

    // Define the page-specific "send" function
    function startProcessing() {
        const formData = getFormData();
        
        if (formData.pdfFiles.length === 0) {
            alert("Please select at least one file.");
            socket.emit('stream_stopped'); 
            return;
        }

        socket.emit('start_processing', formData);

        // Clear input after sending
        document.getElementById('input').value = '';
        document.getElementById('input').dispatchEvent(new Event('input'));
    }

    // Define page-specific socket event handlers
    const eventHandlers = {
        'new_container': function(data) {
            outputDiv.insertAdjacentHTML('beforeend', data.html);
        },
        'update_content': function(data) {
            const container = document.getElementById(data.container_id);
            if (container) {
                container.innerHTML = data.html;
            }
        },
        'processing_complete_for_container': function(data) {
            const containerId = data.container_id;
            const buttonId = 'chat-button-' + containerId;
            const chatButton = document.getElementById(buttonId);

            if (chatButton) {
                const iconSpan = chatButton.querySelector('.icon');
                if (iconSpan) {
                    iconSpan.classList.remove('loading-spinner');
                    iconSpan.classList.add('arrow-ready');
                    iconSpan.textContent = '➤';
                }
                chatButton.disabled = false;
                console.log('Chat button enabled for container:', containerId);
            } else {
                console.warn('Could not find chat button with ID:', buttonId);
            }
        }
    };

    // Initialize the socket manager with our specific configurations
    initSocketManager({
        sendHandler: startProcessing,
        eventHandlers: eventHandlers
    });
});