// Place this in copyEditPanel.js, loaded on every page
console.log('copyEditPanel.js loaded');

document.addEventListener('click', async function(e) {
    // ======================
    // COPY BUTTON
    // ======================
    const copyBtn = e.target.closest('#copy-button, .copy-button'); 
    if (copyBtn) {
        const container = copyBtn.closest('.output-content');
        if (!container) return;

        const block = container.querySelector('.markdown-body');
        if (!block) return;

        try {
            await navigator.clipboard.write([
                new ClipboardItem({
                    "text/html": new Blob([block.innerHTML], { type: "text/html" }),
                    "text/plain": new Blob([block.innerText], { type: "text/plain" })
                })
            ]);
            alert("Copied to clipboard with formatting!");
        } catch (err) {
            console.error(err);
            alert("Copy failed.");
        }

        return;
    }


    // ======================
    // DOWNLOAD BUTTON
    // ======================
    // const testHtml = `
    //     <p>Example <strong>bold</strong> and <em>italic</em> text.</p>
    //     <ul>
    //       <li>First item</li>
    //       <li>Second item</li>
    //     </ul>
    // `;

    const downloadBtn = e.target.closest('#download-button, .download-button');
    if (downloadBtn) {
        // znajdź najbliższy blok output-content
        const container = downloadBtn.closest('.output-content');
        if (!container) return;

        // weź markdown-body tylko z tego kontenera
        const block = container.querySelector('.markdown-body');
        if (!block) return;

        const htmlContent = block.innerHTML;

        try {
            // Send HTML to backend
            const response = await fetch('/download_docx', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: htmlContent })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            // Receive the .docx file
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            // Trigger download
            const a = document.createElement("a");
            a.href = url;
            a.download = "output.docx";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            alert("Word file downloaded.");
        } catch (err) {
            console.error(err);
            alert("Failed to download file from server.");
        }
    }
});