document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('input');
    const button = document.getElementById('action-button');

    input.addEventListener('input', function() {
        button.disabled = !input.value.trim();
    });
});