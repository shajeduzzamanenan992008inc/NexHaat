(() => {
  const messages = document.getElementById('ai-messages');
  if (!messages) return;
  const promptInput = document.getElementById('ai-prompt');
  const initialPrompt = (promptInput ? promptInput.value.trim() : '').trim();
  if (initialPrompt && promptInput && !promptInput.dataset.aiAutoSubmitted) {
    promptInput.dataset.aiAutoSubmitted = 'true';
    window.setTimeout(() => {
      if (promptInput.form && promptInput.value.trim()) {
        promptInput.form.requestSubmit();
      }
    }, 120);
  }
  const token = document.getElementById('ai-csrf').value;
  const endpoints = Object.fromEntries(['endpoint', 'cart-proposal-endpoint', 'cart-confirm-endpoint', 'voice-endpoint', 'image-endpoint', 'consent-endpoint', 'speak-endpoint'].map((key) => [key, document.getElementById(`ai-${key}`).value]));
  const attachmentInput = document.getElementById('ai-attachment-input');
  const attachButton = document.getElementById('ai-attach-button');
  const attachmentList = document.getElementById('ai-attachment-list');
  const voiceToggle = document.getElementById('ai-voice-toggle');
  const voiceMenu = document.getElementById('ai-voice-menu');
  const voiceRecordOption = document.getElementById('ai-voice-record');
  const voiceTalkOption = document.getElementById('ai-voice-talk');
  const history = [];
  let attachedFiles = [];
  let activeVoiceRecorder = null;
  let activeVoiceStream = null;

  const closeVoiceMenu = () => {
    if (!voiceMenu) return;
    voiceMenu.classList.remove('is-open');
    if (voiceToggle) voiceToggle.setAttribute('aria-expanded', 'false');
  };

  const sendPromptToAi = (promptText) => {
    const form = document.getElementById('ai-chat-form');
    const promptInput = form?.elements?.prompt;
    if (!form || !promptInput) {
      addMessage(promptText, 'customer');
      return;
    }
    promptInput.value = promptText;
    form.requestSubmit();
  };

  const renderAttachments = () => {
    if (!attachmentList) return;
    attachmentList.innerHTML = '';
    if (!attachedFiles.length) {
      attachmentList.hidden = true;
      return;
    }
    attachmentList.hidden = false;
    attachedFiles.forEach((file, index) => {
      const item = document.createElement('span');
      item.className = 'ai-attachment-item';
      item.innerHTML = `<span>${file.name}</span><button type="button" aria-label="Remove attachment">×</button>`;
      item.querySelector('button').addEventListener('click', () => {
        attachedFiles.splice(index, 1);
        renderAttachments();
      });
      attachmentList.appendChild(item);
    });
  };

  const queueAttachment = (files) => {
    const selected = Array.from(files || []).filter((file) => file && file.name);
    if (!selected.length) return;
    attachedFiles = [...attachedFiles, ...selected].slice(0, 5);
    renderAttachments();
  };

  const runVoiceSearch = async (blob, filename = 'voice-message.webm') => {
    const formData = new FormData();
    formData.append('csrf_token', token);
    formData.append('audio', blob, filename);
    const responseNode = addTypingIndicator();
    try {
      const response = await fetch(endpoints['voice-endpoint'], {
        method: 'POST', headers: { 'X-CSRFToken': token }, body: formData,
      });
      const result = await response.json();
      responseNode.remove();
      if (result.transcript) addMessage(`Voice search: ${result.transcript}`, 'customer');
      await renderResult(result);
    } catch (_) {
      responseNode.remove();
      addMessage('Voice search is temporarily unavailable. Try a file upload or a typed question instead.');
    }
  };

  const runImageSearch = async (file) => {
    const formData = new FormData();
    formData.append('csrf_token', token);
    formData.append('image', file, file.name || 'uploaded-image');
    const responseNode = addTypingIndicator();
    try {
      const response = await fetch(endpoints['image-endpoint'], {
        method: 'POST', headers: { 'X-CSRFToken': token }, body: formData,
      });
      const result = await response.json();
      responseNode.remove();
      if (result.search_description) addMessage(`Visual search: ${result.search_description}`, 'customer');
      await renderResult(result);
    } catch (_) {
      responseNode.remove();
      addMessage('Visual search is temporarily unavailable. Please try a catalog search or a different image.');
    }
  };

  const addMessage = (text, kind = 'assistant') => {
    const node = document.createElement('p');
    node.className = `ai-message ai-message--${kind}`;
    node.textContent = String(text || '');
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  };

  const addTypingIndicator = () => {
    const node = document.createElement('div');
    node.className = 'ai-message ai-message--assistant ai-message--typing';
    node.innerHTML = '<span class="ai-typing-dots" aria-label="AI is writing"><span></span><span></span><span></span></span>';
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

  const appendSources = (sources) => {
    if (!Array.isArray(sources) || !sources.length) return;
    const group = document.createElement('div'); group.className = 'ai-sources';
    const heading = document.createElement('strong'); heading.textContent = 'Sources'; group.appendChild(heading);
    sources.slice(0, 5).forEach((source) => {
      if (!source || typeof source.url !== 'string' || !source.url.startsWith('https://')) return;
      const row = document.createElement('div'); row.className = 'ai-source';
      const link = document.createElement('a'); link.href = source.url; link.textContent = source.title || 'Open source';
      link.target = '_blank'; link.rel = 'noopener noreferrer'; row.appendChild(link);
      if (source.snippet) { const snippet = document.createElement('small'); snippet.textContent = source.snippet; row.appendChild(snippet); }
      group.appendChild(row);
    });
    if (group.childElementCount > 1) messages.appendChild(group);
  };

  const appendSpeechButton = (answer) => {
    if (!answer) return;
    const group = document.createElement('div'); group.className = 'ai-message-actions';
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'button button--secondary'; button.textContent = 'Listen';
    button.addEventListener('click', async () => {
      button.disabled = true; button.textContent = 'Preparing voice…';
      try {
        const response = await fetch(endpoints['speak-endpoint'], {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({ text: answer.slice(0, 1200) }),
        });
        if (!response.ok) throw new Error('Local speech is unavailable.');
        const objectUrl = URL.createObjectURL(await response.blob());
        const audio = new Audio(objectUrl);
        audio.addEventListener('ended', () => URL.revokeObjectURL(objectUrl), { once: true });
        await audio.play(); button.textContent = 'Playing';
        audio.addEventListener('ended', () => { button.textContent = 'Listen'; button.disabled = false; }, { once: true });
      } catch (_) { button.textContent = 'Voice unavailable'; button.disabled = false; }
    });
    group.appendChild(button); messages.appendChild(group);
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
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({
            action: proposed.action, product_slug: proposed.product_slug,
            item_key: proposed.item_key,
            variant_id: proposed.variant_id, quantity: proposed.quantity
          }),
        });
        const body = await prepared.json();
        if (!prepared.ok || !body.ok) throw new Error(body.answer || 'The proposal could not be confirmed.');
        const response = await fetch(endpoints['cart-confirm-endpoint'], {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({ proposal_id: body.proposal_id }),
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
    const answer = result.answer || result.fallback || 'The assistant could not verify that request.';
    addMessage(answer);
    appendSpeechButton(answer);
    appendProducts(result.products);
    appendVerifiedDetails(result);
    appendSupport(result.support_contact);
    appendSources(result.sources);
    await maybeProposal(result);
    return answer;
  };

  if (attachButton && attachmentInput) {
    attachButton.addEventListener('click', () => {
      attachButton.classList.add('is-active');
      attachmentInput.click();
      window.setTimeout(() => attachButton.classList.remove('is-active'), 200);
    });
    attachmentInput.addEventListener('change', async (event) => {
      const files = Array.from(event.target.files || []);
      if (!files.length) return;
      attachButton.classList.add('is-uploading');
      const first = files[0];
      if (first.type.startsWith('image/')) {
        await runImageSearch(first);
        attachmentInput.value = '';
        attachedFiles = [];
        renderAttachments();
        window.setTimeout(() => attachButton.classList.remove('is-uploading'), 500);
        return;
      }
      if (first.type.startsWith('audio/')) {
        await runVoiceSearch(first, first.name);
        attachmentInput.value = '';
        attachedFiles = [];
        renderAttachments();
        window.setTimeout(() => attachButton.classList.remove('is-uploading'), 500);
        return;
      }
      queueAttachment(files);
      attachmentInput.value = '';
      window.setTimeout(() => attachButton.classList.remove('is-uploading'), 500);
    });
  }

  const consent = document.getElementById('ai-external-consent');
  const shouldUseExternalAi = () => {
    if (!consent) return true;
    return String(consent.value).toLowerCase() !== 'false';
  };

  const submitForm = async (form, endpoint, mode) => {
    const data = new FormData(form);
    const pending = addTypingIndicator();
    try {
      const response = await fetch(endpoint, { method: 'POST', headers: { 'X-CSRFToken': token }, body: data });
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
    const promptInput = form.elements.prompt;
    const prompt = promptInput.value.trim();
    const attachmentSummary = attachedFiles.length ? ` Attachments: ${attachedFiles.map((file) => file.name).join(', ')}` : '';
    const finalPrompt = (prompt + attachmentSummary).trim();
    if (!finalPrompt) return;
    addMessage(finalPrompt, 'customer');
    const priorHistory = history.slice(-8);
    history.push({ role: 'user', content: finalPrompt.slice(0, 1500) });
    promptInput.value = '';
    attachedFiles = [];
    renderAttachments();
    const responseNode = addTypingIndicator();
    try {
      const response = await fetch(endpoints.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
        body: JSON.stringify({ prompt: finalPrompt, history: priorHistory, external_ai_consent: shouldUseExternalAi() })
      });
      const result = await response.json();
      responseNode.remove();
      const answer = await renderResult(result);
      history.push({ role: 'assistant', content: String(answer || '').slice(0, 1500) });
      if (history.length > 8) history.splice(0, history.length - 8);
    } catch (_) { responseNode.remove(); addMessage('The assistant is unavailable. You can use the regular catalog search.'); }
  });

  if (voiceToggle) {
    voiceToggle.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!voiceMenu) return;
      const shouldOpen = !voiceMenu.classList.contains('is-open');
      closeVoiceMenu();
      if (shouldOpen) {
        voiceMenu.classList.add('is-open');
        voiceToggle.setAttribute('aria-expanded', 'true');
      }
    });

    document.addEventListener('click', (event) => {
      if (!voiceMenu) return;
      if (!voiceMenu.contains(event.target) && event.target !== voiceToggle) {
        closeVoiceMenu();
      }
    });
  }

  const startVoiceRecording = async () => {
    closeVoiceMenu();
    if (activeVoiceRecorder) {
      activeVoiceRecorder.stop();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      addMessage('Voice recording is unavailable in this browser. Please choose an audio file instead.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      activeVoiceRecorder = recorder;
      activeVoiceStream = stream;
      voiceToggle.classList.add('is-recording');
      voiceToggle.textContent = '■';
      voiceToggle.setAttribute('aria-label', 'Stop voice recording');
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        if (activeVoiceStream) {
          activeVoiceStream.getTracks().forEach((track) => track.stop());
        }
        activeVoiceRecorder = null;
        activeVoiceStream = null;
        voiceToggle.classList.remove('is-recording');
        voiceToggle.textContent = '🎙️';
        voiceToggle.setAttribute('aria-label', 'Voice options');
        if (!blob.size) {
          addMessage('No voice clip was captured. Please try again.');
          return;
        }
        await runVoiceSearch(blob, 'voice-message.webm');
      };
      recorder.start();
      addMessage('Voice chat is recording… say your question and click the mic again to stop.', 'customer');
      window.setTimeout(() => {
        if (activeVoiceRecorder && activeVoiceRecorder.state === 'recording') {
          activeVoiceRecorder.stop();
        }
      }, 15000);
    } catch (_) {
      addMessage('Microphone access was blocked. Please allow mic access or choose an audio file.');
    }
  };

  const startDirectTalkToAi = () => {
    closeVoiceMenu();
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addMessage('Direct voice-to-text is not supported in this browser. Please record audio or upload a file instead.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onstart = () => {
      voiceToggle.classList.add('is-recording');
      voiceToggle.textContent = '🎧';
      voiceToggle.setAttribute('aria-label', 'Listening to AI voice input');
      addMessage('Listening… speak your question and I will send it to the assistant.', 'customer');
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || '')
        .join(' ')
        .trim();
      if (transcript) {
        if (event.results[event.results.length - 1]?.isFinal) {
          voiceToggle.classList.remove('is-recording');
          voiceToggle.textContent = '🎙️';
          voiceToggle.setAttribute('aria-label', 'Voice options');
          sendPromptToAi(transcript);
        }
      }
    };

    recognition.onerror = () => {
      voiceToggle.classList.remove('is-recording');
      voiceToggle.textContent = '🎙️';
      voiceToggle.setAttribute('aria-label', 'Voice options');
      addMessage('Direct voice input was interrupted. Please try again or record your voice instead.');
    };

    recognition.onend = () => {
      voiceToggle.classList.remove('is-recording');
      voiceToggle.textContent = '🎙️';
      voiceToggle.setAttribute('aria-label', 'Voice options');
    };

    recognition.start();
  };

  if (voiceRecordOption) {
    voiceRecordOption.addEventListener('click', startVoiceRecording);
  }

  if (voiceTalkOption) {
    voiceTalkOption.addEventListener('click', startDirectTalkToAi);
  }
  const voiceForm = document.getElementById('ai-voice-form');
  const recordButton = document.getElementById('ai-record-button');
  const recordStatus = document.getElementById('ai-record-status');
  let recording = null;
  if (voiceForm && recordButton && recordStatus) {
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
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const chunks = [];
        const recorder = new MediaRecorder(stream);
        recording = recorder;
        recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
        recorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          recording = null;
          recordButton.classList.remove('is-recording');
          recordButton.textContent = 'Start voice recording';
          recordButton.disabled = false;
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          if (!blob.size) { recordStatus.textContent = 'No audio was captured. Try again or choose a file.'; return; }
          recordStatus.textContent = 'Transcribing your voice and searching the catalog…';
          await runVoiceSearch(blob, 'voice.webm');
          recordStatus.textContent = 'Voice recording was processed in memory and not stored.';
        };
        recorder.start();
        recordButton.classList.add('is-recording');
        recordButton.textContent = 'Stop and search';
        recordStatus.textContent = 'Recording… select Stop and search when ready (maximum 15 seconds).';
        window.setTimeout(() => { if (recording === recorder && recorder.state === 'recording') recorder.stop(); }, 15000);
      } catch (_) { recordStatus.textContent = 'Microphone access was unavailable. Choose an audio file instead.'; }
    });
  }
  const imageForm = document.getElementById('ai-image-form');
  const imageInput = document.getElementById('ai-image');
  const imageTrigger = document.getElementById('ai-image-trigger');
  if (imageForm && imageInput && imageTrigger) {
    imageTrigger.addEventListener('click', () => {
      imageInput.click();
    });
    imageInput.addEventListener('change', () => {
      if (!imageInput.files || !imageInput.files.length) return;
      const file = imageInput.files[0];
      imageTrigger.textContent = file.name || 'Image selected';
      imageTrigger.classList.add('is-selected');
      runImageSearch(file);
      imageInput.value = '';
      imageTrigger.textContent = 'Find similar products';
      imageTrigger.classList.remove('is-selected');
    });
  }
})();
