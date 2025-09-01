document.addEventListener('DOMContentLoaded', () => {
    const uploadButton = document.getElementById('uploadFileButton');

    if (uploadButton) {
        uploadButton.addEventListener('click', () => {
            // 1. Stwórz dynamicznie element input, aby otworzyć okno dialogowe
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.pdf'; // Ogranicz wybór do plików PDF
            fileInput.style.display = 'none';

            // 2. Obsłuż wybór pliku przez użytkownika
            fileInput.addEventListener('change', (event) => {
                const file = event.target.files[0];
                if (file) {
                    console.log(`File selected: ${file.name}`);
                    uploadFile(file);
                }
            });

            // 3. Dodaj input do body i programowo go kliknij
            document.body.appendChild(fileInput);
            fileInput.click();

            // 4. Usuń element po użyciu
            document.body.removeChild(fileInput);
        });
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        console.log('Uploading file...');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (response.ok) {
                console.log('Upload successful:', result);
                // Additional UI updates can be added here 
                alert(`Plik "${result.filename}" został pomyślnie przesłany!`);
                // Simple page refresh to see the file in the list.
                // In the final version, replacement with a dynamic update.
                window.location.reload(); 
            } else {
                console.error('Upload failed:', result);
                alert(`Błąd podczas przesyłania pliku: ${result.error}`);
            }
        } catch (error) {
            console.error('An error occurred during upload:', error);
            alert('Wystąpił nieoczekiwany błąd. Sprawdź konsolę deweloperską.');
        }
    }
});