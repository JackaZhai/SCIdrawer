/* ============================================
   Integrations (Edit-Banana + chat providers + custom API host)
   Kept separate to avoid destabilizing the main app.js.
   ============================================ */

(function () {
  function $(id) {
    return document.getElementById(id);
  }

  function setText(el, text) {
    if (!el) return;
    el.textContent = text;
  }

  function setEditBananaStatus(text, type) {
    const el = $('editBananaStatusText');
    if (!el) return;
    el.textContent = text;
    el.style.color = type === 'error'
      ? 'var(--color-danger)'
      : type === 'success'
        ? 'var(--color-success)'
        : 'var(--color-text-tertiary)';
  }

  function formatApiError(data, fallback) {
    if (!data) return fallback;
    const base = data.error || fallback;
    const details = data.details ? String(data.details).trim() : '';
    if (!details) return base;
    const short = details.length > 400 ? `${details.slice(0, 400)}...` : details;
    return `${base}\n${short}`;
  }

  async function loadEditBananaStatus() {
    try {
      setEditBananaStatus('检查中...');
      const res = await fetch('/api/edit-banana/status', { method: 'GET' });
      const data = await res.json();
      if (!res.ok) {
        setEditBananaStatus(data.error || '检查失败', 'error');
        return;
      }
      if (!data.rootExists) {
        setEditBananaStatus('未找到 Edit-Banana（检查 integrations/Edit-Banana 或设置 EDIT_BANANA_ROOT）', 'error');
        return;
      }
      if (!data.configExists) {
        setEditBananaStatus('缺少 Edit-Banana 配置：config/config.yaml', 'error');
        return;
      }
      if (!data.torchAvailable) {
        setEditBananaStatus('缺少依赖：torch（需要安装 PyTorch）', 'error');
        return;
      }
      if (!data.cv2Available) {
        setEditBananaStatus('缺少依赖：opencv-python(-headless)', 'error');
        return;
      }
      if (!data.textModuleAvailable) {
        const withTextEl = $('editBananaWithText');
        if (withTextEl) {
          withTextEl.checked = false;
          withTextEl.disabled = true;
        }
        setEditBananaStatus(
          data.cudaAvailable
            ? '环境就绪（CUDA 可用，OCR文字识别模块不可用，将仅图形转换）'
            : '环境就绪（CPU 模式，OCR文字识别模块不可用，将仅图形转换）',
          'success'
        );
        return;
      }
      const withTextEl = $('editBananaWithText');
      if (withTextEl) withTextEl.disabled = false;
      setEditBananaStatus(data.cudaAvailable ? '环境就绪（CUDA 可用）' : '环境就绪（CPU 模式，可能较慢）', 'success');
    } catch (e) {
      setEditBananaStatus(`检查失败: ${e.message}`, 'error');
    }
  }

  async function convertWithEditBanana() {
    const fileInput = $('editBananaFileInput');
    const file = fileInput && fileInput.files ? fileInput.files[0] : null;
    if (!file) {
      setEditBananaStatus('请先选择图片文件', 'error');
      return;
    }

    const withTextEl = $('editBananaWithText');
    const withRefEl = $('editBananaWithRefinement');
    const withText = withTextEl ? withTextEl.checked : true;
    const withRefinement = withRefEl ? withRefEl.checked : false;

    const form = new FormData();
    form.append('file', file);
    form.append('withText', withText ? 'true' : 'false');
    form.append('withRefinement', withRefinement ? 'true' : 'false');

    const btn = $('editBananaConvertBtn');
    try {
      if (btn) btn.disabled = true;
      setEditBananaStatus('转换中...（首次加载模型可能较慢）');

      const res = await fetch('/api/edit-banana/convert', { method: 'POST', body: form });
      if (!res.ok) {
        let err = '转换失败';
        try {
          const data = await res.json();
          err = formatApiError(data, err);
        } catch {
          err = await res.text();
        }
        setEditBananaStatus(err, 'error');
        return;
      }

      const blob = await res.blob();
      const cd = res.headers.get('content-disposition') || '';
      let filename = (file.name || 'output').replace(/\.[^/.]+$/, '') + '.drawio';
      const match = cd.match(/filename\*?=(?:UTF-8''|\"?)([^\";]+)/i);
      if (match && match[1]) {
        try {
          filename = decodeURIComponent(match[1].replace(/\"/g, ''));
        } catch {
          filename = match[1].replace(/\"/g, '');
        }
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setEditBananaStatus('转换完成，已开始下载。', 'success');
    } catch (e) {
      setEditBananaStatus(`转换失败: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function bindEditBananaFileLabel() {
    const input = $('editBananaFileInput');
    const fileNameEl = $('editBananaFileName');
    if (!input || !fileNameEl) return;

    const updateName = () => {
      const file = input.files && input.files[0] ? input.files[0] : null;
      fileNameEl.textContent = file ? file.name : '未选择文件';
    };
    input.addEventListener('change', updateName);
    updateName();
  }

  function applyCustomApiHostUI() {
    const apiHostSelect = $('apiHostSelect');
    const apiHostCustomInput = $('apiHostCustomInput');
    if (!apiHostSelect) return;

    const savedHost = localStorage.getItem('apiHost') || 'https://grsaiapi.com';
    const optionValues = Array.from(apiHostSelect.options || []).map(o => o.value);

    if (optionValues.includes(savedHost)) {
      apiHostSelect.value = savedHost;
      if (apiHostCustomInput) apiHostCustomInput.value = '';
    } else {
      apiHostSelect.value = 'custom';
      if (apiHostCustomInput) apiHostCustomInput.value = savedHost;
    }

    const effectiveHost = apiHostSelect.value === 'custom'
      ? ((apiHostCustomInput && apiHostCustomInput.value) || savedHost)
      : savedHost;

    if (window.APIService && window.APIService.setApiHost) {
      window.APIService.setApiHost(effectiveHost);
    }
  }

  function applyChatProviderUI() {
    const sel = $('chatProviderSelect');
    const keyInput = $('chatApiKeyInput');
    if (sel) {
      const provider = localStorage.getItem('chatProvider') || 'grsai';
      sel.value = provider;
      if (window.APIService && window.APIService.setChatProvider) {
        window.APIService.setChatProvider(provider);
      }
    }
    if (keyInput) {
      const key = localStorage.getItem('chatApiKey') || '';
      keyInput.value = key;
      if (window.APIService && window.APIService.setChatApiKey) {
        window.APIService.setChatApiKey(key);
      }
    }
  }

  function bindIntegrationEvents() {
    const checkBtn = $('editBananaCheckBtn');
    if (checkBtn) checkBtn.addEventListener('click', (e) => { e.preventDefault(); loadEditBananaStatus(); });

    const convertBtn = $('editBananaConvertBtn');
    if (convertBtn) convertBtn.addEventListener('click', (e) => { e.preventDefault(); convertWithEditBanana(); });

    const apiHostSelect = $('apiHostSelect');
    const apiHostCustomInput = $('apiHostCustomInput');
    if (apiHostSelect) apiHostSelect.addEventListener('change', () => {
      if (apiHostSelect.value !== 'custom') {
        localStorage.setItem('apiHost', apiHostSelect.value);
      } else {
        const v = (apiHostCustomInput && apiHostCustomInput.value || '').trim();
        if (v) localStorage.setItem('apiHost', v);
      }
      applyCustomApiHostUI();
    });
    if (apiHostCustomInput) apiHostCustomInput.addEventListener('blur', () => {
      const v = (apiHostCustomInput.value || '').trim();
      if (v) localStorage.setItem('apiHost', v);
      applyCustomApiHostUI();
    });

    const chatProviderSelect = $('chatProviderSelect');
    if (chatProviderSelect) chatProviderSelect.addEventListener('change', () => {
      localStorage.setItem('chatProvider', chatProviderSelect.value);
      if (window.APIService && window.APIService.setChatProvider) {
        window.APIService.setChatProvider(chatProviderSelect.value);
      }
    });

    const chatApiKeyInput = $('chatApiKeyInput');
    if (chatApiKeyInput) chatApiKeyInput.addEventListener('blur', () => {
      const v = (chatApiKeyInput.value || '').trim();
      localStorage.setItem('chatApiKey', v);
      if (window.APIService && window.APIService.setChatApiKey) {
        window.APIService.setChatApiKey(v);
      }
    });

    // Update title and preload integration status when navigating to edit-banana page
    document.querySelectorAll('.nav-item[data-page="edit-banana"]').forEach((el) => {
      el.addEventListener('click', () => {
        const titleEl = $('pageTitle');
        setText(titleEl, 'Edit Banana');
        // Preload status
        loadEditBananaStatus();
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    applyCustomApiHostUI();
    applyChatProviderUI();
    bindIntegrationEvents();
    bindEditBananaFileLabel();
  });
})();
