document.addEventListener('DOMContentLoaded', function() {

    console.log("DOM fully loaded and parsed. socketChat.js running."); 

    // variables, listeners
    const socket = io.connect('http://127.0.0.1:5000');
    console.log("Socket connection initiated.");

    const outputDiv = document.getElementById('output');
    const inputText = document.getElementById('input');
    const actionButton = document.getElementById('action-button');
    const img = actionButton ? actionButton.querySelector('img') : null;

    inputText.addEventListener('input', checkButtonState);
    checkButtonState();

    console.log("Elements obtained: outputDiv:", outputDiv, "inputText:", inputText, "actionButton:", actionButton); 

    const contentId = outputDiv ? outputDiv.dataset.contentId : null;
    console.log("Content ID:", contentId); 

    // Content div holder of the current AI message streamed into
    let currentAIMessageContentDiv = null;
    // Holder for RAW text chunks as they arrive
    let rawAIMessageText = '';

    // Function to create and display a message (either user or error that are not streamed)
    function displayMessage(sender, message, isUser) {
        console.log(`Attempting to display message from ${sender}`); 
        if (!outputDiv) {
            console.error("Output div not found in displayMessage.");
            return;
        }
        const messageElement = document.createElement('div');
        messageElement.classList.add('output-content');
        if (isUser) {
            messageElement.classList.add('user-message');
        } else {
            messageElement.classList.add('ai-message');
        }
        
        const headerElement = document.createElement('div');
        headerElement.classList.add('output-header');
        headerElement.textContent = sender;

        const formattedMessageContent = document.createElement('div');
        formattedMessageContent.classList.add('markdown-body');
        try {
            // Ensure 'marked' is available from the script include
            if (typeof marked.parse === 'function') {
                formattedMessageContent.innerHTML = marked.parse(message);
            } else {
                console.error("Marked.js not loaded correctly.");
                formattedMessageContent.textContent = message; 
            }
       } catch (e) {
            console.error("Error rendering markdown for complete message:", e);
            formattedMessageContent.textContent = message; 
       }

        messageElement.appendChild(headerElement);
        messageElement.appendChild(formattedMessageContent);

        outputDiv.appendChild(messageElement);
        outputDiv.scrollTop = outputDiv.scrollHeight;
        console.log("Message displayed and scrolled."); 
    }

    // Function to handle sending messages
    function sendMessage() {
        console.log("sendMessage function called.");
        const input = inputText ? inputText.value.trim() : '';
        console.log("Message obtained from input:", input); 

        const DEFAULT_OPTIONS = {
            output_size: "medium",
            show_pages_checkbox: false,
            choosen_model: 'gemini-2.0-flash',
            change_length_checkbox: false,
            slider_value: 0.8
        };

        // Get advanced options data
        const output_size = document.getElementById('words-sentence-select') ? document.getElementById('words-sentence-select').value : DEFAULT_OPTIONS.output_size;
        const show_pages_checkbox = document.getElementById('show-pages') ? document.getElementById('show-pages').checked : DEFAULT_OPTIONS.show_pages_checkbox;
        const choosen_model = document.getElementById('model-select') ? document.getElementById('model-select').value : DEFAULT_OPTIONS.choosen_model;
        const change_length_checkbox = document.getElementById('change_length') ? document.getElementById('change_length').checked : DEFAULT_OPTIONS.change_length_checkbox;
        const slider_value = document.getElementById('myRange') ? document.getElementById('myRange').value : DEFAULT_OPTIONS.slider_value;

        if (input && contentId) { 
            console.log("Message and ContentId are valid. Proceeding to display and emit."); 

            // Immediately display the user's message on the frontend
            displayMessage('You', input, true); 

            // Emit the message to the backend with the document contentId
            socket.emit('send_chat_message', {
                input: input,
                contentId: contentId,
                output_size: output_size, 
                show_pages_checkbox: show_pages_checkbox, 
                choosen_model: choosen_model,
                change_length_checkbox: change_length_checkbox,
                slider_value: slider_value
            });
            console.log("Emitted 'send_chat_message'."); 

            // Clear the input field after sending
            if (inputText) {
               inputText.value = '';
               inputText.dispatchEvent(new Event('input'));
            }
            if (actionButton) {
                console.log("sendMessage: Removing sendMessage listener, adding stopProcessing listener."); 
                actionButton.removeEventListener('click', sendMessage); 
                actionButton.addEventListener('click', stopProcessing); 
                console.log("sendMessage: Listener swapped to stopProcessing."); 
            }
            if (img) {
                 console.log("Changing icon to stop.");
                 img.src = stopIconUrl; // Use the variable from documentChat.html
                 checkButtonState();
            }
           rawAIMessageText = ''; // Ensure this is clear for the new stream
           currentAIMessageContentDiv = null; // Ensure this is null for the new stream

        } else {
            console.log("sendMessage condition not met. message:", message, "contentId:", contentId);
             if (!input) {
                 console.log("Reason: message is empty.");
             }
             if (!contentId) {
                 console.log("Reason: contentId is missing.");
             }
        }

        checkButtonState();

    }
        // --- Function to handle stopping processing ---
        // Simmilar function in stopProcessing.js file due to DOM scopes.
        // Need to change implementation in refactor.
        function stopProcessing() {
            socket.emit('stop_processing');
            checkButtonState();
        }

    // --- Event Listeners (for sending messages) ---
    if (actionButton) {
        console.log("Attaching click listener to actionButton.");
        actionButton.addEventListener('click', sendMessage);
        checkButtonState();
    } else {
        console.error("Send button (#action-button) not found. Cannot attach click listener."); // Added log
    }


    if (inputText) {
        console.log("Attaching keypress listener to inputText.");
        document.addEventListener('keypress', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                console.log("Enter key pressed.");
                event.preventDefault();
                // Check if the button currently triggers sendMessage before calling
                // This prevents sending a new message while processing is ongoing (button is stop)
                // A simpler check is if the button is NOT disabled and shows the arrow icon
                if (actionButton && img && img.src.includes(arrowUpIconUrl)) {
                     console.log("Keypress: Calling sendMessage."); 
                     sendMessage();
                } else {
                     console.log("Keypress: Button not in send state or disabled. Not calling sendMessage.");
                }
            }
        });
    } else {
         console.error("Input textarea (#input) not found. Cannot attach keypress listener.");
    }


    // --- Socket.IO Event Listeners (for receiving messages) ---
    socket.on('receive_chat_message', function(data) {
        console.log("Received 'receive_chat_message'. Data:", data);

        if (data.message !== undefined && data.message !== null) {
            const chunkText = data.message;
            console.log("Processing message chunk. Chunk text:", chunkText);

            console.log("Before if/else: currentAIMessageContentDiv is", currentAIMessageContentDiv ? "set" : "null");


            if (!currentAIMessageContentDiv) {
                // This is the FIRST chunk of a new AI message

                console.log("First AI chunk received. Creating new message element.");
                const messageElement = document.createElement('div');
                messageElement.classList.add('output-content', 'ai-message');

                const headerElement = document.createElement('div');
                headerElement.classList.add('output-header');
                headerElement.textContent = 'AI';

                const contentDiv = document.createElement('div');
                contentDiv.classList.add('markdown-body'); // Use markdown-body for styling

                messageElement.appendChild(headerElement);
                messageElement.appendChild(contentDiv); // Append content div to message element
                outputDiv.appendChild(messageElement); // Append the main message element to output area

                // Store reference to the content div for appending subsequent chunks
                currentAIMessageContentDiv = contentDiv;

                // Initialize raw text for this new message
                rawAIMessageText = chunkText;
                console.log("Initialized rawAIMessageText:", rawAIMessageText);

            } else {
                // Subsequent chunk of the current AI message - append to the raw text acumulator
                console.log("Subsequent AI chunk processing. Appending to raw text.");
                rawAIMessageText += chunkText; // Append the chunk to the accumulated text
                console.log("Appended chunk. Current rawAIMessageText length:", rawAIMessageText.length);
            }

            // --- Re-render the entire accumulated text with each chunk ---
            if (currentAIMessageContentDiv) {
                console.log("Re-rendering markdown for accumulated text.");
                console.log("Raw text BEFORE rendering (length:", rawAIMessageText.length, "):", rawAIMessageText);                
                try {
                    if (typeof marked.parse === 'function') {
                       const renderedHTML = marked.parse(rawAIMessageText);
                       currentAIMessageContentDiv.innerHTML = renderedHTML; // Update the DOM
                       console.log("innerHTML updated.");
                    } else {
                        console.error("Marked.js not loaded correctly. Cannot render markdown.");
                        // Fallback to showing raw text
                        currentAIMessageContentDiv.textContent = rawAIMessageText;
                    }


                } catch (e) {
                    console.error("Error during markdown rendering:", e);
                    // Fallback: if rendering fails, show the raw text
                    currentAIMessageContentDiv.textContent = rawAIMessageText;
                }

                // Always scroll to the bottom after appending/rendering
                outputDiv.scrollTop = outputDiv.scrollHeight;
                console.log("Scrolled to bottom.");
            } else {
                console.error("Re-rendering block skipped because currentAIMessageContentDiv is null.");
            }
             console.log("--- Finished processing receive_chat_message chunk ---");

        } else if (data.error) {
            // --- Handle Error Messages from Backend ---
            console.error("Error from backend:", data.error);
            displayMessage('System Error', data.error, false);

            // Reset state variables as the stream is likely stopped due to error
            rawAIMessageText = '';
            currentAIMessageContentDiv = null;
            console.log("Error received, stream state reset.");
            console.log("--- Finished processing receive_chat_message chunk ---");
        }
    });

    socket.on('stream_stopped', function(data) {
        console.log("Received 'stream_stopped'.");

        if (actionButton) {
            console.log("stream_stopped: Removing stopProcessing listener, adding sendMessage listener.");
            actionButton.removeEventListener('click', stopProcessing); // Remove stop listener
            actionButton.addEventListener('click', sendMessage); // Add send listener back
            console.log("stream_stopped: Listener swapped back to sendMessage. Button re-enabled.");
        }
        if (img) {
            console.log("Changing icon back to arrow.");
            img.src = arrowUpIconUrl;
        }

        checkButtonState();

        // Reset state variables
        rawAIMessageText = ''; // Should be empty if processing finished correctly
        currentAIMessageContentDiv = null; // Should be null if processing finished correctly

        console.log("Input and button re-enabled. Icon changed to arrow. Listener swapped back to send. Stream state reset.");
        console.log("--- Finished processing stream_stopped ---");
    });

    function checkButtonState() {
        const isEmpty = inputText.value.trim() === '';
        const isArrowUpIcon = img && img.src.includes('arrow-up-solid.svg');

        const shouldDisable = isEmpty && isArrowUpIcon;

        actionButton.disabled = shouldDisable;

        if (shouldDisable) {
            actionButton.classList.add('disabled');
        } else {
            actionButton.classList.remove('disabled');
        }
    }

    // Add general socket event listeners for debugging
    socket.on('connect', () => console.log('Socket connected.'));
    socket.on('disconnect', () => console.log('Socket disconnected.'));
    socket.on('error', (err) => console.error('Socket error:', err));
   
   
});