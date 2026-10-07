(() => {
  const form = document.getElementById('rider-ai-form');
  if (!form) return;
  const messages = document.getElementById('rider-ai-messages');
  const token = document.getElementById('rider-ai-csrf').value;
  const append = (value, kind = 'assistant') => {
    const node = document.createElement('p');
    node.className = `ai-message ai-message--${kind}`;
    node.textContent = String(value || '');
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const prompt = document.getElementById('rider-ai-prompt').value.trim();
    if (!prompt) return;
    append(prompt, 'customer');
    document.getElementById('rider-ai-prompt').value = '';
    const pending = append('Checking your assigned delivery information…');
    try {
      const response = await fetch('/rider/ai/query', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
        body: JSON.stringify({prompt}),
      });
      const result = await response.json();
      pending.remove();
      append(result.answer || result.fallback || 'The delivery assistant is unavailable.');
      if (result.data && Array.isArray(result.data) && result.data.length) {
        const details = document.createElement('details');
        details.className = 'ai-verified-details';
        const summary = document.createElement('summary'); summary.textContent = 'Assigned delivery details';
        const body = document.createElement('pre'); body.textContent = JSON.stringify(result.data, null, 2).slice(0, 5000);
        details.append(summary, body); messages.appendChild(details);
      }
    } catch (_) { pending.remove(); append('The delivery assistant is unavailable. Your dashboard remains available.'); }
  });
})();
