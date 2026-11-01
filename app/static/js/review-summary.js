(() => {
  const button = document.getElementById('review-ai-summary-button');
  if (!button) return;
  button.addEventListener('click', async () => {
    const output = document.getElementById('review-ai-summary-output');
    button.disabled = true;
    output.textContent = 'Summarizing approved reviews…';
    try {
      const response = await fetch(document.getElementById('review-ai-summary-endpoint').value, {headers: {'Accept': 'application/json'}});
      const result = await response.json();
      output.textContent = result.summary || 'A verified summary is unavailable.';
    } catch (_) { output.textContent = 'A review summary is temporarily unavailable.'; }
    finally { button.disabled = false; }
  });
})();
