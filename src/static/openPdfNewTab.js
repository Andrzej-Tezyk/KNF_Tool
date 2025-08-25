function openPdfNewTab(filename) {
    if (!filename) {
        console.error("Filename is missing.");
        return;
    }

    const pdfUrl = `/files/${encodeURIComponent(filename)}`;
    window.open(pdfUrl, '_blank');
}