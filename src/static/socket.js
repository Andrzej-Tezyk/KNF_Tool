document.addEventListener('DOMContentLoaded', function() {

    // variables, listeners
    window.socket = io.connect('http://127.0.0.1:5000'); // DO ZMIANY
    const outputDiv = document.getElementById('output');
    const inputText = document.getElementById('input');
    const button = document.getElementById('action-button');
    const img = button.querySelector('img');

    button.addEventListener('click', startProcessingOnButton);
    //inputText.addEventListener('keydown', startProcessingOnEnter);
    document.addEventListener('keydown', handleGlobalEnter);



    
    
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
        //inputText.addEventListener('keydown', startProcessingOnEnter);
        document.addEventListener('keydown', handleGlobalEnter);
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
                // --- Change the icon from loading state to ready state (arrow) ---
                iconSpan.classList.remove('loading-spinner'); // Remove the loading class
                iconSpan.classList.add('arrow-ready'); // Add the ready class
                // Set the text content to the arrow character
                iconSpan.textContent = '➤'; // Make sure the character is there
                // -----------------------------------------------------------------
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
        //inputText.removeEventListener('keydown', startProcessingOnEnter);
        document.removeEventListener('keydown', handleGlobalEnter);

        let input = document.getElementById('input').value;
        let output_size = document.getElementById('words-sentence-select').value;
        let selectedFiles = [];
        document.querySelectorAll('.file-checkbox:checked').forEach((checkbox) => {
            selectedFiles.push(checkbox.value);
        });
        let show_pages_checkbox = document.getElementById('show-pages').checked;
        let choosen_model = document.getElementById('model-select').value;
        let change_length_checkbox = document.getElementById('change_length').checked;
        let slider_value = document.getElementById('myRange').value;
        let ragDocSlider = document.getElementById('rag-doc-slider-checkbox').checked;
        
        // rise a popup if no file selected
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
            ragDocSlider: ragDocSlider });
        
        const img = button.querySelector('img');
        img.src = "/static/images/stop-solid.svg"; // changes icon to stop

        button.addEventListener("click", stopProcessing)

        // delete user mesage
        if (inputText) {
               inputText.value = '';
            }
    }

        // start processing: 1) on key; 2) on button
    // remove arrow-up -> add stop button + functionality
    //function startProcessingOnEnter() {
    //    if (event.key === 'Enter' && !event.shiftKey) {
    //        event.preventDefault(); // prevent going to a new line
    //    
    //        startProcessingOnButton();
    //    }       
    //}

    function handleGlobalEnter(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // prevent going to a new line
            startProcessingOnButton();
        }
    }
});