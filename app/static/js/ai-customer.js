(() => {
  const messages = document.getElementById('ai-messages');
  if (!messages) return;
  const comparisonContainer = document.getElementById('ai-comparison');
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
  const endpoints = Object.fromEntries(['endpoint', 'health-endpoint', 'cart-proposal-endpoint', 'cart-confirm-endpoint', 'voice-endpoint', 'image-endpoint', 'consent-endpoint', 'speak-endpoint'].map((key) => [key, document.getElementById(`ai-${key}`)?.value]));
  const attachmentInput = document.getElementById('ai-attachment-input');
  const attachButton = document.getElementById('ai-attach-button');
  const attachmentList = document.getElementById('ai-attachment-list');
  const voiceToggle = document.getElementById('ai-voice-toggle');
  const voiceMenu = document.getElementById('ai-voice-menu');
  const voiceRecordOption = document.getElementById('ai-voice-record');
  const voiceTalkOption = document.getElementById('ai-voice-talk');
  const voiceForm = document.getElementById('ai-voice-form');
  const recordButton = document.getElementById('ai-record-button');
  const recordStatus = document.getElementById('ai-record-status');
  const voiceTranscriptionConfigured = document.getElementById('ai-voice-transcription-configured')?.value === 'true';
  const speechOutputConfigured = document.getElementById('ai-speech-output-configured')?.value === 'true';
  const aiServiceStatus = document.getElementById('ai-service-status');
  const externalAssistanceNotice = document.getElementById('ai-external-assistance-notice')?.textContent.trim();
  const externalConsentStatus = document.getElementById('ai-external-consent-status');
  const customerCartEnabled = document.getElementById('ai-customer-cart-enabled')?.value === 'true';
  const customerApiEnabled = document.getElementById('ai-customer-api-enabled')?.value === 'true';
  const usageStatus = document.getElementById('ai-usage-status');
  const usageEndpoint = '/api/v1/ai/usage';
  const documentEndpoint = document.getElementById('ai-document-api-endpoint')?.value;
  const documentUploadForm = document.getElementById('ai-document-upload');
  const documentList = document.getElementById('ai-document-list');
  const documentStatus = document.getElementById('ai-document-status');
  const cartUrl = document.getElementById('ai-cart-url')?.value || '/cart';
  const checkoutUrl = document.getElementById('ai-checkout-url')?.value || '/checkout';
  const history = [];
  const recentProductSlugs = [];
  const comparisonSelections = new Map();
  let attachedFiles = [];
  let activeVoiceRecorder = null;
  let activeVoiceStream = null;
  let activeVoiceMode = null;
  let pendingCartConfirmation = null;
  let selectedDocumentIds = [];
  let consentUpdate = Promise.resolve();

  const refreshCustomerUsage = async () => {
    if (!customerApiEnabled || !usageStatus) return;
    try {
      const response = await fetch(usageEndpoint, {
        headers: { Accept: 'application/json' },
        cache: 'no-store'
      });
      const payload = await response.json();
      if (!response.ok || payload.success !== true || !payload.data) {
        throw new Error(payload.error?.message || 'Your AI usage could not be loaded.');
      }
      usageStatus.textContent = `AI requests: ${payload.data.used} of ${payload.data.limit} used; ${payload.data.remaining} remaining.`;
    } catch (error) {
      usageStatus.textContent = error.message || 'Your AI usage could not be loaded.';
    }
  };
  refreshCustomerUsage();

  if (aiServiceStatus && endpoints['health-endpoint']) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    fetch(endpoints['health-endpoint'], {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: controller.signal
    }).then(async (response) => {
      const result = await response.json();
      aiServiceStatus.textContent = result.message || 'AI service health is unavailable.';
      aiServiceStatus.dataset.status = result.status || 'unknown';
    }).catch(() => {
      aiServiceStatus.textContent = 'AI service status could not be checked. Catalog search and account tools remain available.';
      aiServiceStatus.dataset.status = 'unknown';
    }).finally(() => window.clearTimeout(timeout));
  }

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

  document.querySelectorAll('[data-ai-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      const prompt = button.getAttribute('data-ai-prompt') || '';
      if (promptInput) promptInput.value = prompt;
      document.getElementById('ai-chat-form')?.requestSubmit();
    });
  });

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
    if (!voiceTranscriptionConfigured) {
      addMessage('Private voice transcription is not configured. You can type your question instead.');
      return false;
    }
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
      return Boolean(result.transcript);
    } catch (_) {
      responseNode.remove();
      addMessage('Voice search is temporarily unavailable. Try a file upload or a typed question instead.');
      return false;
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

  const appendInlineMarkdown = (parent, text) => {
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
    let cursor = 0;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      parent.appendChild(document.createTextNode(text.slice(cursor, match.index)));
      const token = match[0];
      if (token.startsWith('**')) {
        const strong = document.createElement('strong');
        strong.textContent = token.slice(2, -2);
        parent.appendChild(strong);
      } else if (token.startsWith('`')) {
        const code = document.createElement('code');
        code.textContent = token.slice(1, -1);
        parent.appendChild(code);
      } else if (token.startsWith('*')) {
        const emphasis = document.createElement('em');
        emphasis.textContent = token.slice(1, -1);
        parent.appendChild(emphasis);
      } else {
        const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
        const href = linkMatch?.[2]?.trim() || '';
        const safeHref = (href.startsWith('/') && !href.startsWith('//'))
          || href.startsWith('https://') || href.startsWith('mailto:');
        if (!safeHref || !linkMatch) {
          parent.appendChild(document.createTextNode(token));
        } else {
          const link = document.createElement('a');
          link.href = href;
          link.textContent = linkMatch[1];
          if (href.startsWith('https://')) {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
          }
          parent.appendChild(link);
        }
      }
      cursor = match.index + token.length;
    }
    parent.appendChild(document.createTextNode(text.slice(cursor)));
  };

  const renderMessageMarkdown = (container, value) => {
    const lines = String(value || '').replace(/\r\n?/g, '\n').split('\n');
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) { index += 1; continue; }
      if (/^\s*```/.test(line)) {
        const codeLines = [];
        index += 1;
        while (index < lines.length && !/^\s*```/.test(lines[index])) {
          codeLines.push(lines[index++]);
        }
        if (index < lines.length) index += 1;
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = codeLines.join('\n');
        pre.appendChild(code);
        container.appendChild(pre);
        continue;
      }
      const heading = /^(#{1,6})\s+(.+)$/.exec(line);
      if (heading) {
        const node = document.createElement(`h${heading[1].length}`);
        appendInlineMarkdown(node, heading[2]);
        container.appendChild(node);
        index += 1;
        continue;
      }
      const listMatch = /^\s*(?:[-*]\s+|\d+[.)]\s+)/.exec(line);
      if (listMatch) {
        const ordered = /^\s*\d+[.)]\s+/.test(line);
        const list = document.createElement(ordered ? 'ol' : 'ul');
        while (index < lines.length) {
          const itemMatch = /^\s*(?:[-*]\s+|\d+[.)]\s+)(.+)$/.exec(lines[index]);
          if (!itemMatch || /^\s*\d+[.)]\s+/.test(lines[index]) !== ordered) break;
          const item = document.createElement('li');
          appendInlineMarkdown(item, itemMatch[1]);
          list.appendChild(item);
          index += 1;
        }
        container.appendChild(list);
        continue;
      }
      if (line.includes('|') && index + 1 < lines.length
          && /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1])) {
        const cells = (row) => row.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
        const headings = cells(line);
        const table = document.createElement('table');
        const head = document.createElement('thead');
        const headRow = document.createElement('tr');
        headings.forEach((label) => {
          const cell = document.createElement('th');
          appendInlineMarkdown(cell, label);
          headRow.appendChild(cell);
        });
        head.appendChild(headRow);
        table.appendChild(head);
        index += 2;
        const body = document.createElement('tbody');
        while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
          const row = document.createElement('tr');
          cells(lines[index]).forEach((value) => {
            const cell = document.createElement('td');
            appendInlineMarkdown(cell, value);
            row.appendChild(cell);
          });
          body.appendChild(row);
          index += 1;
        }
        table.appendChild(body);
        container.appendChild(table);
        continue;
      }
      const paragraph = document.createElement('p');
      const paragraphLines = [];
      while (index < lines.length && lines[index].trim()
          && !/^\s*```/.test(lines[index])
          && !/^(#{1,6})\s+/.test(lines[index])
          && !/^\s*(?:[-*]\s+|\d+[.)]\s+)/.test(lines[index])
          && !(lines[index].includes('|') && index + 1 < lines.length
            && /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1]))) {
        paragraphLines.push(lines[index++]);
      }
      appendInlineMarkdown(paragraph, paragraphLines.join(' '));
      container.appendChild(paragraph);
    }
  };

  const addMessage = (text, kind = 'assistant') => {
    const node = document.createElement('div');
    node.className = `ai-message ai-message--${kind}`;
    const content = document.createElement('div');
    content.className = 'ai-message__content';
    renderMessageMarkdown(content, text);
    node.appendChild(content);
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

  const appendComparison = () => {
    if (!comparisonContainer) return;
    comparisonContainer.replaceChildren();
    comparisonContainer.hidden = comparisonSelections.size !== 2;
    if (comparisonContainer.hidden) return;
    const selected = [...comparisonSelections.values()];
    const section = document.createElement('section');
    section.className = 'ai-product-comparison';
    section.setAttribute('aria-label', 'Product comparison');
    const heading = document.createElement('h3');
    heading.textContent = 'Product comparison';
    const table = document.createElement('table');
    const caption = document.createElement('caption');
    caption.textContent = 'Marketplace details for the selected products';
    table.appendChild(caption);
    const head = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const featureHeader = document.createElement('th');
    featureHeader.scope = 'col';
    featureHeader.textContent = 'Feature';
    headerRow.appendChild(featureHeader);
    selected.forEach((product) => {
      const cell = document.createElement('th');
      cell.scope = 'col';
      cell.textContent = product.name || 'Catalog product';
      headerRow.appendChild(cell);
    });
    head.appendChild(headerRow);
    table.appendChild(head);
    const body = document.createElement('tbody');
    [
      ['Price', (product) => `BDT ${product.price || '—'}`],
      ['Available stock', (product) => String(product.stock ?? 0)],
      ['Category', (product) => product.category || 'Not listed'],
      ['Brand', (product) => product.brand || 'Not listed'],
      ['Approved rating', (product) => product.rating != null && product.review_count
        ? `${product.rating}/5 (${product.review_count} reviews)` : 'No approved reviews'],
    ].forEach(([label, value]) => {
      const row = document.createElement('tr');
      const headingCell = document.createElement('th');
      headingCell.scope = 'row';
      headingCell.textContent = label;
      row.appendChild(headingCell);
      selected.forEach((product) => {
        const cell = document.createElement('td');
        cell.textContent = value(product);
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.appendChild(body);
    section.append(heading, table);
    comparisonContainer.appendChild(section);
  };

  const appendCartAction = (product, actions, variantSelect) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button--secondary';
    button.textContent = 'Add to cart';
    button.addEventListener('click', async () => {
      const variantId = variantSelect?.value || null;
      if (variantSelect && !variantId) {
        addMessage(`Choose an available option for ${product.name} first.`);
        variantSelect.focus();
        return;
      }
      button.disabled = true;
      button.textContent = 'Checking current price…';
      pendingCartConfirmation?.remove();
      pendingCartConfirmation = null;
      try {
        const response = await fetch(endpoints['cart-proposal-endpoint'], {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({
            action: 'add', product_slug: product.slug, quantity: 1,
            ...(variantId ? { variant_id: Number(variantId) } : {}),
          }),
        });
        const result = await response.json();
        if (!response.ok || !result.ok || !result.proposal) {
          throw new Error(result.answer || 'The cart suggestion could not be prepared.');
        }
        const proposal = result.proposal;
        const review = document.createElement('div');
        review.className = 'ai-cart-review';
        review.setAttribute('role', 'group');
        review.setAttribute('aria-label', 'Review cart addition');
        const summary = document.createElement('p');
        summary.textContent = `Add ${proposal.product} × ${proposal.quantity} at BDT ${proposal.price} each? Checkout is a separate step.`;
        const confirm = document.createElement('button');
        confirm.type = 'button';
        confirm.className = 'button';
        confirm.textContent = 'Confirm add to cart';
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'button button--secondary';
        cancel.textContent = 'Cancel';
        cancel.addEventListener('click', () => {
          review.remove();
          if (pendingCartConfirmation === review) pendingCartConfirmation = null;
          button.disabled = false;
          button.textContent = 'Add to cart';
        });
        confirm.addEventListener('click', async () => {
          confirm.disabled = true;
          cancel.disabled = true;
          try {
            const confirmedResponse = await fetch(endpoints['cart-confirm-endpoint'], {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
              body: JSON.stringify({ proposal_id: result.proposal_id }),
            });
            const confirmed = await confirmedResponse.json();
            if (!confirmedResponse.ok || !confirmed.ok) {
              throw new Error(confirmed.answer || 'The cart could not be updated.');
            }
            review.remove();
            if (pendingCartConfirmation === review) pendingCartConfirmation = null;
            addMessage(confirmed.answer || 'Your cart was updated. Checkout remains a separate step.');
            const links = document.createElement('div');
            links.className = 'ai-message-actions';
            [[cartUrl, 'Open cart'], [checkoutUrl, 'Continue to checkout']].forEach(([href, label]) => {
              const link = document.createElement('a');
              link.className = 'button button--secondary';
              link.href = href;
              link.textContent = label;
              links.appendChild(link);
            });
            messages.appendChild(links);
            button.textContent = 'Added to cart';
          } catch (error) {
            addMessage(error.message || 'The cart could not be updated.');
            confirm.disabled = false;
            cancel.disabled = false;
          }
        });
        review.append(summary, confirm, cancel);
        actions.appendChild(review);
        pendingCartConfirmation = review;
        button.textContent = 'Review pending';
      } catch (error) {
        addMessage(error.message || 'The cart suggestion could not be prepared.');
        button.disabled = false;
        button.textContent = 'Add to cart';
      }
    });
    actions.appendChild(button);
  };

  const appendProducts = (products) => {
    if (!Array.isArray(products) || !products.length) return;
    const list = document.createElement('div');
    list.className = 'ai-product-list';
    products.slice(0, 8).forEach((product) => {
      if (!product || !product.slug) return;
      const card = document.createElement('article');
      card.className = 'ai-product-card';
      if (typeof product.image === 'string' && product.image.trim()) {
        try {
          const imageUrl = new URL(product.image, window.location.origin);
          if (imageUrl.protocol === 'https:'
              || (imageUrl.protocol === 'http:' && imageUrl.origin === window.location.origin)) {
            const image = document.createElement('img');
            image.src = imageUrl.href;
            image.alt = product.name ? `${product.name} product image` : 'Product image';
            image.loading = 'lazy';
            image.decoding = 'async';
            image.className = 'ai-product-card__image';
            card.appendChild(image);
          }
        } catch (_) { /* Invalid catalog image references are not rendered. */ }
      }
      const link = document.createElement('a');
      link.href = `/food/${encodeURIComponent(product.slug)}`;
      link.textContent = product.name || 'Catalog product';
      const title = document.createElement('h3');
      title.appendChild(link);
      const details = document.createElement('p');
      const rating = product.rating != null && product.review_count
        ? ` · ⭐ ${product.rating}/5 (${product.review_count} approved reviews)` : '';
      details.textContent = `BDT ${product.price || '—'} · ${product.stock || 0} in stock${rating}`;
      const actions = document.createElement('div');
      actions.className = 'ai-product-card__actions';
      const viewDetails = document.createElement('a');
      viewDetails.className = 'button button--secondary';
      viewDetails.href = `/food/${encodeURIComponent(product.slug)}`;
      viewDetails.textContent = 'View details';
      actions.appendChild(viewDetails);
      const compare = document.createElement('button');
      compare.type = 'button';
      compare.className = 'button button--secondary';
      compare.textContent = comparisonSelections.has(product.slug) ? 'Remove from compare' : 'Select to compare';
      compare.setAttribute('aria-pressed', String(comparisonSelections.has(product.slug)));
      compare.addEventListener('click', () => {
        if (comparisonSelections.has(product.slug)) {
          comparisonSelections.delete(product.slug);
        } else {
          if (comparisonSelections.size === 2) {
            comparisonSelections.clear();
            addMessage('Comparison selection restarted. Choose two products.');
          }
          comparisonSelections.set(product.slug, product);
        }
        compare.setAttribute('aria-pressed', String(comparisonSelections.has(product.slug)));
        compare.textContent = comparisonSelections.has(product.slug) ? 'Remove from compare' : 'Select to compare';
        appendComparison();
      });
      actions.appendChild(compare);
      const activeVariants = Array.isArray(product.variants)
        ? product.variants.filter((variant) => variant && variant.available && variant.id)
        : [];
      if (customerCartEnabled && (activeVariants.length || Number(product.stock) > 0)) {
        let variantSelect = null;
        if (activeVariants.length) {
          const label = document.createElement('label');
          label.textContent = `Choose an option for ${product.name}`;
          variantSelect = document.createElement('select');
          const placeholder = document.createElement('option');
          placeholder.value = '';
          placeholder.textContent = 'Choose an option';
          variantSelect.appendChild(placeholder);
          activeVariants.forEach((variant) => {
            const option = document.createElement('option');
            option.value = String(variant.id);
            option.textContent = `${variant.label} · BDT ${variant.price}`;
            variantSelect.appendChild(option);
          });
          label.appendChild(variantSelect);
          label.className = 'ai-product-card__variant';
          card.appendChild(label);
        }
        appendCartAction(product, actions, variantSelect);
      }
      card.prepend(title);
      card.append(details, actions);
      list.appendChild(card);
    });
    messages.appendChild(list);
  };

  const appendCategories = (result) => {
    if (!result.tools_used?.includes('get_categories') || !Array.isArray(result.data)) return;
    const list = document.createElement('div');
    list.className = 'ai-message-actions';
    list.setAttribute('aria-label', 'Browse categories');
    result.data.slice(0, 12).forEach((category) => {
      if (!category || typeof category.name !== 'string' || typeof category.slug !== 'string') return;
      const link = document.createElement('a');
      link.className = 'button button--secondary';
      link.href = `/category/${encodeURIComponent(category.slug)}`;
      link.textContent = category.name;
      list.appendChild(link);
    });
    if (list.childElementCount) messages.appendChild(list);
  };

  const appendVerifiedDetails = (result) => {
    if (result.tools_used?.includes('get_categories')) return;
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
      if (!source) return;
      const row = document.createElement('div'); row.className = 'ai-source';
      if (typeof source.url === 'string' && source.url.startsWith('https://')) {
        const link = document.createElement('a'); link.href = source.url; link.textContent = source.title || 'Open source';
        link.target = '_blank'; link.rel = 'noopener noreferrer'; row.appendChild(link);
      } else if (typeof source.filename === 'string') {
        const label = document.createElement('span'); label.textContent = `${source.filename} (private document)`;
        row.appendChild(label);
      } else {
        return;
      }
      if (source.snippet) { const snippet = document.createElement('small'); snippet.textContent = source.snippet; row.appendChild(snippet); }
      group.appendChild(row);
    });
    if (group.childElementCount > 1) messages.appendChild(group);
  };

  const appendSpeechButton = (answer, synthesizeOnRequest = false) => {
    if (!answer || !speechOutputConfigured) return;
    const group = document.createElement('div'); group.className = 'ai-message-actions';
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'button button--secondary'; button.textContent = 'Listen';
    const prepareSpeech = async (showPlayer) => {
      button.disabled = true; button.textContent = 'Preparing voice…';
      try {
        const response = await fetch(endpoints['speak-endpoint'], {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({ text: answer.slice(0, 1200) }),
        });
        if (!response.ok) throw new Error('Local speech is unavailable.');
        const objectUrl = URL.createObjectURL(await response.blob());
        if (showPlayer) {
          const player = document.createElement('audio');
          player.controls = true;
          player.preload = 'none';
          player.src = objectUrl;
          player.setAttribute('aria-label', 'Spoken AI response');
          player.addEventListener('ended', () => URL.revokeObjectURL(objectUrl), { once: true });
          group.appendChild(player);
          button.textContent = 'Audio ready';
          button.disabled = false;
          return;
        }
        const audio = new Audio(objectUrl);
        audio.addEventListener('ended', () => URL.revokeObjectURL(objectUrl), { once: true });
        await audio.play(); button.textContent = 'Playing';
        audio.addEventListener('ended', () => { button.textContent = 'Listen'; button.disabled = false; }, { once: true });
      } catch (_) { button.textContent = 'Voice unavailable'; button.disabled = false; }
    };
    button.addEventListener('click', () => prepareSpeech(false));
    group.appendChild(button); messages.appendChild(group);
    if (synthesizeOnRequest) prepareSpeech(true);
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

  const wantsAudioOutput = (prompt) => {
    const text = String(prompt || '').toLowerCase();
    return /\b(?:read (?:this|it|that|the answer)(?: aloud)?|read aloud|speak(?: it| this| your answer| the answer| your response| the response)?|say (?:it|this|that) out loud|voice response)\b/.test(text)
      || /(?:পড়ে শোনাও|পড়ে শোনাও|শুনিয়ে দাও|শুনিয়ে দাও|কথা বলে শোনাও|শুনতে চাই)/.test(text)
      || /\b(?:pore shonao|pore shunao|shuniye dao|voice e bolo)\b/.test(text);
  };

  const renderResult = async (result, prompt = '') => {
    const answer = result.answer || result.fallback || 'The assistant could not verify that request.';
    addMessage(answer);
    appendSpeechButton(answer, wantsAudioOutput(prompt));
    appendProducts(result.products);
    appendCategories(result);
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
    if (!consent) return false;
    if (consent.type === 'checkbox') return consent.checked;
    return String(consent.value).toLowerCase() !== 'false';
  };
  if (consent?.type === 'checkbox') {
    consent.addEventListener('change', () => {
      const enabled = consent.checked;
      consent.disabled = true;
      consentUpdate = (async () => {
        try {
          const response = await fetch(endpoints['consent-endpoint'], {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
            body: JSON.stringify({ enabled })
          });
          const result = await response.json();
          if (!response.ok || result.ok !== true) {
            throw new Error(result.answer || 'Your external AI preference could not be saved.');
          }
          if (externalConsentStatus) {
            externalConsentStatus.textContent = enabled
              ? 'External assistance is enabled for eligible questions when a provider and budget are configured.'
              : 'External assistance is turned off.';
          }
        } catch (error) {
          consent.checked = !enabled;
          if (externalConsentStatus) {
            externalConsentStatus.textContent = error.message || 'Your external AI preference could not be saved.';
          }
        } finally {
          consent.disabled = false;
        }
      })();
    });
  }

  const loadCustomerDocuments = async () => {
    if (!customerApiEnabled || !documentEndpoint || !documentList) return;
    try {
      const response = await fetch(documentEndpoint, {
        headers: { Accept: 'application/json' },
        cache: 'no-store'
      });
      const payload = await response.json();
      if (!response.ok || payload.success !== true || !Array.isArray(payload.data)) {
        throw new Error(payload.error?.message || 'Your private document library could not be loaded.');
      }
      documentList.replaceChildren();
      selectedDocumentIds = [];
      payload.data.forEach((item) => {
        const row = document.createElement('li');
        row.className = 'ai-document-list__item';
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = String(item.id);
        checkbox.addEventListener('change', () => {
            const checkedDocuments = Array.from(documentList.querySelectorAll('input[type="checkbox"]:checked'));
            if (checkedDocuments.length > 3) {
              checkbox.checked = false;
              documentStatus.textContent = 'Select up to three documents for chat.';
              return;
            }
            selectedDocumentIds = checkedDocuments.map((input) => Number(input.value));
            documentStatus.textContent = selectedDocumentIds.length
              ? `${selectedDocumentIds.length} document(s) selected. Their text stays on the local AI path.`
              : 'No documents selected for chat.';
        });
        const title = document.createElement('span');
        title.textContent = `${item.filename} · ${item.characters} characters`;
        label.append(checkbox, title);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'button button--quiet';
        remove.textContent = 'Delete';
        remove.setAttribute('aria-label', `Delete ${item.filename}`);
        remove.addEventListener('click', async () => {
          remove.disabled = true;
          try {
            const deleted = await fetch(`${documentEndpoint}/${encodeURIComponent(item.id)}`, {
              method: 'DELETE',
              headers: { 'X-CSRFToken': token, Accept: 'application/json' }
            });
            const result = await deleted.json();
            if (!deleted.ok || result.success !== true) {
              throw new Error(result.error?.message || 'The document could not be deleted.');
            }
            documentStatus.textContent = 'Document deleted from your private library.';
            await loadCustomerDocuments();
          } catch (error) {
            documentStatus.textContent = error.message || 'The document could not be deleted.';
            remove.disabled = false;
          }
        });
        row.append(label, remove);
        documentList.appendChild(row);
      });
      if (!payload.data.length) {
        const empty = document.createElement('li');
        empty.textContent = 'No documents uploaded yet.';
        documentList.appendChild(empty);
      }
    } catch (error) {
      documentStatus.textContent = error.message || 'Your private document library could not be loaded.';
    }
  };

  documentUploadForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const fileInput = document.getElementById('ai-document-file');
    const file = fileInput?.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      documentStatus.textContent = 'Documents must be no larger than 2 MB.';
      return;
    }
    const submitButton = documentUploadForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    documentStatus.textContent = 'Adding document to your private library…';
    try {
      const uploaded = await fetch(documentEndpoint, {
        method: 'POST',
        headers: { 'X-CSRFToken': token, Accept: 'application/json' },
        body: new FormData(documentUploadForm)
      });
      const result = await uploaded.json();
      if (!uploaded.ok || result.success !== true) {
        throw new Error(result.error?.message || 'The document could not be added.');
      }
      documentStatus.textContent = 'Document added. Select it to use its text in a local-only chat.';
      documentUploadForm.reset();
      await loadCustomerDocuments();
    } catch (error) {
      documentStatus.textContent = error.message || 'The document could not be added.';
    } finally {
      submitButton.disabled = false;
    }
  });
  loadCustomerDocuments();

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
    messages.querySelector('.ai-chat__welcome')?.remove();
    addMessage(finalPrompt, 'customer');
    const priorHistory = history.slice(-8);
    history.push({ role: 'user', content: finalPrompt.slice(0, 1500) });
    promptInput.value = '';
    attachedFiles = [];
    renderAttachments();
    const responseNode = addTypingIndicator();
    try {
      await consentUpdate;
      const useVersionedApi = customerApiEnabled && selectedDocumentIds.length > 0;
      const response = await fetch(useVersionedApi ? '/api/v1/ai/chat' : endpoints.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
        body: JSON.stringify(useVersionedApi ? {
          message: finalPrompt,
          history: priorHistory,
          document_ids: selectedDocumentIds.length ? selectedDocumentIds : undefined
        } : {
          prompt: finalPrompt,
          history: priorHistory,
          recent_products: recentProductSlugs.slice(0, 5),
          external_ai_consent: shouldUseExternalAi()
        })
      });
      let result = await response.json();
      if (useVersionedApi) {
        if (response.ok && result.success === true) {
          result = { ok: true, ...result.data };
        } else {
          result = { ok: false, answer: result.error?.message || 'The assistant is unavailable.' };
        }
      }
      responseNode.remove();
      if (Array.isArray(result.products)) {
        const slugs = [...new Set(result.products
          .filter((product) => product && typeof product.slug === 'string' && product.slug.trim())
          .map((product) => product.slug.trim()))].slice(0, 5);
        if (slugs.length || result.tools_used?.includes('search_products')) {
          recentProductSlugs.splice(0, recentProductSlugs.length, ...slugs);
        }
      }
      if (externalAssistanceNotice && Array.isArray(result.warnings)
          && result.warnings.includes('External specialist assistance was used for this response.')) {
        addMessage(externalAssistanceNotice);
      }
      const answer = await renderResult(result, prompt);
      history.push({ role: 'assistant', content: String(answer || '').slice(0, 1500) });
      if (history.length > 8) history.splice(0, history.length - 8);
    } catch (_) { responseNode.remove(); addMessage('The assistant is unavailable. You can use the regular catalog search.'); }
    finally { refreshCustomerUsage(); }
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

  const resetVoiceControls = (mode) => {
    if (mode === 'chat' && voiceToggle) {
      voiceToggle.classList.remove('is-recording');
      voiceToggle.textContent = '🎙️';
      voiceToggle.setAttribute('aria-label', 'Voice options');
    }
    if (mode === 'catalog' && recordButton) {
      recordButton.classList.remove('is-recording');
      recordButton.textContent = 'Start voice recording';
      recordButton.disabled = false;
    }
  };

  const startVoiceRecording = async (mode = 'chat') => {
    closeVoiceMenu();
    if (!voiceTranscriptionConfigured) {
      if (mode === 'catalog' && recordStatus) {
        recordStatus.textContent = 'Private voice transcription is not configured. You can type instead.';
      } else {
        addMessage('Private voice transcription is not configured. You can type your question instead.');
      }
      return;
    }
    if (activeVoiceRecorder) {
      if (activeVoiceMode === mode && activeVoiceRecorder.state === 'recording') {
        activeVoiceRecorder.stop();
      } else if (mode === 'catalog' && recordStatus) {
        recordStatus.textContent = 'Finish the current voice recording before starting another.';
      }
      return;
    }
    if (activeVoiceMode) {
      if (mode === 'catalog' && recordStatus) {
        recordStatus.textContent = 'Another voice input is starting. Please wait and try again.';
      }
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      const message = 'Voice recording is unavailable in this browser. You can type your question instead.';
      if (mode === 'catalog' && recordStatus) recordStatus.textContent = message;
      else addMessage(message);
      return;
    }

    activeVoiceMode = mode;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (activeVoiceMode !== mode) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      activeVoiceRecorder = recorder;
      activeVoiceStream = stream;
      if (mode === 'chat' && voiceToggle) {
        voiceToggle.classList.add('is-recording');
        voiceToggle.textContent = '■';
        voiceToggle.setAttribute('aria-label', 'Stop voice recording');
      }
      if (mode === 'catalog' && recordButton) {
        recordButton.classList.add('is-recording');
        recordButton.textContent = 'Stop and send';
      }
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());
        if (activeVoiceStream === stream) activeVoiceStream = null;
        if (activeVoiceRecorder === recorder) activeVoiceRecorder = null;
        if (activeVoiceMode === mode) activeVoiceMode = null;
        resetVoiceControls(mode);
        if (!blob.size) {
          const message = 'No voice clip was captured. Please try again or type your question.';
          if (mode === 'catalog' && recordStatus) recordStatus.textContent = message;
          else addMessage(message);
          return;
        }
        if (mode === 'catalog' && recordStatus) {
          recordStatus.textContent = 'Transcribing with the private local service…';
        }
        const succeeded = await runVoiceSearch(blob, 'voice-message.webm');
        if (mode === 'catalog' && recordStatus) {
        recordStatus.textContent = succeeded
            ? 'Voice transcribed by the private local service.'
            : 'Voice transcription is unavailable. You can type your question instead.';
        }
      };
      recorder.start();
      if (mode === 'catalog' && recordStatus) {
        recordStatus.textContent = 'Recording… select Stop and send when ready (maximum 15 seconds).';
      } else {
        addMessage('Recording with the private voice path… click the mic again to stop.', 'customer');
      }
      window.setTimeout(() => {
        if (activeVoiceRecorder === recorder && recorder.state === 'recording') recorder.stop();
      }, 15000);
    } catch (error) {
      if (activeVoiceMode === mode) activeVoiceMode = null;
      if (activeVoiceRecorder && activeVoiceRecorder.state !== 'inactive') {
        activeVoiceRecorder.onstop = null;
        try { activeVoiceRecorder.stop(); } catch (_) { /* Ignore an already-stopped recorder. */ }
      }
      activeVoiceRecorder = null;
      if (activeVoiceStream) {
        activeVoiceStream.getTracks().forEach((track) => track.stop());
        activeVoiceStream = null;
      }
      resetVoiceControls(mode);
      const message = error?.name === 'NotAllowedError'
        ? 'Microphone access was blocked. Allow microphone access or type your question.'
        : 'Microphone access is unavailable. You can type your question instead.';
      if (mode === 'catalog' && recordStatus) recordStatus.textContent = message;
      else addMessage(message);
    }
  };

  const startDirectTalkToAi = () => startVoiceRecording('chat');

  if (voiceRecordOption) {
    voiceRecordOption.addEventListener('click', startVoiceRecording);
  }

  if (voiceTalkOption) {
    voiceTalkOption.addEventListener('click', startDirectTalkToAi);
  }
  if (voiceForm && recordButton && recordStatus) {
    voiceForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!voiceTranscriptionConfigured) {
        recordStatus.textContent = 'Private voice transcription is not configured. You can type instead.';
        return;
      }
      if (!voiceForm.elements.audio.files.length) { recordStatus.textContent = 'Choose a voice recording or use Start voice recording.'; return; }
      submitForm(voiceForm, endpoints['voice-endpoint'], 'upload');
    });
    recordButton.addEventListener('click', () => startVoiceRecording('catalog'));
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
