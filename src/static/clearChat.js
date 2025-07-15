document.addEventListener('DOMContentLoaded', function() {

    const clearChatBtn = document.getElementById('clean-button');
    const chatOutput = document.getElementById('output');

    clearChatBtn.addEventListener('click', function() {
        const contentId = chatOutput.dataset.contentId;
        if (contentId) {
            socket.emit('reset_chat_history', { 'contentId': contentId });
            location.reload()
        }
    });
});