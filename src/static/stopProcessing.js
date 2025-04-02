function stopProcessing() {
    const button = document.getElementById('action-button');
    socket.emit('stop_processing');
    button.removeEventListener("click", stopProcessing);
}