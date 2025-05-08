document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('input');
    const button = document.getElementById('action-button');

    checkButtonState();

    input.addEventListener('input', checkButtonState);

    function checkButtonState() {
        const isEmpty = input.value.trim() === '';

        button.disabled = isEmpty;

        if (isEmpty) {
            button.classList.add('disabled');
          } else {
            button.classList.remove('disabled');
          }
    }
});