document.addEventListener('DOMContentLoaded', function() { 
  //inputText.addEventListener('input', checkButtonState);
  function checkButtonState() {
      const button = document.getElementById('action-button');
      const inputText = document.getElementById('input');
      const img = button.querySelector('img');
      const isEmpty = inputText.value.trim() === '';
      const isArrowUpIcon = img && img.src.includes('arrow-up-solid.svg');

      const shouldDisable = isEmpty && isArrowUpIcon;

      button.disabled = shouldDisable;

      if (shouldDisable) {
          button.classList.add('disabled');
      } else {
          button.classList.remove('disabled');
      }
  }
});