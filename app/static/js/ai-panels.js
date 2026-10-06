(() => {
  const token = document.getElementById('ai-csrf')?.value;
  const show = (element, result) => {
    element.replaceChildren();
    const answer = document.createElement('p');
    answer.textContent = result.answer || 'No verified data is available.';
    element.appendChild(answer);
    const data = result.suggestion || result.quality || result.similar_listings || result.data;
    if (data && (Array.isArray(data) ? data.length : Object.keys(data).length)) {
      const pre = document.createElement('pre');
      pre.className = 'ai-result__data';
      pre.textContent = JSON.stringify(data, null, 2);
      element.appendChild(pre);
    }
    if (result.fallback) {
      const note = document.createElement('small'); note.textContent = result.fallback; element.appendChild(note);
    }
  };
  const post = async (url, body) => {
    const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token}, body: JSON.stringify(body)});
    const result = await response.json();
    if (!response.ok && !result.answer) throw new Error('The assistant request failed.');
    return result;
  };
  const suggest = document.getElementById('seller-ai-suggest-form');
  if (suggest) suggest.addEventListener('submit', async (event) => {
    event.preventDefault();
    const resultNode = document.getElementById('seller-ai-suggest-result');
    const body = {title: document.getElementById('seller-ai-title').value, description: document.getElementById('seller-ai-description').value};
    const productId = document.getElementById('seller-ai-product').value;
    if (productId) body.product_id = Number(productId);
    resultNode.textContent = 'Preparing a suggestion…';
    try { show(resultNode, await post(document.getElementById('seller-ai-suggest-endpoint').value, body)); }
    catch (error) { resultNode.textContent = error.message; }
  });
  const sellerQuery = document.getElementById('seller-ai-query-form');
  if (sellerQuery) sellerQuery.addEventListener('submit', async (event) => {
    event.preventDefault();
    const node = document.getElementById('seller-ai-query-result'); node.textContent = 'Reviewing your store data…';
    try { show(node, await post(document.getElementById('seller-ai-query-endpoint').value, {prompt: document.getElementById('seller-ai-query').value})); }
    catch (error) { node.textContent = error.message; }
  });
  const sellerPrice = document.getElementById('seller-ai-price-form');
  if (sellerPrice) sellerPrice.addEventListener('submit', async (event) => {
    event.preventDefault();
    const node = document.getElementById('seller-ai-price-result'); node.textContent = 'Comparing current price data…';
    const competitor = document.getElementById('seller-ai-competitor').value;
    const body = {product_id: Number(document.getElementById('seller-ai-price-product').value)};
    if (competitor) body.competitor_price = Number(competitor);
    try { show(node, await post(document.getElementById('seller-ai-price-endpoint').value, body)); }
    catch (error) { node.textContent = error.message; }
  });
  const adminForm = document.getElementById('admin-ai-query-form');
  if (adminForm) {
    const input = document.getElementById('admin-ai-query');
    const send = async () => {
      const node = document.getElementById('admin-ai-result'); node.textContent = 'Reading verified marketplace data…';
      try { show(node, await post(document.getElementById('admin-ai-query-endpoint').value, {prompt: input.value})); }
      catch (error) { node.textContent = error.message; }
    };
    adminForm.addEventListener('submit', (event) => { event.preventDefault(); send(); });
    document.querySelectorAll('[data-ai-query]').forEach((button) => button.addEventListener('click', () => {
      input.value = button.dataset.aiQuery || ''; send();
    }));
  }
})();
