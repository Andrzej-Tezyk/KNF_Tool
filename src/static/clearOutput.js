document.addEventListener('DOMContentLoaded', function() {
    
    const clearBtn = document.getElementById('clean-button');
    const outputDiv = document.getElementById('output');
    clearBtn.addEventListener('click', clearOutput);
    
    // clear button
    function clearOutput() {
        stopProcessing()
        outputDiv.innerHTML = ''; // clear previous output
    }
});