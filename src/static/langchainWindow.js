function openLangchainChat(containerId) {
    if (!containerId) {
        console.error("Cannot open chat: containerId is missing.");
        alert("Error: Could not identify the document for chat.");
        return;
    }
    // Construct the URL with the containerId as a query parameter
    const chatUrl = `/langchainChat?contentId=${encodeURIComponent(containerId)}`;
    window.open(chatUrl, '_blank'); // Open in a new tab
}