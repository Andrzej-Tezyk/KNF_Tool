document.addEventListener('DOMContentLoaded', function() {

    // variables, listeners
    const socketUrl = window.location.origin.replace(/^http/, 'ws');
    window.socket = io(socketUrl, {
        reconnectionAttempts: 5,  // Retry up to 5 times
        timeout: 5000,            // 5 seconds timeout
        transports: ['websocket'] // Enforce WebSocket for better performance
    });

    const outputDiv = document.getElementById('output');
    const inputText = document.getElementById('input');
    const button = document.getElementById('action-button');
    const img = button.querySelector('img');

    inputText.addEventListener('input', checkButtonState);

    button.addEventListener('click', startProcessingOnButton);
    document.addEventListener('keydown', handleGlobalEnter);
    checkButtonState();
    
    // socket events
    socket.on('new_container', function(data) {
        outputDiv.insertAdjacentHTML('beforeend', data.html);
    });
    
    socket.on('update_content', function(data) {
        const container = document.getElementById(data.container_id);
        if (container) {
            container.innerHTML = data.html;
        }
    });

    socket.on('stream_stopped', function(data) {
        img.src = "/static/images/arrow-up-solid.svg";
        button.addEventListener("click", startProcessingOnButton);
        document.addEventListener('keydown', handleGlobalEnter);
        checkButtonState();
    });

    // Handler for when processing is complete for a SINGLE container (document)
    // This event carries the container_id for which processing finished
    socket.on('processing_complete_for_container', function(data) {
        const containerId = data.container_id;
        const buttonId = 'chat-button-' + containerId;
        const chatButton = document.getElementById(buttonId);

        if (chatButton) {
            const iconSpan = chatButton.querySelector('.icon'); // Find the span with the 'icon' class inside the button

            if (iconSpan) {
                // Change the icon from loading state to ready state (arrow)
                iconSpan.classList.remove('loading-spinner');
                iconSpan.classList.add('arrow-ready');
                // Set the text content to the arrow character
                iconSpan.textContent = '➤'; // Make sure the character is there
            } else {
                 console.warn('Could not find .icon span inside button with ID:', buttonId);
            }


            chatButton.disabled = false; // Enable the button
            console.log('Chat button enabled for container:', containerId);

        } else {
            console.warn('Could not find chat button with ID:', buttonId, 'to enable after processing complete.');
        }
    });



    function startProcessingOnButton() {
        const button = document.getElementById('action-button');
        
        button.removeEventListener("click", startProcessingOnButton)
        document.removeEventListener('keydown', handleGlobalEnter);

        const DEFAULT_OPTIONS = {
            show_pages_checkbox: false,
            choosen_model: 'gemini-2.0-flash',
            change_length_checkbox: false,
            slider_value: 0.8,
            ragDocSlider: false,
            prompt_enhancer: true
        };

        const input = document.getElementById('input').value;
        const output_size = document.getElementById('words-sentence-select').value;
        const show_pages_checkbox = document.getElementById('show-pages') ? document.getElementById('show-pages').checked : DEFAULT_OPTIONS.show_pages_checkbox;
        const choosen_model = document.getElementById('model-select') ? document.getElementById('model-select').value : DEFAULT_OPTIONS.choosen_model;
        const change_length_checkbox = document.getElementById('change_length') ? document.getElementById('change_length').checked : DEFAULT_OPTIONS.change_length_checkbox;
        const slider_value = document.getElementById('myRange') ? document.getElementById('myRange').value : DEFAULT_OPTIONS.slider_value;
        const ragDocSlider = document.getElementById('rag-doc-slider-checkbox') ? document.getElementById('rag-doc-slider-checkbox').checked : DEFAULT_OPTIONS.ragDocSlider;
        const prompt_enhancer = document.getElementById('prompt-enhancer') ? document.getElementById('prompt-enhancer').checked : DEFAULT_OPTIONS.prompt_enhancer;

        const selectedFiles = [];
        document.querySelectorAll('.file-checkbox:checked').forEach((checkbox) => {
            selectedFiles.push(checkbox.value);
        });
        
        // rise a popup if no file selected; do not put return here!
        if (!selectedFiles.length) {
            alert("Please select at least one file.");
        }

        window.socket.emit('start_processing', { 
            input: input, 
            pdfFiles: selectedFiles, 
            output_size: output_size, 
            show_pages_checkbox: show_pages_checkbox, 
            choosen_model: choosen_model,
            change_length_checkbox: change_length_checkbox,
            slider_value: slider_value,
            ragDocSlider: ragDocSlider,
            prompt_enhancer: prompt_enhancer });
        
        const img = button.querySelector('img');
        img.src = "/static/images/stop-solid.svg"; // changes icon to stop

        button.addEventListener("click", stopProcessing)

        // delete user mesage
        if (inputText) {
               inputText.value = '';
            }

        inputText.dispatchEvent(new Event('input'));
    }

    function handleGlobalEnter(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // prevent going to a new line
            startProcessingOnButton();
        }
    }

    function checkButtonState() {
        const isEmpty = inputText.value.trim() === '';
        const isArrowUpIcon = img && img.src && img.src.includes('arrow-up-solid.svg');

        const shouldDisable = isEmpty && isArrowUpIcon;

        button.disabled = shouldDisable;

        if (shouldDisable) {
            button.classList.add('disabled');
        } else {
            button.classList.remove('disabled');
        }
    }
});