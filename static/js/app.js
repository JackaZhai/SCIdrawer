/* ============================================
   SCIdrawer - 主应用脚本
   ============================================ */

// 应用状态管理
const AppState = {
    currentPage: 'dashboard',
    theme: localStorage.getItem('theme') || 'dark',
    hasKey: false,
    keyStore: null,
    apiHost: '',
    activeBaseUrl: '',
    isLoading: false,
    currentGeneration: null,
    notifications: [],
    referenceImages: []
};

// DOM 元素缓存
const DOM = {
    // 侧边栏
    sidebar: document.querySelector('.sidebar'),
    navItems: document.querySelectorAll('.nav-item'),

    // 顶部栏
    pageTitle: document.getElementById('pageTitle'),
    themeToggle: document.getElementById('themeToggle'),

    // 页面容器
    pageSections: document.querySelectorAll('.page-section'),

    // 仪表盘
    totalImages: document.getElementById('totalImages'),
    totalChats: document.getElementById('totalChats'),
    apiUsage: document.getElementById('apiUsage'),
    refreshActivities: document.getElementById('refreshActivities'),
    activitiesList: document.getElementById('activitiesList'),

    // 图像生成
    promptInput: document.getElementById('promptInput'),
    generationTextProviderSelect: document.getElementById('generationTextProviderSelect'),
    generationImageProviderSelect: document.getElementById('generationImageProviderSelect'),
    generationTextModelSelect: document.getElementById('generationTextModelSelect'),
    generationImageModelSelect: document.getElementById('generationImageModelSelect'),
    generationExpModeSelect: document.getElementById('generationExpModeSelect'),
    generationRetrievalSelect: document.getElementById('generationRetrievalSelect'),
    generationCriticRoundsInput: document.getElementById('generationCriticRoundsInput'),
    generationCriticEnabledCheck: document.getElementById('generationCriticEnabledCheck'),
    generationEvalEnabledCheck: document.getElementById('generationEvalEnabledCheck'),
    generationModelSection: document.getElementById('generationModelSection'),
    referenceImagesInput: document.getElementById('referenceImagesInput'),
    referenceImagesList: document.getElementById('referenceImagesList'),
    generateBtn: document.getElementById('generateBtn'),
    resetFormBtn: document.getElementById('resetFormBtn'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    paperStageTitle: document.getElementById('paperStageTitle'),
    paperStageChip: document.getElementById('paperStageChip'),
    paperStageMessage: document.getElementById('paperStageMessage'),
    paperTaskIdText: document.getElementById('paperTaskIdText'),
    paperStageList: document.getElementById('paperStageList'),
    paperStageItems: document.querySelectorAll('.paper-stage-item'),
    generationWorkflowSummary: document.getElementById('generationWorkflowSummary'),
    downloadBtn: document.getElementById('downloadBtn'),
    clearBtn: document.getElementById('clearBtn'),

    // API 密钥
    currentKeyStatus: document.getElementById('currentKeyStatus'),
    lastUsedTime: document.getElementById('lastUsedTime'),
    newApiKey: document.getElementById('newApiKey'),
    keyName: document.getElementById('keyName'),
    addKeyBtn: document.getElementById('addKeyBtn'),
    testKeyBtn: document.getElementById('testKeyBtn'),
    refreshKeysBtn: document.getElementById('refreshKeysBtn'),
    keysTableBody: document.getElementById('keysTableBody'),

    // 仪表盘
    creditsBalance: document.getElementById('creditsBalance'),
    apiKeyStatusText: document.getElementById('apiKeyStatus'),
    apiHostDisplay: document.getElementById('apiHostDisplay'),
    refreshModelStatus: document.getElementById('refreshModelStatus'),
    modelStatusList: document.getElementById('modelStatusList'),

    // 设置
    timeoutSelect: document.getElementById('timeoutSelect'),
    retrySelect: document.getElementById('retrySelect'),

};

// 页面配置
const PageConfig = {
    dashboard: {
        title: '工作台'
    },
    'image-generation': {
        title: '图像生成'
    },

    'api-keys': {
        title: 'API 设置'
    },
    'edit-banana': {
        title: 'Edit Banana'
    },
    settings: {
        title: '系统设置'
    },
};

const PAPER_STAGE_LABELS = {
    queued: '排队',
    initializing: '初始化',
    loading_agents: '加载 Agent',
    processing: '生成推理',
    processing_retriever: '检索参考',
    processing_planner: '规划内容',
    processing_stylist: '风格优化',
    processing_visualizer: '执行生图',
    processing_critic: '批评迭代',
    processing_eval: '评估整理',
    saving: '写入结果',
    completed: '完成',
    failed: '失败'
};

const PAPER_STAGE_ORDER = [
    'queued',
    'initializing',
    'loading_agents',
    'processing',
    'processing_retriever',
    'processing_planner',
    'processing_stylist',
    'processing_visualizer',
    'processing_critic',
    'processing_eval',
    'saving',
    'completed'
];

const PROVIDER_MODEL_CATALOG = {
    grsai: {
        text: ['gemini-3.1-pro', 'gemini-3-pro', 'gemini-2.5-pro'],
        image: ['sora-image', 'nano-banana-pro', 'gpt-image-1.5', 'nano-banana-fast', 'nano-banana-pro-vt']
    },
    openai: {
        text: ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1'],
        image: ['gpt-image-1']
    },
    deepseek: {
        text: ['deepseek-chat', 'deepseek-reasoner'],
        image: ['gpt-image-1']
    },
    anthropic: {
        text: ['claude-3-5-sonnet-latest', 'claude-3-7-sonnet-latest'],
        image: ['gpt-image-1']
    },
    google: {
        text: ['gemini-2.5-pro', 'gemini-2.5-flash'],
        image: ['gemini-3-pro-image-preview']
    },
    openrouter: {
        text: ['openai/gpt-4o-mini', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.5-pro'],
        image: ['gpt-image-1']
    }
};

const PROVIDER_BASE_URL_DEFAULTS = {
    grsai: 'https://grsaiapi.com/v1',
    openai: 'https://api.openai.com/v1',
    deepseek: 'https://api.deepseek.com/v1',
    openrouter: 'https://openrouter.ai/api/v1',
    anthropic: 'https://api.anthropic.com',
    google: ''
};

const ALLOWED_TEXT_MODELS = new Set([
    'gemini-3.1-pro',
    'gemini-3-pro',
    'gemini-2.5-pro'
]);

const ALLOWED_IMAGE_MODELS = new Set([
    'sora-image',
    'nano-banana-pro',
    'gpt-image-1.5',
    'nano-banana-fast',
    'nano-banana-pro-vt'
]);

function normalizeProviderName(provider) {
    const value = String(provider || '').trim().toLowerCase();
    if (value === 'chatgpt' || value === 'gpt') return 'openai';
    if (value === 'claude') return 'anthropic';
    if (value === 'gemini') return 'google';
    if (value === 'openruter') return 'openrouter';
    return value || 'grsai';
}

function uniq(arr) {
    return Array.from(new Set((arr || []).filter(Boolean)));
}

function loadGenerationModelPrefs() {
    try {
        return JSON.parse(localStorage.getItem('generationModelPrefs') || '{}') || {};
    } catch {
        return {};
    }
}

function saveGenerationModelPrefs(prefs) {
    localStorage.setItem('generationModelPrefs', JSON.stringify(prefs || {}));
}

function persistLaneModelSelection(lane, provider, model) {
    if (!lane || !provider) return;
    const prefs = loadGenerationModelPrefs();
    prefs[lane] = prefs[lane] || {};
    prefs[lane][provider] = model || '';
    saveGenerationModelPrefs(prefs);
}

function getActiveProvidersFromStore(store) {
    const keys = (store && Array.isArray(store.keys)) ? store.keys : [];
    const providers = new Set();
    keys.forEach((item) => {
        if (item && item.isActive && item.provider) {
            providers.add(String(item.provider).trim().toLowerCase());
        }
    });
    if (providers.size === 0) {
        providers.add('grsai');
    }
    return Array.from(providers);
}

function getProviderBaseUrlFromStore(provider, store) {
    const normalized = normalizeProviderName(provider);
    const keyStore = store || AppState.keyStore || {};
    const keys = Array.isArray(keyStore.keys) ? keyStore.keys : [];

    const active = keys.find((item) => item && item.isActive && normalizeProviderName(item.provider) === normalized);
    if (active && active.baseUrl) {
        return String(active.baseUrl).trim();
    }

    const anyOne = keys.find((item) => item && normalizeProviderName(item.provider) === normalized && item.baseUrl);
    if (anyOne && anyOne.baseUrl) {
        return String(anyOne.baseUrl).trim();
    }

    return PROVIDER_BASE_URL_DEFAULTS[normalized] || '';
}

function syncApiKeyBaseUrlByProvider() {
    const providerEl = document.getElementById('apiKeyProvider');
    const baseUrlEl = document.getElementById('apiKeyBaseUrl');
    if (!providerEl || !baseUrlEl) return;

    const provider = normalizeProviderName(providerEl.value);
    baseUrlEl.value = getProviderBaseUrlFromStore(provider, AppState.keyStore);
}

function buildGenerationModelOptions(store) {
    const activeProviders = getActiveProvidersFromStore(store);
    const textByProvider = {};
    const imageByProvider = {};

    activeProviders.forEach((provider) => {
        const cfg = PROVIDER_MODEL_CATALOG[provider] || { text: [], image: [] };
        textByProvider[provider] = uniq(cfg.text).filter((m) => ALLOWED_TEXT_MODELS.has(m));
        imageByProvider[provider] = uniq(cfg.image).filter((m) => ALLOWED_IMAGE_MODELS.has(m));
    });

    return { activeProviders, textByProvider, imageByProvider };
}

function renderProviderSelect(selectEl, providers, selectedValue) {
    if (!selectEl) return;
    const list = Array.isArray(providers) ? providers : [];
    selectEl.innerHTML = list.map((provider) => {
        const selected = provider === selectedValue ? ' selected' : '';
        return `<option value="${escapeHtml(provider)}"${selected}>${escapeHtml(provider)}</option>`;
    }).join('') || '<option value="grsai">grsai</option>';
}

function renderFlatModelSelect(selectEl, models, selectedValue) {
    if (!selectEl) return;
    const list = Array.isArray(models) ? models : [];
    selectEl.innerHTML = list.map((model) => {
        const selected = model === selectedValue ? ' selected' : '';
        return `<option value="${escapeHtml(model)}"${selected}>${escapeHtml(model)}</option>`;
    }).join('') || '<option value="">无可用模型</option>';
}

function refreshGenerationModelOptions(storeOverride = null) {
    const store = storeOverride || AppState.keyStore || {};
    const options = buildGenerationModelOptions(store);
    const activeProviders = options.activeProviders || ['grsai'];
    const savedTextProvider = localStorage.getItem('generationTextProvider') || 'grsai';
    const savedImageProvider = localStorage.getItem('generationImageProvider') || 'grsai';
    const textProviderValue = (DOM.generationTextProviderSelect && DOM.generationTextProviderSelect.value) || savedTextProvider;
    const imageProviderValue = (DOM.generationImageProviderSelect && DOM.generationImageProviderSelect.value) || savedImageProvider;
    const selectedTextProvider = activeProviders.includes(textProviderValue)
        ? textProviderValue
        : (activeProviders.includes(savedTextProvider) ? savedTextProvider : (activeProviders[0] || 'grsai'));
    const selectedImageProvider = activeProviders.includes(imageProviderValue)
        ? imageProviderValue
        : (activeProviders.includes(savedImageProvider) ? savedImageProvider : (activeProviders[0] || 'grsai'));

    renderProviderSelect(DOM.generationTextProviderSelect, activeProviders, selectedTextProvider);
    renderProviderSelect(DOM.generationImageProviderSelect, activeProviders, selectedImageProvider);
    if (DOM.generationTextProviderSelect) DOM.generationTextProviderSelect.value = selectedTextProvider;
    if (DOM.generationImageProviderSelect) DOM.generationImageProviderSelect.value = selectedImageProvider;
    localStorage.setItem('generationTextProvider', selectedTextProvider);
    localStorage.setItem('generationImageProvider', selectedImageProvider);

    const textModels = options.textByProvider[selectedTextProvider] || [];
    const imageModels = options.imageByProvider[selectedImageProvider] || [];
    const modelPrefs = loadGenerationModelPrefs();
    const prefText = (((modelPrefs || {}).text || {})[selectedTextProvider] || '').trim();
    const prefImage = (((modelPrefs || {}).image || {})[selectedImageProvider] || '').trim();
    const currentText = DOM.generationTextModelSelect ? DOM.generationTextModelSelect.value : '';
    const currentImage = DOM.generationImageModelSelect ? DOM.generationImageModelSelect.value : '';

    renderFlatModelSelect(
        DOM.generationTextModelSelect,
        textModels,
        textModels.includes(prefText) ? prefText : currentText
    );
    renderFlatModelSelect(
        DOM.generationImageModelSelect,
        imageModels,
        imageModels.includes(prefImage) ? prefImage : currentImage
    );

    if (DOM.generationTextModelSelect && !DOM.generationTextModelSelect.value) {
        DOM.generationTextModelSelect.value = textModels[0] || '';
    }
    if (DOM.generationImageModelSelect && !DOM.generationImageModelSelect.value) {
        DOM.generationImageModelSelect.value = imageModels[0] || '';
    }

    persistLaneModelSelection('text', selectedTextProvider, DOM.generationTextModelSelect ? DOM.generationTextModelSelect.value : '');
    persistLaneModelSelection('image', selectedImageProvider, DOM.generationImageModelSelect ? DOM.generationImageModelSelect.value : '');
}

async function loadGenerationModelOptionsFromKeys() {
    try {
        const res = await fetch('/api/keys', { method: 'GET', credentials: 'same-origin' });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || data.message || '加载密钥失败');
        }
        AppState.keyStore = data;
        refreshGenerationModelOptions(data);
    } catch (error) {
        console.warn('加载模型选项失败:', error);
        refreshGenerationModelOptions(null);
    }
}

function updatePaperStage(stage, message, status = 'running') {
    const hasKnownStage = stage && PAPER_STAGE_ORDER.includes(stage);
    const safeStage = hasKnownStage ? stage : (status === 'failed' ? 'processing' : 'queued');
    const currentIdx = PAPER_STAGE_ORDER.indexOf(safeStage);

    if (DOM.paperStageTitle) {
        DOM.paperStageTitle.textContent = status === 'idle'
            ? '等待开始'
            : `当前阶段：${PAPER_STAGE_LABELS[safeStage] || '处理中'}`;
    }
    if (DOM.paperStageChip) {
        DOM.paperStageChip.textContent = status === 'idle'
            ? '未开始'
            : (status === 'failed' ? '失败' : (status === 'succeeded' ? '完成' : '进行中'));
    }
    if (DOM.paperStageMessage) {
        DOM.paperStageMessage.textContent = message || '处理中...';
    }

    if (DOM.paperStageItems && DOM.paperStageItems.length) {
        DOM.paperStageItems.forEach((item) => {
            const itemStage = item.dataset.stage;
            const itemIdx = PAPER_STAGE_ORDER.indexOf(itemStage);
            item.classList.remove('is-done', 'is-current', 'is-failed');
            if (status !== 'idle') {
                item.classList.remove('is-preview-current');
            }

            if (status === 'idle') {
                return;
            }

            if (status === 'failed') {
                if (itemStage === safeStage) {
                    item.classList.add('is-failed');
                } else if (itemIdx !== -1 && currentIdx !== -1 && itemIdx < currentIdx) {
                    item.classList.add('is-done');
                }
                return;
            }

            if (status === 'succeeded') {
                item.classList.add('is-done');
                return;
            }

            if (itemIdx !== -1 && currentIdx !== -1 && itemIdx < currentIdx) {
                item.classList.add('is-done');
            } else if (itemStage === safeStage) {
                item.classList.add('is-current');
            }
        });
    }
    if (DOM.paperStageList && status !== 'idle') {
        DOM.paperStageList.classList.remove('is-workflow-updating');
    }
}

function updatePaperTaskId(taskId) {
    if (!DOM.paperTaskIdText) return;
    const id = (taskId || '').trim();
    DOM.paperTaskIdText.textContent = id ? `任务ID：${id}` : '任务ID：--';
}

function getGenerationWorkflowConfig() {
    const expMode = (localStorage.getItem('generationExpMode') || '').trim();
    const retrievalSetting = (localStorage.getItem('generationRetrieval') || '').trim();
    const criticEnabled = localStorage.getItem('generationCriticEnabled') !== '0';
    const evalEnabled = localStorage.getItem('generationEvalEnabled') !== '0';
    const criticRoundsRaw = localStorage.getItem('generationCriticRounds');
    const criticRounds = Number.isFinite(Number(criticRoundsRaw)) ? Number(criticRoundsRaw) : 3;

    return {
        expMode,
        retrievalSetting,
        criticEnabled,
        evalEnabled,
        criticRounds: Math.max(0, Math.min(10, Math.trunc(criticRounds)))
    };
}

function syncGenerationWorkflowOptions() {
    const cfg = getGenerationWorkflowConfig();
    if (DOM.generationExpModeSelect) {
        DOM.generationExpModeSelect.value = cfg.expMode;
    }
    if (DOM.generationRetrievalSelect) {
        DOM.generationRetrievalSelect.value = cfg.retrievalSetting;
    }
    if (DOM.generationCriticEnabledCheck) {
        DOM.generationCriticEnabledCheck.checked = !!cfg.criticEnabled;
    }
    if (DOM.generationEvalEnabledCheck) {
        DOM.generationEvalEnabledCheck.checked = !!cfg.evalEnabled;
    }
    if (DOM.generationCriticRoundsInput) {
        DOM.generationCriticRoundsInput.value = String(cfg.criticRounds);
        DOM.generationCriticRoundsInput.disabled = !cfg.criticEnabled;
    }
    refreshGenerationWorkflowControlState();
    updateWorkflowPreview(false);
}

function refreshGenerationWorkflowControlState() {
    const expMode = DOM.generationExpModeSelect ? (DOM.generationExpModeSelect.value || 'dev_full') : 'dev_full';
    const isVanilla = expMode === 'vanilla';
    const supportsCritic = ['dev_full', 'demo_full', 'dev_planner_critic', 'demo_planner_critic'].includes(expMode);
    if (DOM.generationRetrievalSelect) {
        DOM.generationRetrievalSelect.disabled = isVanilla;
    }
    if (DOM.generationCriticEnabledCheck) {
        DOM.generationCriticEnabledCheck.disabled = !supportsCritic;
        if (!supportsCritic) DOM.generationCriticEnabledCheck.checked = false;
    }
    if (DOM.generationCriticRoundsInput) {
        const criticEnabled = DOM.generationCriticEnabledCheck ? DOM.generationCriticEnabledCheck.checked : true;
        DOM.generationCriticRoundsInput.disabled = !supportsCritic || !criticEnabled;
    }
}

function getWorkflowPlanFromUI() {
    const expModeRaw = DOM.generationExpModeSelect ? (DOM.generationExpModeSelect.value || '').trim() : '';
    const retrieval = DOM.generationRetrievalSelect ? (DOM.generationRetrievalSelect.value || '').trim() : '';
    const criticEnabled = DOM.generationCriticEnabledCheck ? !!DOM.generationCriticEnabledCheck.checked : true;
    const evalEnabled = DOM.generationEvalEnabledCheck ? !!DOM.generationEvalEnabledCheck.checked : true;
    const criticRounds = DOM.generationCriticRoundsInput
        ? Math.max(0, Math.min(10, Math.trunc(Number(DOM.generationCriticRoundsInput.value) || 0)))
        : 0;

    const expMode = expModeRaw || 'dev_full';
    const stages = ['queued', 'initializing', 'loading_agents', 'processing'];
    let expLabel = '';
    if (expMode === 'vanilla') {
        stages.push('processing_visualizer');
        expLabel = 'Vanilla（直接生图）';
    } else if (expMode === 'dev_planner') {
        stages.push('processing_planner', 'processing_visualizer');
        expLabel = 'Planner + 生图';
    } else if (expMode === 'dev_planner_stylist') {
        stages.push('processing_planner', 'processing_stylist', 'processing_visualizer');
        expLabel = 'Planner + Stylist + 生图';
    } else if (expMode === 'dev_planner_critic' || expMode === 'demo_planner_critic') {
        stages.push('processing_planner', 'processing_visualizer');
        if (criticEnabled && criticRounds > 0) {
            stages.push('processing_critic');
        }
        expLabel = 'Planner + Critic';
    } else {
        stages.push('processing_retriever', 'processing_planner', 'processing_stylist', 'processing_visualizer');
        if (criticEnabled && criticRounds > 0) {
            stages.push('processing_critic');
        }
        expLabel = expMode === 'demo_full' ? 'Demo Full' : 'Full';
    }
    if (evalEnabled && !['demo_full', 'demo_planner_critic', 'dev_retriever'].includes(expMode)) {
        stages.push('processing_eval');
    }
    stages.push('saving', 'completed');

    return {
        expMode,
        expLabel,
        retrieval,
        criticEnabled,
        evalEnabled,
        criticRounds,
        stages: Array.from(new Set(stages))
    };
}

function animateWorkflowPreview() {
    if (!DOM.paperStageList) return;
    DOM.paperStageList.classList.remove('is-workflow-updating');
    // Force reflow to restart animation.
    void DOM.paperStageList.offsetWidth;
    DOM.paperStageList.classList.add('is-workflow-updating');
    setTimeout(() => {
        if (DOM.paperStageList) DOM.paperStageList.classList.remove('is-workflow-updating');
    }, 420);
}

function updateWorkflowPreview(animate = false) {
    const plan = getWorkflowPlanFromUI();
    const planSet = new Set(plan.stages);
    if (DOM.paperStageItems && DOM.paperStageItems.length) {
        let plannedIdx = 0;
        DOM.paperStageItems.forEach((item) => {
            const stage = item.dataset.stage;
            const isPlanned = planSet.has(stage);
            item.classList.remove('is-planned', 'is-skipped', 'is-preview-current');
            if (isPlanned) {
                item.classList.add('is-planned');
                item.style.setProperty('--wf-delay', `${plannedIdx * 24}ms`);
                plannedIdx += 1;
            } else {
                item.classList.add('is-skipped');
                item.style.removeProperty('--wf-delay');
            }
        });
        const focusStage = plan.stages.find((s) => s.startsWith('processing_')) || 'processing';
        const focusEl = Array.from(DOM.paperStageItems).find((item) => item.dataset.stage === focusStage);
        if (focusEl) focusEl.classList.add('is-preview-current');
    }

    if (DOM.generationWorkflowSummary) {
        const criticText = plan.criticEnabled && plan.criticRounds > 0 ? `审图 ${plan.criticRounds} 轮` : '审图关闭';
        const evalText = plan.evalEnabled ? '评估开启' : '评估关闭';
        const retrievalText = plan.retrieval ? `检索=${plan.retrieval}` : '检索默认';
        DOM.generationWorkflowSummary.textContent = `当前流程预览：${plan.expLabel} · ${criticText} · ${evalText} · ${retrievalText}`;
    }

    if (animate) animateWorkflowPreview();
}

// 初始化应用
function initApp() {
    console.log("初始化 SCIdrawer 应用...");

    // 设置主题
    setTheme(AppState.theme);

    // 绑定事件
    bindEvents();
    renderReferenceImages();
    syncGenerationWorkflowOptions();

    // 加载初始数据
    loadInitialData();

    // 显示当前页面
    showPage(AppState.currentPage);
    updatePaperStage('queued', '提交任务后会显示 PaperBanana 当前处理阶段。', 'idle');
    updatePaperTaskId('');

    console.log('应用初始化完成');
}

// 设置主题
function setTheme(theme) {
    AppState.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // 更新主题切换按钮图标
    if (DOM.themeToggle) {
        const icon = DOM.themeToggle.querySelector('i');
        icon.className = theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
    }
}

// 绑定事件
function bindEvents() {
    // 侧边栏导航
    DOM.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            showPage(page);
        });
    });

    // 主题切换
    if (DOM.themeToggle) {
        DOM.themeToggle.addEventListener('click', () => {
            const newTheme = AppState.theme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    }

    // 搜索框
    if (DOM.searchInput) {
        DOM.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch(DOM.searchInput.value);
            }
        });
    }

    // 仪表盘事件
    if (DOM.refreshActivities) {
        DOM.refreshActivities.addEventListener('click', refreshActivities);
    }

    if (DOM.refreshModelStatus) {
        DOM.refreshModelStatus.addEventListener('click', refreshModelStatuses);
    }

    // 图像生成事件
    if (DOM.generateBtn) {
        DOM.generateBtn.addEventListener('click', generateImage);
    }

    if (DOM.resetFormBtn) {
        DOM.resetFormBtn.addEventListener('click', resetImageForm);
    }

    if (DOM.referenceImagesInput) {
        DOM.referenceImagesInput.addEventListener('change', (e) => {
            handleReferenceImages(e.target.files);
        });
    }

    if (DOM.clearBtn) {
        DOM.clearBtn.addEventListener('click', clearPreview);
    }

    // 聊天事件
    if (DOM.sendMessageBtn) {
        DOM.sendMessageBtn.addEventListener('click', sendMessage);
    }

    if (DOM.chatInput) {
        DOM.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (DOM.newChatBtn) {
        DOM.newChatBtn.addEventListener('click', createNewChat);
    }

    if (DOM.clearChatBtn) {
        DOM.clearChatBtn.addEventListener('click', clearChat);
    }

    // API 设置事件
    if (DOM.addKeyBtn) {
        DOM.addKeyBtn.addEventListener('click', addApiKey);
    }

    if (DOM.testKeyBtn) {
        DOM.testKeyBtn.addEventListener('click', testApiKey);
    }

    if (DOM.refreshKeysBtn) {
        DOM.refreshKeysBtn.addEventListener('click', refreshApiKeys);
    }

    const apiKeyProviderEl = document.getElementById('apiKeyProvider');
    if (apiKeyProviderEl) {
        apiKeyProviderEl.addEventListener('change', syncApiKeyBaseUrlByProvider);
    }
    if (DOM.generationTextProviderSelect) {
        DOM.generationTextProviderSelect.addEventListener('change', () => {
            const prev = localStorage.getItem('generationTextProvider') || 'grsai';
            persistLaneModelSelection('text', prev, DOM.generationTextModelSelect ? DOM.generationTextModelSelect.value : '');
            localStorage.setItem('generationTextProvider', DOM.generationTextProviderSelect.value || 'grsai');
            refreshGenerationModelOptions();
        });
    }
    if (DOM.generationImageProviderSelect) {
        DOM.generationImageProviderSelect.addEventListener('change', () => {
            const prev = localStorage.getItem('generationImageProvider') || 'grsai';
            persistLaneModelSelection('image', prev, DOM.generationImageModelSelect ? DOM.generationImageModelSelect.value : '');
            localStorage.setItem('generationImageProvider', DOM.generationImageProviderSelect.value || 'grsai');
            refreshGenerationModelOptions();
        });
    }
    if (DOM.generationTextModelSelect) {
        DOM.generationTextModelSelect.addEventListener('change', () => {
            const provider = (DOM.generationTextProviderSelect && DOM.generationTextProviderSelect.value) || 'grsai';
            persistLaneModelSelection('text', provider, DOM.generationTextModelSelect.value || '');
        });
    }
    if (DOM.generationImageModelSelect) {
        DOM.generationImageModelSelect.addEventListener('change', () => {
            const provider = (DOM.generationImageProviderSelect && DOM.generationImageProviderSelect.value) || 'grsai';
            persistLaneModelSelection('image', provider, DOM.generationImageModelSelect.value || '');
        });
    }
    if (DOM.generationExpModeSelect) {
        DOM.generationExpModeSelect.addEventListener('change', () => {
            localStorage.setItem('generationExpMode', (DOM.generationExpModeSelect.value || '').trim());
            refreshGenerationWorkflowControlState();
            updateWorkflowPreview(true);
        });
    }
    if (DOM.generationRetrievalSelect) {
        DOM.generationRetrievalSelect.addEventListener('change', () => {
            localStorage.setItem('generationRetrieval', (DOM.generationRetrievalSelect.value || '').trim());
            updateWorkflowPreview(true);
        });
    }
    if (DOM.generationCriticEnabledCheck) {
        DOM.generationCriticEnabledCheck.addEventListener('change', () => {
            const enabled = !!DOM.generationCriticEnabledCheck.checked;
            localStorage.setItem('generationCriticEnabled', enabled ? '1' : '0');
            refreshGenerationWorkflowControlState();
            updateWorkflowPreview(true);
        });
    }
    if (DOM.generationEvalEnabledCheck) {
        DOM.generationEvalEnabledCheck.addEventListener('change', () => {
            const enabled = !!DOM.generationEvalEnabledCheck.checked;
            localStorage.setItem('generationEvalEnabled', enabled ? '1' : '0');
            updateWorkflowPreview(true);
        });
    }
    if (DOM.generationCriticRoundsInput) {
        DOM.generationCriticRoundsInput.addEventListener('change', () => {
            const raw = Number(DOM.generationCriticRoundsInput.value);
            const value = Number.isFinite(raw) ? Math.max(0, Math.min(10, Math.trunc(raw))) : 3;
            DOM.generationCriticRoundsInput.value = String(value);
            localStorage.setItem('generationCriticRounds', String(value));
            updateWorkflowPreview(true);
        });
    }

    // 设置事件
    if (DOM.timeoutSelect) {
        DOM.timeoutSelect.addEventListener('change', saveSettings);
    }

    if (DOM.retrySelect) {
        DOM.retrySelect.addEventListener('change', saveSettings);
    }

    // API主机选择
    const apiHostSelect = document.getElementById('apiHostSelect');
    if (apiHostSelect) {
        apiHostSelect.addEventListener('change', saveSettings);
    }
    const apiHostCustomInput = document.getElementById('apiHostCustomInput');
    if (apiHostCustomInput) {
        apiHostCustomInput.addEventListener('change', saveSettings);
        apiHostCustomInput.addEventListener('blur', saveSettings);
    }

    // 流式响应开关
    const streamToggle = document.getElementById('streamToggle');
    if (streamToggle) {
        streamToggle.addEventListener('change', saveSettings);
    }

    // 模型选择
    const chatModelSelect = document.getElementById('chatModelSelect');

    if (chatModelSelect) {
        chatModelSelect.addEventListener('change', saveSettings);
    }

    // 主题选择器
    document.querySelectorAll('[data-theme]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const theme = e.currentTarget.dataset.theme;
            setTheme(theme);
        });
    });

    // 快速操作按钮
    document.querySelectorAll('.quick-action').forEach(action => {
        action.addEventListener('click', (e) => {
            e.preventDefault();
            const target = action.dataset.target;
            if (target) {
                showPage(target);
            }
        });
    });

    document.querySelectorAll('[data-fill-prompt]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const value = (btn.dataset.fillPrompt || '').trim();
            showPage('image-generation');
            if (DOM.promptInput && value) {
                DOM.promptInput.value = value;
                DOM.promptInput.focus();
                DOM.promptInput.setSelectionRange(DOM.promptInput.value.length, DOM.promptInput.value.length);
            }
        });
    });
}

// 显示页面
function showPage(pageId) {
    // 更新当前页面状态
    AppState.currentPage = pageId;

    // 更新导航激活状态
    DOM.navItems.forEach(item => {
        if (item.dataset.page === pageId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // 更新页面标题
    const config = PageConfig[pageId];
    if (config) {
        DOM.pageTitle.textContent = config.title;
    }

    // 切换页面内容
    DOM.pageSections.forEach(section => {
        if (section.id === `page-${pageId}`) {
            section.classList.add('active');
        } else {
            section.classList.remove('active');
        }
    });

    // 页面特定初始化
    switch (pageId) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'image-generation':
            loadGenerationModelOptionsFromKeys();
            updateWorkflowPreview(false);
            break;
        case 'api-keys':
            loadApiKeys();
            break;
        case 'settings':
            loadSettings();
            break;
    }

    // 滚动到顶部
    window.scrollTo(0, 0);
}

// 执行搜索
function performSearch(query) {
    if (!query.trim()) return;

    console.log('搜索:', query);
    // 这里可以添加实际的搜索逻辑
    showNotification(`搜索: ${query}`, 'info');
}

// 加载初始数据
async function loadInitialData() {
    try {        // 从后端读取当前 Key 状态
        try {
            const profileRes = await fetch('/api/profile', { method: 'GET', credentials: 'same-origin' });
            const profile = await profileRes.json();
            if (profileRes.ok) {
                AppState.hasKey = !!profile.hasKey;
                AppState.apiHost = profile.apiHost || '';
                AppState.activeBaseUrl = profile.activeBaseUrl || '';

                if (DOM.lastUsedTime && profile.usage && profile.usage.lastUsedAt) {
                    DOM.lastUsedTime.textContent = new Date(profile.usage.lastUsedAt).toLocaleString();
                }
            } else {
                AppState.hasKey = false;
            }
        } catch (e) {
            AppState.hasKey = false;
        }

        if (DOM.currentKeyStatus) {
            DOM.currentKeyStatus.textContent = AppState.hasKey ? '已设置' : '未设置';
            DOM.currentKeyStatus.className = AppState.hasKey ? 'badge badge-success' : 'badge badge-secondary';
        }// 更新仪表盘统计数据
        await updateDashboardStats();
        await loadGenerationModelOptionsFromKeys();

        // 初始化活动记录
        refreshActivities();
    } catch (error) {
        console.error('加载初始数据失败:', error);
    }
}

// 加载仪表盘数据
function loadDashboardData() {
    updateDashboardStats();
}

function getDashboardModels() {
    const models = [];
    if (window.APIConfig && Array.isArray(window.APIConfig.imageModels)) {
        window.APIConfig.imageModels.forEach((model) => {
            models.push({ id: model.id, name: model.name });
        });
    }
    if (window.APIConfig && Array.isArray(window.APIConfig.chatModels)) {
        window.APIConfig.chatModels.forEach((model) => {
            if (!models.find((item) => item.id === model.id)) {
                models.push({ id: model.id, name: model.name });
            }
        });
    }
    return models;
}

async function refreshCreditsBalance() {
    if (!DOM.creditsBalance) return;

    if (!window.APIService) {
        DOM.creditsBalance.textContent = '--';
        return;
    }

    try {
        const result = await window.APIService.getCredits();
        DOM.creditsBalance.textContent = typeof result.credits === 'number' ? result.credits : '--';
    } catch (error) {
        DOM.creditsBalance.textContent = '--';
        console.error('获取积分余额失败:', error);
        showNotification(`积分余额获取失败: ${error.message || '请求失败'}`, 'error');
    }
}

function updateDashboardKeyStatus() {
    if (!DOM.apiKeyStatusText) return;
    const hasKey = !!AppState.hasKey;
    DOM.apiKeyStatusText.textContent = hasKey ? '已设置' : '未设置';
}

function updateDashboardHost() {
    if (!DOM.apiHostDisplay) return;
    const host = (AppState.activeBaseUrl || AppState.apiHost || '').trim();
    DOM.apiHostDisplay.textContent = host ? host : '--';
}

async function refreshModelStatuses() {
    if (!DOM.modelStatusList) return;

    const models = getDashboardModels();
    if (models.length === 0) {
        DOM.modelStatusList.innerHTML = '<div class="model-status-empty">暂无模型</div>';
        return;
    }

    DOM.modelStatusList.innerHTML = '<div class="model-status-loading">正在获取模型状态...</div>';
    if (!AppState.hasKey) {
        DOM.modelStatusList.innerHTML = '<div class="model-status-empty">请先在“API 设置”里添加 Key</div>';
        return;
    }
    const results = await Promise.all(models.map(async (model) => {
        try {
            const response = await window.APIService.getModelStatus(model.id);
            return {
                model,
                status: !!response.status,
                error: response.error || ''
            };
        } catch (error) {
            return {
                model,
                status: false,
                error: error.message || '获取失败'
            };
        }
    }));

    DOM.modelStatusList.innerHTML = results.map((item) => {
        const badgeClass = item.status ? 'badge-success' : 'badge-error';
        const badgeText = item.status ? '正常' : '异常';
        const errorText = item.error ? `<div class="model-status-error">${escapeHtml(item.error)}</div>` : '';
        return `
            <div class="model-status-item">
                <div class="model-status-info">
                    <div class="model-status-name">${escapeHtml(item.model.name || item.model.id)}</div>
                    <div class="model-status-id">${escapeHtml(item.model.id)}</div>
                    ${errorText}
                </div>
                <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
        `;
    }).join('');
}

// 刷新活动记录
const MAX_REFERENCE_IMAGES = 3;
const MAX_REFERENCE_IMAGE_BYTES = 5 * 1024 * 1024;

function handleReferenceImages(fileList) {
    if (!fileList || fileList.length === 0) return;

    const files = Array.from(fileList);
    const remainingSlots = MAX_REFERENCE_IMAGES - AppState.referenceImages.length;

    if (remainingSlots <= 0) {
        showNotification('Reference image limit reached.', 'warning');
        if (DOM.referenceImagesInput) {
            DOM.referenceImagesInput.value = '';
        }
        return;
    }

    files.slice(0, remainingSlots).forEach((file) => {
        if (!file.type || !file.type.startsWith('image/')) {
            showNotification(`Skipped ${file.name}: not an image.`, 'warning');
            return;
        }
        if (file.size > MAX_REFERENCE_IMAGE_BYTES) {
            showNotification(`Skipped ${file.name}: file too large.`, 'warning');
            return;
        }

        const reader = new FileReader();
        reader.onload = () => {
            AppState.referenceImages.push({
                name: file.name,
                size: file.size,
                dataUrl: reader.result
            });
            renderReferenceImages();
        };
        reader.onerror = () => {
            showNotification(`Failed to read ${file.name}.`, 'error');
        };
        reader.readAsDataURL(file);
    });

    if (DOM.referenceImagesInput) {
        DOM.referenceImagesInput.value = '';
    }
}

function removeReferenceImage(index) {
    AppState.referenceImages.splice(index, 1);
    renderReferenceImages();
}

function renderReferenceImages() {
    if (!DOM.referenceImagesList) return;

    if (AppState.referenceImages.length === 0) {
        DOM.referenceImagesList.innerHTML = '<div class=\"reference-empty\">No reference images</div>';
        return;
    }

    DOM.referenceImagesList.innerHTML = AppState.referenceImages.map((item, index) => `
        <div class=\"reference-item\">
            <img src=\"${item.dataUrl}\" alt=\"Reference ${index + 1}\" class=\"reference-thumb\">
            <div class=\"reference-meta\">
                <div class=\"reference-name\">${escapeHtml(item.name)}</div>
                <div class=\"reference-size\">${formatBytes(item.size)}</div>
            </div>
            <button class=\"reference-remove\" data-index=\"${index}\" type=\"button\">
                <i class=\"fas fa-times\"></i>
            </button>
        </div>
    `).join('');

    DOM.referenceImagesList.querySelectorAll('.reference-remove').forEach((btn) => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.dataset.index, 10);
            if (!Number.isNaN(idx)) {
                removeReferenceImage(idx);
            }
        });
    });
}

function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = (bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1);
    return `${value} ${units[index]}`;
}

function refreshActivities() {
    if (!DOM.activitiesList) return;

    DOM.activitiesList.innerHTML = `
        <div class="activity-item">
            <div class="activity-icon">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">加载中...</div>
                <div class="activity-description">正在获取最新活动记录</div>
            </div>
        </div>
    `;

    // 从localStorage加载活动记录
    setTimeout(() => {
        const activities = JSON.parse(localStorage.getItem('activities') || '[]');

        if (activities.length === 0) {
            DOM.activitiesList.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="fas fa-circle text-tertiary"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">暂无活动记录</div>
                        <div class="activity-description">开始一次绘图或对话后会显示在这里</div>
                    </div>
                    <div class="activity-time"></div>
                </div>
            `;
            return;
        }

        // 显示实际的活动记录
        DOM.activitiesList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas ${activity.icon}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-description">${activity.description}</div>
                </div>
                <div class="activity-time">${formatTime(activity.timestamp || activity.time)}</div>
            </div>
        `).join('');
    }, 300);
}

// 添加活动记录
function addActivity(activity) {
    // 获取现有活动记录
    const activities = JSON.parse(localStorage.getItem('activities') || '[]');

    // 添加时间戳
    activity.timestamp = new Date().toISOString();

    // 添加到列表开头
    activities.unshift(activity);

    // 限制最多保存20条记录
    if (activities.length > 20) {
        activities.pop();
    }

    // 保存到localStorage
    localStorage.setItem('activities', JSON.stringify(activities));

    // 如果当前在仪表盘页面，刷新活动列表
    if (AppState.currentPage === 'dashboard' && DOM.activitiesList) {
        refreshActivities();
    }
}

// 更新仪表盘统计数据
async function updateDashboardStats() {
    try {
        updateDashboardKeyStatus();
        updateDashboardHost();
        await refreshCreditsBalance();
        await refreshModelStatuses();
    } catch (error) {
        console.error('更新仪表盘统计失败:', error);
    }
}

// 生成图像
async function generateImage() {
    if (!DOM.promptInput || !DOM.promptInput.value.trim()) {
        ErrorHandler.handleValidationError('提示词', '请输入提示词');
        DOM.promptInput.focus();
        return;
    }

    if (AppState.isLoading) return;

    // 检查API密钥
    if (!AppState.hasKey) {
        ErrorHandler.handleValidationError('API设置', '请先在“API 设置”页面添加 Key');
        showPage('api-keys');
        return;
    }

    AppState.isLoading = true;
    const generationController = { cancelled: false, taskId: null };
    AppState.currentGeneration = generationController;
    DOM.generateBtn.disabled = true;
    DOM.generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';

    const prompt = DOM.promptInput.value;
    const textProvider = DOM.generationTextProviderSelect ? DOM.generationTextProviderSelect.value : 'grsai';
    const imageProvider = DOM.generationImageProviderSelect ? DOM.generationImageProviderSelect.value : 'grsai';
    const provider = imageProvider || textProvider || 'grsai';
    const textModel = DOM.generationTextModelSelect ? DOM.generationTextModelSelect.value : 'gemini-2.5-pro';
    const imageModel = DOM.generationImageModelSelect ? DOM.generationImageModelSelect.value : 'nano-banana-pro';
    const workflowExpMode = DOM.generationExpModeSelect ? (DOM.generationExpModeSelect.value || '').trim() : '';
    const workflowRetrieval = DOM.generationRetrievalSelect ? (DOM.generationRetrievalSelect.value || '').trim() : '';
    const workflowCriticEnabled = DOM.generationCriticEnabledCheck ? !!DOM.generationCriticEnabledCheck.checked : true;
    const workflowEvalEnabled = DOM.generationEvalEnabledCheck ? !!DOM.generationEvalEnabledCheck.checked : true;
    const workflowCriticRoundsRaw = DOM.generationCriticRoundsInput ? Number(DOM.generationCriticRoundsInput.value) : 3;
    const workflowCriticRounds = Number.isFinite(workflowCriticRoundsRaw)
        ? Math.max(0, Math.min(10, Math.trunc(workflowCriticRoundsRaw)))
        : 3;

    // 更新进度条
    if (DOM.progressBar) DOM.progressBar.style.width = '10%';
    if (DOM.progressText) DOM.progressText.textContent = '10%';
    updatePaperStage('queued', '任务已提交，等待 PaperBanana 启动...', 'running');

    try {
        // 使用API服务生成图像
        const result = await window.APIService.generateImage(prompt, {
            model: 'nano-banana-pro',
            provider,
            textProvider,
            imageProvider,
            textModel,
            imageModel,
            expMode: workflowExpMode,
            retrievalSetting: workflowRetrieval,
            criticEnabled: workflowCriticEnabled,
            evalEnabled: workflowEvalEnabled,
            maxCriticRounds: workflowCriticEnabled ? workflowCriticRounds : 0,
            aspectRatio: 'auto',
            imageSize: '1K',
            urls: AppState.referenceImages.map((item) => item.dataUrl),
            cancellation: generationController,
            onProgress: (progress, message, payload) => {
                // 更新进度条
                if (DOM.progressBar) {
                    DOM.progressBar.style.width = `${progress}%`;
                }
                if (DOM.progressText) {
                    DOM.progressText.textContent = `${progress}%`;
                }

                // 显示进度消息
                if (message) {
                    console.log('生成进度:', message);
                }
                if (payload && payload.id) {
                    updatePaperTaskId(payload.id);
                }
                updatePaperStage(payload?.stage, payload?.stageMessage || message, payload?.status || 'running');
            },
            onComplete: (resultData) => {
                // 处理生成结果
                handleImageGenerationComplete(resultData);
            }
        });

        if (result.success) {
            // 更新使用统计
            window.APIService.updateStats('image');

            // 更新仪表盘数据
            updateDashboardStats();

    ErrorHandler.handleSuccess('图像生成任务已提交，正在处理中...', '图像生成');
        } else {
            throw new Error(result.message || '图像生成失败');
        }
    } catch (error) {
        const failedTaskId = AppState.currentGeneration && AppState.currentGeneration.taskId
            ? AppState.currentGeneration.taskId
            : '';
        const taskIdFromError = (error && error.taskId) ? error.taskId : '';
        const finalTaskId = taskIdFromError || failedTaskId;

        if (error && error.isTimeout) {
            AppState.isLoading = false;
            AppState.currentGeneration = null;
            DOM.generateBtn.disabled = false;
            DOM.generateBtn.innerHTML = '<i class="fas fa-magic"></i> 生成图像';
            if (DOM.progressBar) DOM.progressBar.style.width = '95%';
            if (DOM.progressText) DOM.progressText.textContent = '95%';
            updatePaperStage('processing', '轮询超时，任务仍在后台执行，请稍后查询结果', 'running');
            updatePaperTaskId(finalTaskId);
            showNotification(`任务仍在执行中，可稍后查询。任务ID：${finalTaskId || '未知'}`, 'warning');
            return;
        }

        if (!(error && error.isCanceled)) {
            ErrorHandler.handleApiError(error, '图像生成');
        }

        // 重置UI状态
        AppState.isLoading = false;
        AppState.currentGeneration = null;
        DOM.generateBtn.disabled = false;
        DOM.generateBtn.innerHTML = '<i class="fas fa-magic"></i> 生成图像';

        if (DOM.progressBar) DOM.progressBar.style.width = '0%';
        if (DOM.progressText) DOM.progressText.textContent = '0%';
        if (error && error.isCanceled) {
            updatePaperStage('failed', '任务已取消', 'failed');
        } else {
            updatePaperStage('failed', error.message || '任务执行失败', 'failed');
        }
        updatePaperTaskId(finalTaskId);
    }
}

// 处理图像生成完成
function handleImageGenerationComplete(resultData) {
    AppState.isLoading = false;
    AppState.currentGeneration = null;
    DOM.generateBtn.disabled = false;
    DOM.generateBtn.innerHTML = '<i class="fas fa-magic"></i> 生成图像';

    // 更新进度条
    if (DOM.progressBar) {
        DOM.progressBar.style.width = '100%';
    }
    if (DOM.progressText) {
        DOM.progressText.textContent = '100%';
    }
    updatePaperStage(resultData.stage || 'completed', resultData.stageMessage || '图像生成完成', 'succeeded');
    updatePaperTaskId(resultData && resultData.id ? resultData.id : '');

    // 启用下载按钮
    if (DOM.downloadBtn) {
        DOM.downloadBtn.disabled = false;

        // 设置下载链接
        if (resultData.results && resultData.results.length > 0 && resultData.results[0].url) {
            const imageUrl = resultData.results[0].url;
            DOM.downloadBtn.onclick = () => {
                const link = document.createElement('a');
                link.href = imageUrl;
                link.download = `matchbox-image-${Date.now()}.png`;
                link.click();
            };
        }
    }

    // 更新预览
    const previewContainer = document.querySelector('.preview-container');
    if (previewContainer && resultData.results && resultData.results.length > 0) {
        const result = resultData.results[0];

        if (result.url) {
            // 显示生成的图像
            previewContainer.innerHTML = `
                <div class="preview-success">
                    <div class="preview-success-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <img src="${result.url}" alt="生成的图像" class="preview-image" style="max-width: 100%; max-height: 400px; margin: 1rem 0;">
                    <p>图像生成成功！</p>
                    <p class="text-sm text-tertiary">${result.content || '点击下载按钮保存图像'}</p>
                </div>
            `;
        } else {
            // 显示成功消息
            previewContainer.innerHTML = `
                <div class="preview-success">
                    <div class="preview-success-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <p>图像生成成功！</p>
                    <p class="text-sm text-tertiary">${result.content || '生成完成'}</p>
                </div>
            `;
        }
    }

    ErrorHandler.handleSuccess('图像生成成功', '图像生成');

    // 添加到活动记录
    addActivity({
        icon: 'fa-image',
        title: '图像生成完成',
        description: `使用 ${resultData.model || 'AI'} 模型`,
        time: '刚刚'
    });
}

async function cancelCurrentGeneration() {
    const current = AppState.currentGeneration;
    if (!current) return;
    current.cancelled = true;

    const taskId = current.taskId;
    if (taskId && window.APIService && typeof window.APIService.cancelImageTask === 'function') {
        try {
            await window.APIService.cancelImageTask(taskId);
        } catch (error) {
            console.warn('取消后端任务失败:', error);
        }
    }
}

// 重置图像表单
async function resetImageForm() {
    if (AppState.isLoading) {
        await cancelCurrentGeneration();
    }

    if (DOM.promptInput) DOM.promptInput.value = '';
    if (DOM.generationTextProviderSelect && DOM.generationTextProviderSelect.options.length > 0) {
        DOM.generationTextProviderSelect.selectedIndex = 0;
        localStorage.setItem('generationTextProvider', DOM.generationTextProviderSelect.value || 'grsai');
    }
    if (DOM.generationImageProviderSelect && DOM.generationImageProviderSelect.options.length > 0) {
        DOM.generationImageProviderSelect.selectedIndex = 0;
        localStorage.setItem('generationImageProvider', DOM.generationImageProviderSelect.value || 'grsai');
    }
    if (DOM.generationTextProviderSelect || DOM.generationImageProviderSelect) {
        refreshGenerationModelOptions();
    }
    if (DOM.generationTextModelSelect && DOM.generationTextModelSelect.options.length > 0) {
        DOM.generationTextModelSelect.selectedIndex = 0;
    }
    if (DOM.generationImageModelSelect && DOM.generationImageModelSelect.options.length > 0) {
        DOM.generationImageModelSelect.selectedIndex = 0;
    }
    if (DOM.generationExpModeSelect) {
        DOM.generationExpModeSelect.value = '';
        localStorage.setItem('generationExpMode', '');
    }
    if (DOM.generationRetrievalSelect) {
        DOM.generationRetrievalSelect.value = '';
        localStorage.setItem('generationRetrieval', '');
    }
    if (DOM.generationCriticEnabledCheck) {
        DOM.generationCriticEnabledCheck.checked = true;
        localStorage.setItem('generationCriticEnabled', '1');
    }
    if (DOM.generationEvalEnabledCheck) {
        DOM.generationEvalEnabledCheck.checked = true;
        localStorage.setItem('generationEvalEnabled', '1');
    }
    if (DOM.generationCriticRoundsInput) {
        DOM.generationCriticRoundsInput.value = '3';
        DOM.generationCriticRoundsInput.disabled = false;
        localStorage.setItem('generationCriticRounds', '3');
    }
    refreshGenerationWorkflowControlState();
    updateWorkflowPreview(false);
    if (DOM.referenceImagesInput) DOM.referenceImagesInput.value = '';
    AppState.referenceImages = [];
    renderReferenceImages();

    if (DOM.progressBar) DOM.progressBar.style.width = '0%';
    if (DOM.progressText) DOM.progressText.textContent = '0%';
    if (DOM.downloadBtn) DOM.downloadBtn.disabled = true;
    updatePaperStage('queued', '提交任务后会显示 PaperBanana 当前处理阶段。', 'idle');
    updatePaperTaskId('');
    AppState.isLoading = false;
    AppState.currentGeneration = null;
    if (DOM.generateBtn) {
        DOM.generateBtn.disabled = false;
        DOM.generateBtn.innerHTML = '<i class="fas fa-magic"></i> 生成图像';
    }

    const previewContainer = document.querySelector('.preview-container');
    if (previewContainer) {
        previewContainer.innerHTML = `
            <div class="preview-placeholder">
                <div class="preview-placeholder-icon">
                    <i class="fas fa-image"></i>
                </div>
                <p>生成的图像将显示在这里</p>
                <p class="text-sm text-tertiary">填写提示词并点击"生成图像"开始</p>
            </div>
        `;
    }
}

// 清空预览
function clearPreview() {
    resetImageForm();
    ErrorHandler.handleSuccess('预览已清空', '图像生成');
}

// 发送消息
async function sendMessage() {
    const message = DOM.chatInput ? DOM.chatInput.value.trim() : '';
    if (!message) return;

    // 检查API密钥
    if (!AppState.hasKey) {
        ErrorHandler.handleValidationError('API设置', '请先在“API 设置”页面添加 Key');
        showPage('api-keys');
        return;
    }

    // 添加用户消息
    addMessage(message, 'user');

    // 清空输入框
    if (DOM.chatInput) {
        DOM.chatInput.value = '';
        DOM.chatInput.style.height = 'auto';
    }

    // 禁用发送按钮
    if (DOM.sendMessageBtn) {
        DOM.sendMessageBtn.disabled = true;
        DOM.sendMessageBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 思考中...';
    }

    // 添加AI思考中的消息
    const thinkingMessageId = 'thinking-' + Date.now();
    addMessage('思考中...', 'assistant', thinkingMessageId);

    try {
        // 获取聊天历史
        const messages = getChatHistory();
        messages.push({
            role: 'user',
            content: message
        });

        // 检查是否启用流式响应
        const useStreaming = window.APIService.useStreaming;

        if (useStreaming) {
            // 流式响应
            await sendMessageStreaming(messages, thinkingMessageId);
        } else {
            // 非流式响应
            await sendMessageNonStreaming(messages, thinkingMessageId);
        }

        // 更新使用统计
        window.APIService.updateStats('chat');
        updateDashboardStats();

        // 添加到活动记录
        addActivity({
            icon: 'fa-comment',
            title: 'AI对话完成',
            description: '与AI助手进行了对话',
            time: '刚刚'
        });

    } catch (error) {
        const errorResult = ErrorHandler.handleApiError(error, '发送消息');

        // 更新思考中的消息为错误消息
        updateMessage(thinkingMessageId, `抱歉，我遇到了一些问题: ${errorResult.message}`, 'assistant');
    } finally {
        // 恢复发送按钮
        if (DOM.sendMessageBtn) {
            DOM.sendMessageBtn.disabled = false;
            DOM.sendMessageBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 发送';
        }
    }
}

// 获取聊天历史
function getChatHistory() {
    const messages = [];
    const messageElements = DOM.chatMessages ? DOM.chatMessages.querySelectorAll('.message') : [];

    for (const element of messageElements) {
        const isUser = element.classList.contains('user');
        const messageText = element.querySelector('.message-text');

        if (messageText) {
            messages.push({
                role: isUser ? 'user' : 'assistant',
                content: messageText.textContent
            });
        }
    }

    return messages;
}

// 发送消息 - 流式响应
async function sendMessageStreaming(messages, thinkingMessageId) {
    try {
        // 获取流式响应
        const stream = await window.APIService.chatCompletionStream(messages, {
            model: window.APIService.activeChatModel,
            temperature: 0.7,
            maxTokens: 2000
        });

        let fullResponse = '';
        let isFirstChunk = true;

        // 处理流式数据
        await window.APIService.processStreamResponse(
            stream.reader,
            stream.decoder,
            (chunk) => {
                if (chunk.choices && chunk.choices.length > 0) {
                    const delta = chunk.choices[0].delta;
                    if (delta && delta.content) {
                        if (isFirstChunk) {
                            // 替换思考中的消息
                            updateMessage(thinkingMessageId, delta.content, 'assistant');
                            isFirstChunk = false;
                        } else {
                            // 追加内容
                            appendToMessage(thinkingMessageId, delta.content);
                        }
                        fullResponse += delta.content;
                    }
                }
            },
            () => {
                // 流式完成
                console.log('流式响应完成');
                stream.close();
            }
        );

    } catch (error) {
        throw new Error(`流式聊天失败: ${error.message}`);
    }
}

// 发送消息 - 非流式响应
async function sendMessageNonStreaming(messages, thinkingMessageId) {
    try {
        const response = await window.APIService.chatCompletion(messages, {
            model: window.APIService.activeChatModel,
            stream: false,
            temperature: 0.7,
            maxTokens: 2000
        });

        if (response.success && response.data && response.data.choices && response.data.choices.length > 0) {
            const aiResponse = response.data.choices[0].message.content;
            updateMessage(thinkingMessageId, aiResponse, 'assistant');
        } else {
            throw new Error('AI响应格式错误');
        }
    } catch (error) {
        throw new Error(`非流式聊天失败: ${error.message}`);
    }
}

// 更新消息内容
function updateMessage(messageId, newText, sender) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const messageText = messageElement.querySelector('.message-text');
        if (messageText) {
            messageText.textContent = newText;
        }
    } else {
        // 如果找不到消息元素，创建新的消息
        addMessage(newText, sender, messageId);
    }
}

// 追加消息内容
function appendToMessage(messageId, additionalText) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        const messageText = messageElement.querySelector('.message-text');
        if (messageText) {
            messageText.textContent += additionalText;

            // 滚动到底部
            DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
        }
    }
}

// 添加消息
function addMessage(text, sender, messageId = null) {
    if (!DOM.chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    if (messageId) {
        messageDiv.id = messageId;
    }

    const avatarIcon = sender === 'user' ? 'fa-user' : 'fa-robot';
    const senderName = sender === 'user' ? '您' : 'AI 助手';

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${avatarIcon}"></i>
        </div>
        <div class="message-content">
            <div class="message-text">${escapeHtml(text)}</div>
            <div class="message-time">刚刚</div>
        </div>
    `;

    DOM.chatMessages.appendChild(messageDiv);

    // 滚动到底部
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
}

// 创建新对话
function createNewChat() {
    if (!DOM.chatMessages) return;

    DOM.chatMessages.innerHTML = `
        <div class="message assistant">
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-text">
                    你好！我是 AI 助手，很高兴为您服务。我可以帮助您解答问题、生成内容或进行对话。请问有什么可以帮您的吗？
                </div>
                <div class="message-time">刚刚</div>
            </div>
        </div>
    `;

    if (DOM.chatInput) {
        DOM.chatInput.value = '';
    }

    ErrorHandler.handleSuccess('新对话已创建', '智能对话');
}

// 清空对话
function clearChat() {
    if (!confirm('确定要清空当前对话吗？')) return;

    createNewChat();
}

// 加载API密钥（后端加密存储，支持多提供商）
async function loadApiKeys() {
    if (!DOM.keysTableBody) return;

    const colCount = 5;
    DOM.keysTableBody.innerHTML = `
        <tr>
            <td colspan="${colCount}" class="text-center py-8">
                <div class="loading">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">加载中...</div>
                </div>
            </td>
        </tr>
    `;

    try {
        const res = await fetch('/api/keys', { method: 'GET', credentials: 'same-origin' });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || data.message || '加载失败');
        }

        // 更新状态区
        const anyActive = data && data.keys && data.keys.some(k => k && k.isActive);
        AppState.keyStore = data;
        refreshGenerationModelOptions(data);
        syncApiKeyBaseUrlByProvider();
        if (DOM.currentKeyStatus) {
            DOM.currentKeyStatus.textContent = anyActive ? '已设置' : '未设置';
            DOM.currentKeyStatus.className = anyActive ? 'badge badge-success' : 'badge badge-secondary';
        }

        renderApiKeysTable(data);
    } catch (e) {
        DOM.keysTableBody.innerHTML = `
            <tr>
                <td colspan="${colCount}" class="text-center py-8">
                    <div class="text-tertiary">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                        <p>加载失败</p>
                        <p class="text-sm">${escapeHtml(e.message || '未知错误')}</p>
                    </div>
                </td>
            </tr>
        `;
    }
}

function renderApiKeysTable(store) {
    if (!DOM.keysTableBody) return;

    const keys = (store && store.keys) ? store.keys : [];
    if (!keys.length) {
        DOM.keysTableBody.innerHTML = `
            <tr class="keys-empty">
                <td colspan="5" class="text-center py-8">
                    <i class="fas fa-key text-3xl text-tertiary mb-2"></i>
                    <p class="text-tertiary">暂无 API 密钥</p>
                    <p class="text-sm text-muted">添加您的第一个 API 密钥以开始使用</p>
                </td>
            </tr>
        `;
        return;
    }

    DOM.keysTableBody.innerHTML = keys.map(key => {
        const provider = key.provider || 'grsai';
        const name = key.name || '';
        const baseUrl = key.baseUrl || '';
        const baseUrlShort = baseUrl && baseUrl.length > 32 ? baseUrl.slice(0, 32) + '…' : baseUrl;

        return `
            <tr>
                <td>
                    <span class="badge badge-secondary">${escapeHtml(provider)}</span>
                </td>
                <td>
                    ${escapeHtml(name || '未命名')}
                    ${key.isActive ? '<span class="badge badge-primary badge-sm ml-2">当前</span>' : ''}
                </td>
                <td><code class="key-masked">${escapeHtml(key.mask || '***')}</code></td>
                <td title="${escapeHtml(baseUrl)}">${escapeHtml(baseUrlShort || '--')}</td>
                <td>
                    <div class="key-actions">
                        <button class="btn btn-icon btn-sm ${key.isActive ? 'btn-primary' : ''}" title="${key.isActive ? '当前密钥' : '设为当前'}" onclick="setActiveKey('${escapeHtml(key.id)}')" ${key.isActive ? 'disabled' : ''}>
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-icon btn-sm btn-danger" title="删除" onclick="deleteApiKeyById('${escapeHtml(key.id)}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 设为当前密钥（按 provider 生效）
async function setActiveKey(keyId) {
    if (!keyId) return;
    try {
        const res = await fetch('/api/keys/active', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: keyId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || '设置失败');
        ErrorHandler.handleSuccess('已设为当前（该提供商）', 'API密钥管理');
        await loadApiKeys();
        loadInitialData();
    } catch (e) {
        ErrorHandler.handleApiError(e, '设为当前密钥');
    }
}

// 删除API密钥
async function deleteApiKeyById(keyId) {
    if (!keyId || !confirm('确定要删除这个API密钥吗？')) return;
    try {
        const res = await fetch(`/api/keys/${encodeURIComponent(keyId)}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || '删除失败');
        ErrorHandler.handleSuccess('API密钥已删除', 'API密钥删除');
        await loadApiKeys();
        loadInitialData();
    } catch (e) {
        ErrorHandler.handleApiError(e, '删除API密钥');
    }
}

// 添加API密钥
async function addApiKey() {
    const providerEl = document.getElementById('apiKeyProvider');
    const baseUrlEl = document.getElementById('apiKeyBaseUrl');

    const provider = providerEl ? providerEl.value : 'grsai';
    const key = DOM.newApiKey ? DOM.newApiKey.value.trim() : '';
    const name = DOM.keyName ? DOM.keyName.value.trim() : '';
    const baseUrl = baseUrlEl ? baseUrlEl.value.trim() : '';

    if (!key) {
        ErrorHandler.handleValidationError('API密钥', '请输入 API 密钥');
        if (DOM.newApiKey) DOM.newApiKey.focus();
        return;
    }

    showNotification('正在添加API密钥...', 'info');

    try {
        const res = await fetch('/api/keys', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, value: key, name, baseUrl })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || '添加失败');

        if (DOM.newApiKey) DOM.newApiKey.value = '';
        if (DOM.keyName) DOM.keyName.value = '';
        syncApiKeyBaseUrlByProvider();

        ErrorHandler.handleSuccess('API密钥已添加并设为当前（该提供商）', 'API密钥管理');
        await loadApiKeys();
        loadInitialData();

        addActivity({
            icon: 'fa-key',
            title: 'API密钥已添加',
            description: (name || provider || '新API密钥'),
            time: '刚刚'
        });
    } catch (e) {
        ErrorHandler.handleApiError(e, '添加API密钥');
    }
}

// 测试API密钥（暂不直接在前端暴露 Key；建议添加后通过聊天/生成验证）
async function testApiKey() {
    ErrorHandler.handleValidationError('API密钥', '请先添加密钥；本地模式下将由后端使用并验证。');
}

// 刷新API密钥
function refreshApiKeys() {
    loadApiKeys();
    ErrorHandler.handleSuccess('API密钥列表已刷新', 'API密钥管理');
}


// 加载设置
function loadSettings() {
    // 从localStorage加载设置
    const settings = JSON.parse(localStorage.getItem('appSettings') || '{}');

    if (DOM.timeoutSelect && settings.timeout) {
        DOM.timeoutSelect.value = settings.timeout;
    }

    if (DOM.retrySelect && settings.retry) {
        DOM.retrySelect.value = settings.retry;
    }

    // 加载API主机设置
    const apiHostSelect = document.getElementById('apiHostSelect');
    const apiHostCustomInput = document.getElementById('apiHostCustomInput');
    if (apiHostSelect) {
        const savedHost = localStorage.getItem('apiHost') || 'https://grsaiapi.com';
        const hasOption = Array.from(apiHostSelect.options).some((opt) => opt.value === savedHost);
        if (hasOption) {
            apiHostSelect.value = savedHost;
            if (apiHostCustomInput) apiHostCustomInput.value = '';
        } else {
            apiHostSelect.value = 'custom';
            if (apiHostCustomInput) apiHostCustomInput.value = savedHost;
        }

        // 更新API服务的主机
        if (window.APIService) {
            window.APIService.setApiHost(savedHost);
        }
    }

    // 加载流式响应设置
    const streamToggle = document.getElementById('streamToggle');
    if (streamToggle) {
        const useStreaming = localStorage.getItem('useStreaming') !== 'false';
        streamToggle.checked = useStreaming;

        if (window.APIService) {
            window.APIService.useStreaming = useStreaming;
        }
    }

    // 加载模型选择
    const chatModelSelect = document.getElementById('chatModelSelect');

    if (chatModelSelect && window.APIService) {
        chatModelSelect.value = window.APIService.activeChatModel;
    }
}

// 保存设置
function saveSettings() {
    const settings = {
        timeout: DOM.timeoutSelect ? DOM.timeoutSelect.value : '60',
        retry: DOM.retrySelect ? DOM.retrySelect.value : '1'
    };

    localStorage.setItem('appSettings', JSON.stringify(settings));

    // 保存API主机设置
    const apiHostSelect = document.getElementById('apiHostSelect');
    const apiHostCustomInput = document.getElementById('apiHostCustomInput');
    if (apiHostSelect) {
        const selectedHost = apiHostSelect.value === 'custom'
            ? String(apiHostCustomInput ? apiHostCustomInput.value : '').trim()
            : apiHostSelect.value;
        const finalHost = selectedHost || 'https://grsaiapi.com';
        localStorage.setItem('apiHost', finalHost);

        if (window.APIService) {
            window.APIService.setApiHost(finalHost);
        }
    }

    // 保存流式响应设置
    const streamToggle = document.getElementById('streamToggle');
    if (streamToggle) {
        const useStreaming = streamToggle.checked;
        localStorage.setItem('useStreaming', useStreaming);

        if (window.APIService) {
            window.APIService.useStreaming = useStreaming;
        }
    }

    // 保存模型选择
    const chatModelSelect = document.getElementById('chatModelSelect');

    if (chatModelSelect && window.APIService) {
        const selectedModel = chatModelSelect.value;
        window.APIService.activeChatModel = selectedModel;
        localStorage.setItem('activeChatModel', selectedModel);
    }

    ErrorHandler.handleSuccess('设置已保存', '系统设置');
}

// 错误处理工具
const ErrorHandler = {
    // 处理API错误
    handleApiError: function(error, context = '') {
        console.error(`API错误 [${context}]:`, error);

        let userMessage = '发生未知错误';

        if (error.message) {
            if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                userMessage = '网络连接失败，请检查网络连接';
            } else if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                userMessage = 'API密钥无效或已过期';
            } else if (error.message.includes('403') || error.message.includes('Forbidden')) {
                userMessage = '权限不足，请检查API密钥权限';
            } else if (error.message.includes('429') || error.message.includes('Too Many Requests')) {
                userMessage = '请求过于频繁，请稍后再试';
            } else if (error.message.includes('500') || error.message.includes('Internal Server Error')) {
                userMessage = '服务器内部错误，请稍后再试';
            } else if (error.message.includes('timeout')) {
                userMessage = '请求超时，请检查网络连接';
            } else {
                userMessage = error.message;
            }
        }

        showNotification(`${context ? context + ': ' : ''}${userMessage}`, 'error');

        // 记录错误到活动记录
        if (context) {
            addActivity({
                icon: 'fa-exclamation-circle',
                title: `${context}失败`,
                description: userMessage,
                time: '刚刚'
            });
        }

        return {
            success: false,
            message: userMessage,
            error: error
        };
    },

    // 处理验证错误
    handleValidationError: function(field, message) {
        showNotification(`${field}: ${message}`, 'error');
        return {
            success: false,
            field: field,
            message: message
        };
    },

    // 处理成功操作
    handleSuccess: function(message, context = '') {
        showNotification(message, 'success');
        return {
            success: true,
            message: message
        };
    }
};

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
        </div>
        <div class="notification-content">
            <p>${escapeHtml(message)}</p>
        </div>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
    `;

    // 添加到页面
    document.body.appendChild(notification);

    // 添加动画
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // 绑定关闭事件
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    });

    // 自动关闭
    setTimeout(() => {
        if (notification.parentNode) {
            closeBtn.click();
        }
    }, 5000);

    // 添加到状态
    AppState.notifications.push({
        message,
        type,
        timestamp: new Date()
    });
}

// 获取通知图标
function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// 格式化时间
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

    return date.toLocaleDateString();
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 添加通知样式
function addNotificationStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            bottom: 1rem;
            right: 1rem;
            background: var(--color-bg-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            padding: var(--space-3) var(--space-4);
            display: flex;
            align-items: center;
            gap: var(--space-3);
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            max-width: 24rem;
            opacity: 0;
            transform: translateY(16px) scale(0.98);
            transition: opacity 0.25s ease, transform 0.25s ease;
            backdrop-filter: blur(6px);
        }

        .notification.show {
            opacity: 1;
            transform: translateY(0) scale(1);
        }

        .notification-icon {
            font-size: 1.25rem;
            flex-shrink: 0;
        }

        .notification-info .notification-icon {
            color: var(--color-info);
        }

        .notification-success .notification-icon {
            color: var(--color-success);
        }

        .notification-warning .notification-icon {
            color: var(--color-warning);
        }

        .notification-error .notification-icon {
            color: var(--color-error);
        }

        .notification-content {
            flex: 1;
            font-size: var(--font-size-sm);
        }

        .notification-close {
            background: none;
            border: none;
            color: var(--color-text-tertiary);
            cursor: pointer;
            padding: var(--space-1);
            border-radius: var(--radius-sm);
            flex-shrink: 0;
        }

        .notification-close:hover {
            background: var(--color-bg-surface-hover);
            color: var(--color-text-primary);
        }
    `;
    document.head.appendChild(style);
}

// 添加预览成功样式
function addPreviewSuccessStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .preview-success {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: var(--space-8);
            text-align: center;
        }

        .preview-success-icon {
            font-size: 3rem;
            color: var(--color-success);
            margin-bottom: var(--space-4);
        }
    `;
    document.head.appendChild(style);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    addNotificationStyles();
    addPreviewSuccessStyles();
    initApp();
});

// 绑定工具箱事件
function bindToolboxEvents() {
    initNavigationTool();
    initScreenshotTool();
}

// 初始化导航工具
function initNavigationTool() {
    const navGrid = document.getElementById('toolNavGrid');
    const addBtn = document.getElementById('toolAddNavBtn');
    
    if (!navGrid || !addBtn) return;

    // 默认导航数据
    const defaultNavs = [
        { name: 'ChatGPT', url: 'https://chat.openai.com', icon: 'https://chat.openai.com/favicon.ico' },
        { name: 'Bilibili', url: 'https://www.bilibili.com', icon: 'https://www.bilibili.com/favicon.ico' },
        { name: '知乎', url: 'https://www.zhihu.com', icon: 'https://static.zhihu.com/heifetz/favicon.ico' },
        { name: 'GitHub', url: 'https://github.com', icon: 'https://github.com/favicon.ico' },
        { name: 'Google', url: 'https://www.google.com', icon: 'https://www.google.com/favicon.ico' }
    ];

    // 加载导航数据
    function loadNavs() {
        const saved = localStorage.getItem('toolbox_navs');
        return saved ? JSON.parse(saved) : defaultNavs;
    }

    // 保存导航数据
    function saveNavs(navs) {
        localStorage.setItem('toolbox_navs', JSON.stringify(navs));
        renderNavs();
    }

    // 渲染导航网格
    function renderNavs() {
        const navs = loadNavs();
        navGrid.innerHTML = navs.map((nav, index) => `
            <div class="toolbox-nav-item" style="position: relative;">
                <a href="${nav.url}" target="_blank" class="toolbox-nav-link" style="display: flex; flex-direction: column; align-items: center; padding: 1rem; background: var(--color-bg-surface-hover); border-radius: var(--radius-md); text-decoration: none; color: var(--color-text-primary); transition: all 0.2s; width: 100%; height: 100%;">
                    <img src="${nav.icon}" onerror="this.src='https://www.google.com/s2/favicons?domain=${nav.url}'" style="width: 32px; height: 32px; margin-bottom: 0.5rem; border-radius: 4px;">
                    <span style="font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;">${escapeHtml(nav.name)}</span>
                </a>
                <button class="btn-delete-nav" data-index="${index}" style="position: absolute; top: -5px; right: -5px; width: 20px; height: 20px; border-radius: 50%; background: var(--color-error); color: white; border: none; cursor: pointer; display: none; align-items: center; justify-content: center; font-size: 10px; z-index: 10;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        // 添加删除按钮事件
        navGrid.querySelectorAll('.toolbox-nav-item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                const btn = item.querySelector('.btn-delete-nav');
                if (btn) btn.style.display = 'flex';
            });
            item.addEventListener('mouseleave', () => {
                const btn = item.querySelector('.btn-delete-nav');
                if (btn) btn.style.display = 'none';
            });
        });

        navGrid.querySelectorAll('.btn-delete-nav').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault(); // 防止触发链接跳转
                const index = parseInt(btn.dataset.index);
                const currentNavs = loadNavs();
                currentNavs.splice(index, 1);
                saveNavs(currentNavs);
            });
        });
    }

    // 添加导航
    addBtn.addEventListener('click', () => {
        const name = prompt('请输入网站名称：');
        if (!name) return;
        
        let url = prompt('请输入网站地址：', 'https://');
        if (!url) return;

        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }

        const currentNavs = loadNavs();
        currentNavs.push({
            name,
            url,
            icon: `https://www.google.com/s2/favicons?domain=${url}` // 使用 Google Favicon API 作为默认图标源
        });
        saveNavs(currentNavs);
    });

    // 初始渲染
    renderNavs();
}

// 初始化截图工具
function initScreenshotTool() {
    const screenshotBtn = document.getElementById('toolScreenshotBtn');
    const shortcutInput = document.getElementById('toolScreenshotShortcut');
    const clearShortcutBtn = document.getElementById('toolClearShortcutBtn');
    const autoCopyCheckbox = document.getElementById('toolAutoCopy');

    if (!screenshotBtn) return;

    
// 加载设置
    const settings = JSON.parse(localStorage.getItem('toolbox_screenshot_settings') || '{"shortcut": "", "autoCopy": true}');
    if (shortcutInput) shortcutInput.value = settings.shortcut;
    if (autoCopyCheckbox) autoCopyCheckbox.checked = settings.autoCopy;

    // 保存设置
    function saveSettings() {
        const newSettings = {
            shortcut: shortcutInput.value,
            autoCopy: autoCopyCheckbox.checked
        };
        localStorage.setItem('toolbox_screenshot_settings', JSON.stringify(newSettings));
    }

    // 截图功能
    async function takeScreenshot() {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: "always" },
                audio: false
            });

            const video = document.createElement("video");
            video.srcObject = stream;
            video.play();

            // 等待视频加载
            await new Promise(resolve => video.onloadedmetadata = resolve);

            // 创建画布并截图
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            // 停止所有轨道
            stream.getTracks().forEach(track => track.stop());

            // 打开裁剪器
            openCropper(canvas);

        } catch (err) {
            console.error("截图失败:", err);
            if (err.name !== 'NotAllowedError') {
                showNotification('截图失败: ' + err.message, 'error');
            }
        }
    }

    // 裁剪器逻辑
    function openCropper(sourceCanvas) {
        const modal = document.getElementById('screenshot-cropper');
        const img = document.getElementById('cropper-img');
        const wrapper = document.getElementById('cropper-wrapper');
        const selection = document.getElementById('cropper-selection');
        const sizeDisplay = document.getElementById('cropper-size');
        const confirmBtn = document.getElementById('cropperConfirmBtn');
        const cancelBtn = document.getElementById('cropperCancelBtn');

        if (!modal || !img) return;

        // 显示模态框
        modal.style.display = 'flex';
        img.src = sourceCanvas.toDataURL();

        // 状态
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        let rect = { x: 0, y: 0, w: 0, h: 0 };

        // 重置选择
        selection.style.display = 'none';
        rect = { x: 0, y: 0, w: 0, h: 0 };

        // 鼠标事件
        function handleMouseDown(e) {
            if (e.target.closest('.cropper-toolbar')) return;
            isDragging = true;
            const bounds = wrapper.getBoundingClientRect();
            startX = e.clientX - bounds.left;
            startY = e.clientY - bounds.top;
            
            // 允许反向拖拽
            rect.x = startX;
            rect.y = startY;
            rect.w = 0;
            rect.h = 0;

            selection.style.display = 'block';
            updateSelection();
            e.preventDefault();
        }

        function handleMouseMove(e) {
            if (!isDragging) return;
            const bounds = wrapper.getBoundingClientRect();
            const currentX = Math.max(0, Math.min(e.clientX - bounds.left, bounds.width));
            const currentY = Math.max(0, Math.min(e.clientY - bounds.top, bounds.height));

            rect.x = Math.min(startX, currentX);
            rect.y = Math.min(startY, currentY);
            rect.w = Math.abs(currentX - startX);
            rect.h = Math.abs(currentY - startY);

            updateSelection();
        }

        function handleMouseUp() {
            isDragging = false;
        }

        function updateSelection() {
            selection.style.left = rect.x + 'px';
            selection.style.top = rect.y + 'px';
            selection.style.width = rect.w + 'px';
            selection.style.height = rect.h + 'px';
            
            // 计算实际像素尺寸
            const scaleX = sourceCanvas.width / img.offsetWidth;
            const scaleY = sourceCanvas.height / img.offsetHeight;
            const realW = Math.round(rect.w * scaleX);
            const realH = Math.round(rect.h * scaleY);
            sizeDisplay.textContent = `${realW} x ${realH}`;
        }

        // 绑定事件
        wrapper.onmousedown = handleMouseDown;
        window.onmousemove = handleMouseMove;
        window.onmouseup = handleMouseUp;

        // 确认裁剪
        const handleConfirm = () => {
            // 如果没有选择区域，则使用全图
            if (rect.w === 0 || rect.h === 0) {
                rect.x = 0;
                rect.y = 0;
                rect.w = img.offsetWidth;
                rect.h = img.offsetHeight;
            }

            const scaleX = sourceCanvas.width / img.offsetWidth;
            const scaleY = sourceCanvas.height / img.offsetHeight;

            const finalCanvas = document.createElement('canvas');
            finalCanvas.width = rect.w * scaleX;
            finalCanvas.height = rect.h * scaleY;
            
            const ctx = finalCanvas.getContext('2d');
            ctx.drawImage(sourceCanvas, 
                rect.x * scaleX, rect.y * scaleY, rect.w * scaleX, rect.h * scaleY,
                0, 0, finalCanvas.width, finalCanvas.height
            );

            finalCanvas.toBlob(async (blob) => {
                if (autoCopyCheckbox.checked) {
                    try {
                        await navigator.clipboard.write([
                            new ClipboardItem({ [blob.type]: blob })
                        ]);
                        showNotification('截图已复制到剪贴板', 'success');
                    } catch (err) {
                        console.error('复制失败:', err);
                        showNotification('自动复制失败', 'warning');
                    }
                }

                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `screenshot_${new Date().getTime()}.png`;
                a.click();
                URL.revokeObjectURL(url);
                
                closeCropper();
            }, 'image/png');
        };

        // 取消
        const handleCancel = () => {
            closeCropper();
        };

        // 关闭清理
        function closeCropper() {
            modal.style.display = 'none';
            wrapper.onmousedown = null;
            window.onmousemove = null;
            window.onmouseup = null;
            confirmBtn.onclick = null;
            cancelBtn.onclick = null;
            // 清理内存
            img.src = '';
        }

        confirmBtn.onclick = handleConfirm;
        cancelBtn.onclick = handleCancel;
        
        // 双击确认
        wrapper.ondblclick = handleConfirm;
    }

    // 绑定按钮事件
    screenshotBtn.addEventListener('click', takeScreenshot);

    // 绑定快捷键设置
    if (shortcutInput) {
        shortcutInput.addEventListener('keydown', (e) => {
            e.preventDefault();
            const keys = [];
            if (e.ctrlKey) keys.push('Ctrl');
            if (e.shiftKey) keys.push('Shift');
            if (e.altKey) keys.push('Alt');
            if (e.metaKey) keys.push('Meta');
            
            // 忽略单独的修饰键
            if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return;
            
            keys.push(e.key.toUpperCase());
            shortcutInput.value = keys.join('+');
            saveSettings();
        });
    }

    if (clearShortcutBtn) {
        clearShortcutBtn.addEventListener('click', () => {
            shortcutInput.value = '';
            saveSettings();
        });
    }

    if (autoCopyCheckbox) {
        autoCopyCheckbox.addEventListener('change', saveSettings);
    }

    // 全局快捷键监听
    document.addEventListener('keydown', (e) => {
        const currentShortcut = shortcutInput.value;
        if (!currentShortcut) return;

        const keys = [];
        if (e.ctrlKey) keys.push('Ctrl');
        if (e.shiftKey) keys.push('Shift');
        if (e.altKey) keys.push('Alt');
        if (e.metaKey) keys.push('Meta');
        
        if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return;
        
        keys.push(e.key.toUpperCase());
        const pressedShortcut = keys.join('+');

        if (pressedShortcut === currentShortcut) {
            e.preventDefault();
            takeScreenshot();
        }
    });
}

// 导出到全局
window.App = {
    state: AppState,
    showPage,
    showNotification,
    setTheme,
    // API密钥管理函数
    setCurrentKey,
    testSpecificKey,
    deleteApiKey,
    // 其他实用函数
    addActivity,
    updateDashboardStats
};


















