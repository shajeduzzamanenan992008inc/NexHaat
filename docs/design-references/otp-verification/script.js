(() => {
  const card = document.querySelector('[data-card]');
  const inputs = [...document.querySelectorAll('[data-digit]')];
  const loading = document.querySelector('[data-loading]');
  const success = document.querySelector('[data-success]');
  const error = document.querySelector('[data-error]');
  const message = document.querySelector('[data-message]');
  const resend = document.querySelector('[data-resend]');
  const inputStage = document.querySelector('[data-input-stage]');

  function fillDigits(value, startIndex = 0) {
    const digits = value.replace(/\D/g, '').slice(0, inputs.length - startIndex).split('');
    digits.forEach((digit, offset) => {
      const input = inputs[startIndex + offset];
      input.value = digit;
      input.classList.add('filled');
    });
    const nextIndex = startIndex + digits.length;
    if (nextIndex < inputs.length) inputs[nextIndex].focus();
    if (inputs.every((item) => item.value)) {
      showState('loading');
      window.setTimeout(() => showState('success'), 900);
    }
  }

  function showState(state) {
    card.dataset.state = state;
    loading.classList.toggle('active', state === 'loading');
    success.classList.toggle('active', state === 'success');
    error.classList.toggle('active', state === 'error');
    document.querySelector('[data-input-stage]').hidden = state !== 'idle' && state !== 'error';
  }

  inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
      const value = input.value;
      input.value = '';
      fillDigits(value, index);
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Backspace' && !input.value && index > 0) inputs[index - 1].focus();
    });
  });

  inputStage.addEventListener('paste', (event) => {
    event.preventDefault();
    fillDigits(
      event.clipboardData.getData('text'),
      Math.max(0, inputs.indexOf(document.activeElement)),
    );
  });

  resend.addEventListener('click', () => {
    inputs.forEach((input) => { input.value = ''; input.classList.remove('filled'); });
    message.textContent = 'A new code would be sent here.';
    showState('idle');
    inputs[0].focus();
  });
})();
