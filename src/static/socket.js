import { initSocketManager, socket, createOutputContainer } from './socketManager.js';

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
    let activeContainerId = null;

    // Define the page-specific "send" function
    function startProcessing() {
        const formData = getFormData();
        
        if (formData.pdfFiles.length === 0) {
            alert("Please select at least one file.");
            return false;
        }

        socket.emit('start_processing', formData);

        // Clear input after sending
        document.getElementById('input').value = '';
        document.getElementById('input').dispatchEvent(new Event('input'));

        return true;
    }

    // Define page-specific socket event handlers1
    const eventHandlers = {
        'new_container': (data) => {
            const newContainerElement = createOutputContainer(data);
            outputDiv.appendChild(newContainerElement);
            activeContainerId = data.id;
        },
        'update_content': (data) => {
            const containerBody = document.getElementById(data.container_id);
            if (containerBody) {
                if (typeof containerBody.dataset.rawMarkdown === 'undefined') {
                    containerBody.dataset.rawMarkdown = '';
                }
                containerBody.dataset.rawMarkdown += data.chunk;
                containerBody.innerHTML = marked.parse(containerBody.dataset.rawMarkdown);
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
            }
            if (activeContainerId === containerId) {
                activeContainerId = null;
            }
        },
        'stream_stopped': () => {
            if (activeContainerId) {
                const buttonId = `chat-button-${activeContainerId}`;
                const chatButton = document.getElementById(buttonId);
                if (chatButton) {
                    const iconSpan = chatButton.querySelector('.icon');
                    if (iconSpan) {
                        iconSpan.classList.remove('loading-spinner');
                        iconSpan.classList.add('arrow-disabled');
                        iconSpan.textContent = '➤';
                    }
                }
                activeContainerId = null;
            }
        }
    };

    // Initialize the socket manager with our specific configurations
    initSocketManager({
        sendHandler: startProcessing,
        eventHandlers: eventHandlers
    });
});