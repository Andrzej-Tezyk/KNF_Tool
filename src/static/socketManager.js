// --- Global variables for the module ---
export let socket;
let actionButton;
let inputText;
let buttonIcon;
let sendFunction; 

// --- Rendering functions for output containers ---
/**
 * Navigates the user to the chat view for a specific container.
 * @param {string} containerId - The unique ID of the conversation.
 */
function openChatView(containerId) {
    const url = `/documentChat?contentId=${containerId}`;
    console.log("Navigating to chat view for container ID:", containerId, "URL:", url);
    window.open(url, '_blank');
}

/**
 * Creates and returns a complete HTML element for an output container.
 * This is our reusable JavaScript template function.
 * @param {object} data - The data for the container.
 * @param {string} data.id - The unique ID for the container.
 * @param {string} data.title - The title to display in the header.
 * @returns {HTMLElement} The constructed container element.
 */
export function createOutputContainer({ id, title }) {
    console.log("Creating output container with ID:", id, "and title:", title);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = `
        <div class="output-content">
            <div class="output-header">
                ${title}
                <button class="output-button" id="chat-button-${id}" disabled>
                    <span class="icon loading-spinner"></span>
                </button>
            </div>
            <div class="markdown-body" id="${id}"></div>
            <div class="copy-edit-contener" id="under_chat_buttons-${id}">
                <button class="button-round"> 
                    <img class="output-icon" src="/static/images/copy-regular.svg">
                </button>
                <button class="button-round"> 
                    <img class="output-icon" src="/static/images/download-solid.svg">
                </button>
                <button type="button" class="button-round" data-tooltip="Edit"> 
                    <img class="output-icon" src="/static/images/pen-to-square-regular.svg">
                </button>
            </div>
        </div>`;

    const newContainer = tempDiv.firstElementChild;
    newContainer.querySelector(`#chat-button-${id}`).addEventListener('click', () => openChatView(id));

    return newContainer;
}

// --- Core Functions ---

/**
 * Initializes the SocketManager with page-specific configurations.
 * @param {object} config - The configuration object.
 * @param {function} config.sendHandler - The function to execute when the action button is clicked.
 * @param {object} config.eventHandlers - An object mapping socket event names to handler functions.
 */
export function initSocketManager(config) {
    sendFunction = config.sendHandler;
    
    // Establish Socket.IO connection
    const socketUrl = window.location.origin.replace(/^http/, 'ws');
    socket = io(socketUrl, {
        reconnectionAttempts: 5,
        timeout: 5000,
        transports: ['websocket']
    });

    // Get common DOM elements
    actionButton = document.getElementById('action-button');
    inputText = document.getElementById('input');
    buttonIcon = actionButton.querySelector('img');

    if (!actionButton || !inputText || !buttonIcon) {
        console.error("SocketManager Error: A required UI element (action-button, input, or its icon) is missing.");
        return;
    }

    // Register common event listeners
    inputText.addEventListener('input', checkButtonState);
    actionButton.addEventListener('click', handleSend);
    document.addEventListener('keydown', handleGlobalEnter);
    
    // Register common socket event handlers
    socket.on('stream_stopped', handleStreamStopped);
    socket.on('connect', () => console.log('Socket connected successfully.'));
    socket.on('disconnect', () => console.log('Socket disconnected.'));
    socket.on('error', (err) => console.error('Socket error:', err.message || err));


    // Register page-specific socket event handlers passed in config
    for (const eventName in config.eventHandlers) {
        socket.on(eventName, config.eventHandlers[eventName]);
    }
    
    // Set the initial state of the button
    checkButtonState();
    console.log("SocketManager initialized successfully.");
}

/**
 * Toggles the button's disabled state based on input text.
 */
function checkButtonState() {
    if (!actionButton || !inputText || !buttonIcon) return;
    const isEmpty = inputText.value.trim() === '';
    const isSendMode = buttonIcon.src.includes('arrow-up-solid.svg');
    const shouldDisable = isEmpty && isSendMode;
    
    actionButton.disabled = shouldDisable;
    actionButton.classList.toggle('disabled', shouldDisable);
}

/**
 * Emits a request to stop the ongoing stream.
 */
function stopProcessing() {
    console.log("Client requesting to stop processing.");
    socket.emit('stop_processing');
}

// --- Event Handlers ---

/**
 * The primary handler for the action button click.
 * It calls the page-specific send function.
 */
function handleSend() {
    if (sendFunction) {
        sendFunction();
        // After sending, the button becomes a 'stop' button
        switchToStopMode();
    }
}

/**
 * Handles the global Enter key press to send the form.
 * @param {KeyboardEvent} event 
 */
function handleGlobalEnter(event) {
    if (event.key === 'Enter' && !event.shiftKey && !actionButton.disabled) {
        event.preventDefault();
        handleSend();
    }
}

/**
 * Handles the 'stream_stopped' event from the server.
 */
function handleStreamStopped() {
    console.log("Received 'stream_stopped'. Resetting UI.");
    switchToListenMode();
}

// --- UI State Changers ---

/**
 * Configures the action button to be in 'Stop' mode (during streaming).
 */
function switchToStopMode() {
    buttonIcon.src = stopIconUrl;
    actionButton.removeEventListener('click', handleSend);
    actionButton.addEventListener('click', stopProcessing);
    checkButtonState();
}

/**
 * Configures the action button to be in 'Send' mode (listening for input).
 */
function switchToListenMode() {
    buttonIcon.src = arrowUpIconUrl; // arrowUpIconUrl must be defined globally in the HTML
    actionButton.removeEventListener('click', stopProcessing);
    actionButton.addEventListener('click', handleSend);
    checkButtonState();
}