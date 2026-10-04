(() => {
  const card = document.querySelector('[data-card]');
  const inputs = [...document.querySelectorAll('[data-digit]')];
  const loading = document.querySelector('[data-loading]');
  const success = document.querySelector('[data-success]');
  const error = document.querySelector('[data-error]');
  const message = document.querySelector('[data-message]');
  const resend = document.querySelector('[data-resend]');

  function showState(state) {
    card.dataset.state = state;
    loading.classList.toggle('active', state === 'loading');
    success.classList.toggle('active', state === 'success');
    error.classList.toggle('active', state === 'error');
    document.querySelector('[data-input-stage]').hidden = state !== 'idle' && state !== 'error';
  }

  inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
      input.value = input.value.replace(/\D/g, '').slice(0, input.maxLength);
      input.classList.toggle('filled', Boolean(input.value));
      if (input.value && index < inputs.length - 1) inputs[index + 1].focus();
      if (inputs.every((item) => item.value)) {
        showState('loading');
        window.setTimeout(() => showState('success'), 900);
      }
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Backspace' && !input.value && index > 0) inputs[index - 1].focus();
    });
  });

  resend.addEventListener('click', () => {
    inputs.forEach((input) => { input.value = ''; input.classList.remove('filled'); });
    message.textContent = 'A new code would be sent here.';
    showState('idle');
    inputs[0].focus();
  });
})();
