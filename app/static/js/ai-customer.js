(() => {
  const messages = document.getElementById('ai-messages');
  if (!messages) return;
  const token = document.getElementById('ai-csrf').value;
  const endpoints = Object.fromEntries(['endpoint', 'cart-proposal-endpoint', 'cart-confirm-endpoint', 'voice-endpoint', 'image-endpoint'].map((key) => [key, document.getElementById(`ai-${key}`).value]));

  const addMessage = (text, kind = 'assistant') => {
    const node = document.createElement('p');
    node.className = `ai-message ai-message--${kind}`;
    node.textContent = String(text || '');
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  };

  const appendProducts = (products) => {
    if (!Array.isArray(products) || !products.length) return;
    const list = document.createElement('div');
    list.className = 'ai-product-list';
    products.slice(0, 8).forEach((product) => {
      if (!product || !product.slug) return;
      const card = document.createElement('article');
      card.className = 'ai-product-card';
      const link = document.createElement('a');
      link.href = `/food/${encodeURIComponent(product.slug)}`;
      link.textContent = product.name || 'Catalog product';
      const details = document.createElement('p');
      details.textContent = `BDT ${product.price || '—'} · ${product.stock || 0} in stock`;
      card.append(link, details);
      list.appendChild(card);
    });
    messages.appendChild(list);
  };

  const appendVerifiedDetails = (result) => {
    const details = result.data && typeof result.data !== 'string'
      ? result.data
      : (Array.isArray(result.tool_results) ? result.tool_results
        .filter((item) => item && item.ok && item.result && typeof item.result === 'object')
        .map((item) => item.result)
        .filter((item) => !('slug' in item)) : []);
    if (!details || (Array.isArray(details) && details.length === 0)) return;
    const disclosure = document.createElement('details');
    disclosure.className = 'ai-verified-details';
    const summary = document.createElement('summary'); summary.textContent = 'Verified account and marketplace details';
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(details, null, 2).slice(0, 5000);
    disclosure.append(summary, pre); messages.appendChild(disclosure);
  };

  const appendSupport = (support) => {
    if (!support) return;
    const links = document.createElement('p'); links.className = 'ai-support-links';
    const addLink = (href, label) => {
      if (!href || !((href.startsWith('/') && !href.startsWith('//')) || href.startsWith('https://') || href.startsWith('mailto:'))) return;
      const link = document.createElement('a'); link.href = href; link.textContent = label;
      links.appendChild(link);
    };
    addLink(support.support_page, 'Open a support case');
    addLink(support.email ? `mailto:${support.email}` : '', support.email ? `Email ${support.email}` : '');
    addLink(support.support_url, 'Open support');
    if (links.childElementCount) messages.appendChild(links);
  };

  const maybeProposal = async (result) => {
    const proposed = (result.tool_results || []).find((item) => item && item.ok && item.result && item.result.requires_confirmation)?.result;
    if (!proposed) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button--secondary ai-confirm-button';
    button.textContent = `Review cart change: ${proposed.product || 'item'} · BDT ${proposed.price || '—'} × ${proposed.quantity ?? 0}`;
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const prepared = await fetch(endpoints['cart-proposal-endpoint'], {
          method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
          body: JSON.stringify({action: proposed.action, product_slug: proposed.product_slug,
            item_key: proposed.item_key,
            variant_id: proposed.variant_id, quantity: proposed.quantity}),
        });
        const body = await prepared.json();
        if (!prepared.ok || !body.ok) throw new Error(body.answer || 'The proposal could not be confirmed.');
        const response = await fetch(endpoints['cart-confirm-endpoint'], {
          method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
          body: JSON.stringify({proposal_id: body.proposal_id}),
        });
        const confirmed = await response.json();
        addMessage(confirmed.answer || 'Cart update finished.');
        if (confirmed.cart_url && confirmed.ok) {
          const link = document.createElement('a'); link.href = confirmed.cart_url; link.textContent = 'Open cart';
          messages.appendChild(link);
        }
      } catch (error) { addMessage(error.message || 'The cart change could not be completed.'); }
      finally { button.remove(); }
    });
    messages.appendChild(button);
  };

  const renderResult = async (result) => {
    addMessage(result.answer || result.fallback || 'The assistant could not verify that request.');
    appendProducts(result.products);
    appendVerifiedDetails(result);
    appendSupport(result.support_contact);
    await maybeProposal(result);
  };

  const submitForm = async (form, endpoint, mode) => {
    const data = new FormData(form);
    const pending = addMessage('Checking marketplace data…');
    try {
      const response = await fetch(endpoint, {method: 'POST', headers: {'X-CSRFToken': token}, body: data});
      const result = await response.json();
      pending.remove();
      if (result.transcript) addMessage(`Voice search: ${result.transcript}`, 'customer');
      await renderResult(result);
    } catch (_) { pending.remove(); addMessage('The assistant is unavailable. You can use the regular catalog search.'); }
    if (mode === 'upload') form.reset();
  };

  document.getElementById('ai-chat-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const prompt = form.elements.prompt.value.trim();
    if (!prompt) return;
    addMessage(prompt, 'customer');
    form.elements.prompt.value = '';
    const responseNode = addMessage('Checking marketplace data…');
    try {
      const response = await fetch(endpoints.endpoint, {method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': token}, body: JSON.stringify({prompt})});
      const result = await response.json();
      responseNode.remove();
      await renderResult(result);
    } catch (_) { responseNode.remove(); addMessage('The assistant is unavailable. You can use the regular catalog search.'); }
  });
  const voiceForm = document.getElementById('ai-voice-form');
  const recordButton = document.getElementById('ai-record-button');
  const recordStatus = document.getElementById('ai-record-status');
  let recording = null;
  voiceForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!voiceForm.elements.audio.files.length) { recordStatus.textContent = 'Choose a voice recording or use Start voice recording.'; return; }
    submitForm(voiceForm, endpoints['voice-endpoint'], 'upload');
  });
  recordButton.addEventListener('click', async () => {
    if (recording) { recording.stop(); return; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      recordStatus.textContent = 'Voice recording is unavailable in this browser. Choose an audio file instead.'; return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const chunks = [];
      const recorder = new MediaRecorder(stream);
      recording = recorder;
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        recording = null; recordButton.textContent = 'Start voice recording'; recordButton.disabled = false;
        const blob = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
        if (!blob.size) { recordStatus.textContent = 'No audio was captured. Try again or choose a file.'; return; }
        recordStatus.textContent = 'Transcribing your voice and searching the catalog…';
        const formData = new FormData(); formData.append('csrf_token', token);
        formData.append('audio', blob, 'voice.webm');
        const pending = addMessage('Checking marketplace data…');
        try {
          const response = await fetch(endpoints['voice-endpoint'], {method: 'POST', headers: {'X-CSRFToken': token}, body: formData});
          const result = await response.json(); pending.remove();
          if (result.transcript) addMessage(`Voice search: ${result.transcript}`, 'customer');
          await renderResult(result);
          recordStatus.textContent = 'Voice recording was processed in memory and not stored.';
        } catch (_) { pending.remove(); recordStatus.textContent = 'Voice search is temporarily unavailable.'; }
      };
      recorder.start(); recordButton.textContent = 'Stop and search';
      recordStatus.textContent = 'Recording… select Stop and search when ready (maximum 15 seconds).';
      window.setTimeout(() => { if (recording === recorder && recorder.state === 'recording') recorder.stop(); }, 15000);
    } catch (_) { recordStatus.textContent = 'Microphone access was unavailable. Choose an audio file instead.'; }
  });
  document.getElementById('ai-image-form').addEventListener('submit', (event) => {
    event.preventDefault(); submitForm(event.currentTarget, endpoints['image-endpoint'], 'upload');
  });
})();
