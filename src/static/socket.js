document.addEventListener('DOMContentLoaded', function() {

    // variables, listeners
    window.socket = io.connect('http://127.0.0.1:5000'); // DO ZMIANY
    const outputDiv = document.getElementById('output');
    const inputText = document.getElementById('input');
    const button = document.getElementById('action-button');
    const img = button.querySelector('img');

    button.addEventListener('click', startProcessingOnButton);
    inputText.addEventListener('keydown', startProcessingOnEnter);

    
    
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
        inputText.addEventListener('keydown', startProcessingOnEnter);
    });

    // start processing: 1) on key; 2) on button
    // remove arrow-up -> add stop button + functionality
    function startProcessingOnEnter() {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // prevent going to a new line
        
            startProcessingOnButton();
        }       
    }

    function startProcessingOnButton() {
        const button = document.getElementById('action-button');
        
        button.removeEventListener("click", startProcessingOnButton)
        inputText.removeEventListener('keydown', startProcessingOnEnter);

        let input = document.getElementById('input').value;
        let output_size = document.getElementById('words-sentence-select').value;
        let selectedFiles = [];
        document.querySelectorAll('.file-checkbox:checked').forEach((checkbox) => {
            selectedFiles.push(checkbox.value);
        });
        let show_pages_checkbox = document.getElementById('show-pages').checked;
        let choosen_model = document.getElementById('model-select').value;
        let change_length_checkbox = document.getElementById('change_lebgth').checked;
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
    }
});