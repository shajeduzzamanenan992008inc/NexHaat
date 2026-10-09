(() => {
  const root = document.querySelector('.ai-builder');
  if (!root) return;
  const token = document.getElementById('ai-builder-csrf')?.value || '';
  const resultNode = document.getElementById('ai-builder-result');
  const projectList = document.getElementById('ai-builder-project-list');
  const detailTitle = document.getElementById('ai-builder-detail-title');
  const detailStatus = document.getElementById('ai-builder-detail-status');
  const detailContent = document.getElementById('ai-builder-detail-content');
  const actions = document.getElementById('ai-builder-actions');
  const patchActions = document.getElementById('ai-builder-patch-actions');
  const lessonFormWrap = document.getElementById('ai-builder-lesson-form-wrap');
  let selectedProject = null;
  let selectedPatch = null;

  const showMessage = (message, data) => {
    resultNode.replaceChildren();
    const paragraph = document.createElement('p');
    paragraph.textContent = message || 'Request finished.';
    resultNode.appendChild(paragraph);
    if (data !== undefined) {
      const pre = document.createElement('pre');
      pre.className = 'ai-builder__pre';
      pre.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
      resultNode.appendChild(pre);
    }
  };

  const send = async (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    headers.set('X-CSRFToken', token);
    headers.set('Accept', 'application/json');
    if (options.body && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    const response = await fetch(url, {...options, headers, credentials: 'same-origin'});
    if (response.status === 204) return {ok: true};
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error || payload.message || 'Builder request failed.');
      error.payload = payload;
      throw error;
    }
    return payload;
  };

  const button = (label, callback, className = 'button button--quiet') => {
    const element = document.createElement('button');
    element.type = 'button';
    element.className = className;
    element.textContent = label;
    element.addEventListener('click', callback);
    return element;
  };

  const renderProjectList = (projects) => {
    projectList.replaceChildren();
    if (!projects.length) {
      const empty = document.createElement('li');
      empty.className = 'muted';
      empty.textContent = 'No project has been saved yet.';
      projectList.appendChild(empty);
      return;
    }
    projects.forEach((project) => {
      const item = document.createElement('li');
      item.appendChild(button(project.name, () => loadProject(project.id), 'ai-builder__project-button'));
      projectList.appendChild(item);
    });
  };

  const refreshProjects = async () => {
    const data = await send(root.dataset.projectsUrl);
    renderProjectList(data.projects || []);
  };

  const renderFindings = (findings) => {
    const heading = document.createElement('h3');
    heading.textContent = 'Guardian findings';
    detailContent.appendChild(heading);
    if (!findings || !findings.length) {
      const empty = document.createElement('p');
      empty.textContent = 'No open findings were returned by the latest scan.';
      detailContent.appendChild(empty);
      return;
    }
    const list = document.createElement('ul');
    list.className = 'ai-builder__findings';
    findings.forEach((finding) => {
      const item = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = finding.severity.toUpperCase() + ' · ' + finding.rule_id;
      const description = document.createElement('p');
      description.textContent = finding.file_path + ':' + finding.line_number + ' — ' + finding.summary;
      item.append(title, description);
      if (!finding.confirmed) {
        item.appendChild(button('Confirm with review evidence', async () => {
          const evidence = window.prompt('Describe how this risk was reviewed or reproduced.');
          if (!evidence) return;
          try {
            await send('/admin/ai-builder/findings/' + finding.id, {
              method: 'PATCH', body: JSON.stringify({confirm: true, evidence}),
            });
            await loadProject(selectedProject.id);
            showMessage('Finding confirmation recorded.');
          } catch (error) { showMessage(error.message); }
        }));
      }
      item.appendChild(button('Mark reviewed', async () => {
        try {
          await send('/admin/ai-builder/findings/' + finding.id, {
            method: 'PATCH', body: JSON.stringify({status: 'acknowledged'}),
          });
          await loadProject(selectedProject.id);
          showMessage('Finding review status updated.');
        } catch (error) { showMessage(error.message); }
      }));
      list.appendChild(item);
    });
    detailContent.appendChild(list);
  };

  const renderPatch = (patch) => {
    selectedPatch = patch;
    patchActions.replaceChildren();
    patchActions.hidden = false;
    const title = document.createElement('h3');
    title.textContent = 'Patch candidate · ' + patch.status + ' · tests: ' + patch.test_status;
    const diff = document.createElement('pre');
    diff.className = 'ai-builder__pre';
    diff.textContent = patch.diff || '';
    patchActions.append(title, diff);
    if (patch.test_output) {
      const note = document.createElement('p');
      note.textContent = patch.test_output;
      patchActions.appendChild(note);
    }
    if (patch.status !== 'rejected') {
      patchActions.appendChild(button('Run isolated tests', async () => {
        try {
          const response = await send('/admin/ai-builder/patches/' + patch.id + '/test', {method: 'POST'});
          renderPatch(response.patch);
          showMessage(response.patch.test_output);
        } catch (error) {
          if (error.payload?.patch) renderPatch(error.payload.patch);
          showMessage(error.message);
        }
      }));
    }
    if (!['approved', 'rejected'].includes(patch.status)) {
      patchActions.appendChild(button('Reject patch candidate', async () => {
        try {
          const response = await send('/admin/ai-builder/patches/' + patch.id + '/reject', {method: 'POST'});
          renderPatch(response.patch);
          showMessage('Patch candidate rejected.');
        } catch (error) { showMessage(error.message); }
      }));
    }
    if (patch.status === 'tested' && patch.test_status === 'passed') {
      patchActions.appendChild(button('Approve patch', async () => {
        try {
          const response = await send('/admin/ai-builder/patches/' + patch.id + '/approve', {method: 'POST'});
          renderPatch(response.patch);
          showMessage('Patch approval recorded. Applying or exporting still requires an explicit action.');
        } catch (error) { showMessage(error.message); }
      }, 'button'));
    }
    if (patch.status === 'approved') {
      patchActions.appendChild(button('Apply to saved project', async () => {
        try {
          const response = await send('/admin/ai-builder/patches/' + patch.id + '/apply', {method: 'POST'});
          showMessage('Approved patch applied to the saved project.');
          await loadProject(response.project.id);
        } catch (error) { showMessage(error.message); }
      }, 'button'));
      const exportLink = document.createElement('a');
      exportLink.className = 'button button--secondary';
      exportLink.href = '/admin/ai-builder/patches/' + patch.id + '/export';
      exportLink.textContent = 'Export approved patch';
      patchActions.appendChild(exportLink);
    }
    if (patch.test_status === 'passed' && patch.status !== 'rejected') lessonFormWrap.hidden = false;
  };

  const renderLessons = (lessons) => {
    const node = document.getElementById('ai-builder-lessons');
    node.replaceChildren();
    const heading = document.createElement('h3');
    heading.textContent = 'Sanitized lessons awaiting or in Admin review';
    node.appendChild(heading);
    (lessons || []).forEach((lesson) => {
      const item = document.createElement('article');
      item.className = 'ai-builder__lesson';
      const title = document.createElement('h4');
      title.textContent = lesson.title + ' · ' + lesson.status;
      const content = document.createElement('p');
      content.textContent = lesson.content;
      item.append(title, content);
      if (lesson.status === 'proposed') {
        item.appendChild(button('Approve for private Admin retrieval', async () => {
          try {
            await send('/admin/ai-builder/lessons/' + lesson.id + '/review', {
              method: 'POST', body: JSON.stringify({decision: 'approve'}),
            });
            await loadLessons();
            showMessage('Lesson approved for private Admin retrieval.');
          } catch (error) { showMessage(error.message); }
        }, 'button'));
        item.appendChild(button('Reject lesson', async () => {
          try {
            await send('/admin/ai-builder/lessons/' + lesson.id + '/review', {
              method: 'POST', body: JSON.stringify({decision: 'reject'}),
            });
            await loadLessons();
            showMessage('Lesson rejected.');
          } catch (error) { showMessage(error.message); }
        }));
      }
      node.appendChild(item);
    });
  };

  const loadLessons = async () => {
    const data = await send(root.dataset.lessonsUrl);
    renderLessons(data.lessons || []);
  };

  const loadProject = async (projectId) => {
    try {
      const data = await send(root.dataset.projectsUrl + '/' + encodeURIComponent(projectId));
      selectedProject = data.project;
      detailTitle.textContent = data.project.name;
      detailStatus.textContent = data.project.project_type + ' · ' + data.project.source_sha256;
      detailContent.replaceChildren();
      actions.hidden = false;
      const filesTitle = document.createElement('h3');
      filesTitle.textContent = 'Saved project files';
      detailContent.appendChild(filesTitle);
      (data.project.files || []).forEach((file) => {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = file.path;
        const pre = document.createElement('pre');
        pre.className = 'ai-builder__pre';
        pre.textContent = file.content;
        details.append(summary, pre);
        detailContent.appendChild(details);
      });
      const consent = document.createElement('label');
      consent.className = 'ai-builder__check';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = Boolean(data.project.external_code_consent);
      checkbox.disabled = document.getElementById('ai-builder-project-external').disabled;
      checkbox.setAttribute('aria-label', 'Project-level external source consent');
      checkbox.addEventListener('change', async () => {
        try {
          await send(root.dataset.projectsUrl + '/' + encodeURIComponent(projectId), {
            method: 'PATCH',
            body: JSON.stringify({external_code_consent: checkbox.checked}),
          });
          showMessage('Project-level external code consent updated.');
        } catch (error) {
          checkbox.checked = !checkbox.checked;
          showMessage(error.message);
        }
      });
      const consentText = document.createElement('span');
      consentText.textContent = 'Project-level external code consent';
      consent.append(checkbox, consentText);
      detailContent.appendChild(consent);
      renderFindings(data.findings || []);
      const scanTitle = document.createElement('h3');
      scanTitle.textContent = 'Recent Guardian scans';
      detailContent.appendChild(scanTitle);
      (data.scans || []).forEach((scan) => {
        const item = document.createElement('p');
        item.textContent = scan.trigger + ' · ' + scan.status + ' · ' + scan.result_summary;
        detailContent.appendChild(item);
      });
      const patchesTitle = document.createElement('h3');
      patchesTitle.textContent = 'Patch candidates';
      detailContent.appendChild(patchesTitle);
      (data.patches || []).forEach((patch) => {
        detailContent.appendChild(button(
          patch.status + ' · tests ' + patch.test_status + ' · ' + patch.id.slice(0, 8),
          () => renderPatch(patch),
        ));
      });
      const exportProject = document.getElementById('ai-builder-export-project');
      exportProject.href = '/admin/ai-builder/projects/' + encodeURIComponent(projectId) + '/export';
      exportProject.hidden = false;
      patchActions.hidden = true;
      lessonFormWrap.hidden = true;
    } catch (error) {
      showMessage(error.message);
    }
  };

  document.getElementById('ai-builder-create-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      name: document.getElementById('ai-builder-name').value,
      project_type: document.getElementById('ai-builder-type').value,
      description: document.getElementById('ai-builder-description').value,
      persist: document.getElementById('ai-builder-persist').checked,
      external_code_consent: document.getElementById('ai-builder-project-external').checked,
    };
    try {
      const data = await send(root.dataset.createProjectUrl, {method: 'POST', body: JSON.stringify(payload)});
      showMessage(data.message || data.generation || 'Project starter created.', data.project.files);
      if (data.persisted) {
        await refreshProjects();
        await loadProject(data.project.id);
      }
      form.reset();
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-input-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form);
    body.set('allow_external_code', String(document.getElementById('ai-builder-input-code-consent').checked));
    body.set('allow_external_media', String(document.getElementById('ai-builder-input-media-consent').checked));
    showMessage('Analyzing transient attachment…');
    try {
      const data = await send(root.dataset.analyzeInputUrl, {method: 'POST', body});
      showMessage('Attachment analysis complete. Source persisted: ' + data.source_persisted, data.job?.result);
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-session-media-consent')?.addEventListener('change', async (event) => {
    try {
      await send(root.dataset.mediaConsentUrl, {
        method: 'POST', body: JSON.stringify({enabled: event.currentTarget.checked}),
      });
      showMessage('Browser-session media consent updated.');
    } catch (error) {
      event.currentTarget.checked = !event.currentTarget.checked;
      showMessage(error.message);
    }
  });

  document.getElementById('ai-builder-refresh')?.addEventListener('click', () => {
    refreshProjects().catch((error) => showMessage(error.message));
  });
  projectList?.addEventListener('click', (event) => {
    const target = event.target.closest('[data-project-id]');
    if (target) loadProject(target.dataset.projectId);
  });

  document.getElementById('ai-builder-analyze-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedProject) return;
    try {
      const data = await send('/admin/ai-builder/projects/' + encodeURIComponent(selectedProject.id) + '/analyze', {
        method: 'POST',
        body: JSON.stringify({
          prompt: document.getElementById('ai-builder-analysis-prompt').value,
          allow_external_code: document.getElementById('ai-builder-analysis-external').checked,
        }),
      });
      showMessage('Project analysis ' + data.job.status + '.', data.job.result);
    } catch (error) { showMessage(error.message, error.payload?.job?.result); }
  });

  document.getElementById('ai-builder-patch-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedProject) return;
    try {
      const data = await send('/admin/ai-builder/projects/' + encodeURIComponent(selectedProject.id) + '/patches', {
        method: 'POST',
        body: JSON.stringify({
          prompt: document.getElementById('ai-builder-patch-prompt').value,
          allow_external_code: document.getElementById('ai-builder-patch-external').checked,
        }),
      });
      showMessage('Patch candidate saved for review.');
      await loadProject(selectedProject.id);
      renderPatch(data.patch);
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-manual-patch-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedProject) return;
    let changes;
    try {
      changes = JSON.parse(document.getElementById('ai-builder-manual-changes').value);
    } catch (_error) {
      showMessage('Enter valid JSON for the manual patch changes.');
      return;
    }
    try {
      const data = await send('/admin/ai-builder/projects/' + encodeURIComponent(selectedProject.id) + '/patches', {
        method: 'POST',
        body: JSON.stringify({changes}),
      });
      await loadProject(selectedProject.id);
      renderPatch(data.patch);
      showMessage('Manual patch candidate saved for review.');
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-scan')?.addEventListener('click', async () => {
    if (!selectedProject) return;
    try {
      const data = await send('/admin/ai-builder/projects/' + encodeURIComponent(selectedProject.id) + '/scans', {
        method: 'POST', body: JSON.stringify({trigger: 'manual'}),
      });
      await loadProject(selectedProject.id);
      showMessage(data.scan.result_summary, data.scan.findings);
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-delete-project')?.addEventListener('click', async () => {
    if (!selectedProject || !window.confirm('Delete this saved project and its Builder records?')) return;
    try {
      await send(root.dataset.projectsUrl + '/' + encodeURIComponent(selectedProject.id), {method: 'DELETE'});
      selectedProject = null;
      detailTitle.textContent = 'Select a project';
      detailStatus.textContent = 'Choose one of your saved projects to review its files and scans.';
      detailContent.replaceChildren();
      actions.hidden = true;
      document.getElementById('ai-builder-export-project').hidden = true;
      await refreshProjects();
      showMessage('Project deleted.');
    } catch (error) { showMessage(error.message); }
  });

  document.getElementById('ai-builder-lesson-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedPatch || !selectedProject) return;
    try {
      await send('/admin/ai-builder/patches/' + selectedPatch.id + '/lessons', {
        method: 'POST',
        body: JSON.stringify({
          title: document.getElementById('ai-builder-lesson-title').value,
          content: document.getElementById('ai-builder-lesson-content').value,
        }),
      });
      await loadLessons();
      showMessage('Lesson submitted for a separate Admin approval.');
    } catch (error) { showMessage(error.message); }
  });

  refreshProjects().catch((error) => showMessage(error.message));
  loadLessons().catch((error) => showMessage(error.message));
})();
