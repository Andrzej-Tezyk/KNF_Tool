document.addEventListener('DOMContentLoaded', function() {
    
    const clearBtn = document.getElementById('clean-button');
    clearBtn.addEventListener('click', clearOutput);
    
    // clear button
    function clearOutput() {
        stopProcessing()
        outputDiv.innerHTML = ''; // clear previous output
    }
});