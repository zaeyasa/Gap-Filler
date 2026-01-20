/**
 * Gap Filler Installer - JavaScript
 * Setup wizard logic and flow control
 */

// State
let currentStep = 1;
let ollamaStatus = { installed: false, running: false };
let modelInstalled = false;
let defaultModel = '';

// DOM Elements
const steps = document.querySelectorAll('.step');
const stepContents = document.querySelectorAll('.step-content');
const btnNext = document.getElementById('btn-next');
const btnBack = document.getElementById('btn-back');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    defaultModel = await window.gapFiller.getDefaultModel();
    document.getElementById('model-name').textContent = defaultModel;

    // Model pull progress listener
    window.gapFiller.onModelPullProgress(({ percent, status }) => {
        updateProgress(percent || 0, status || 'İndiriliyor...');
        addLog(`📥 ${status}`, 'info');
    });

    updateButtons();
});

// Navigation
btnNext.addEventListener('click', () => {
    handleNext();
});

btnBack.addEventListener('click', () => {
    if (currentStep > 1) {
        goToStep(currentStep - 1);
    }
});

async function handleNext() {
    switch (currentStep) {
        case 1:
            goToStep(2);
            await checkDependencies();
            break;
        case 2:
            goToStep(3);
            await runInstallation();
            break;
        case 3:
            goToStep(4);
            break;
        case 4:
            await finishSetup();
            break;
    }
}

function goToStep(step) {
    // Update step indicators
    steps.forEach((el, index) => {
        el.classList.remove('active');
        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });

    // Update content
    stepContents.forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${step}`).classList.add('active');

    currentStep = step;
    updateButtons();
}

function updateButtons() {
    // Back button
    btnBack.style.visibility = currentStep > 1 && currentStep < 4 ? 'visible' : 'hidden';

    // Next button text
    switch (currentStep) {
        case 1:
            btnNext.textContent = 'Başla →';
            btnNext.disabled = false;
            break;
        case 2:
            btnNext.textContent = 'Kuruluma Geç →';
            btnNext.disabled = true; // Enable after check
            break;
        case 3:
            btnNext.textContent = 'Bekleyin...';
            btnNext.disabled = true;
            break;
        case 4:
            btnNext.textContent = 'Gap Filler\'ı Başlat 🚀';
            btnNext.disabled = false;
            break;
    }
}

// ============================================================================
// Step 2: Dependency Check
// ============================================================================

async function checkDependencies() {
    const depOllama = document.getElementById('dep-ollama');
    const depModel = document.getElementById('dep-model');
    const actionInfo = document.getElementById('action-info');

    // Check Ollama
    updateDepStatus(depOllama, 'checking', 'Kontrol ediliyor...');
    ollamaStatus = await window.gapFiller.checkOllama();

    if (ollamaStatus.installed && ollamaStatus.running) {
        updateDepStatus(depOllama, 'success', 'Yüklü ve çalışıyor ✓');

        // Check model
        updateDepStatus(depModel, 'checking', `${defaultModel} kontrol ediliyor...`);
        modelInstalled = await window.gapFiller.checkModel(defaultModel);

        if (modelInstalled) {
            updateDepStatus(depModel, 'success', `${defaultModel} yüklü ✓`);
            showActionInfo(actionInfo, 'success',
                '✅ Tüm Gereksinimler Hazır!',
                'Sistem kurulum için hazır. Devam edebilirsiniz.'
            );
        } else {
            updateDepStatus(depModel, 'warning', `${defaultModel} yüklenmesi gerekiyor`);
            showActionInfo(actionInfo, 'warning',
                '📥 Model İndirilecek',
                `${defaultModel} modeli indirilecek. Bu işlem internet hızınıza bağlı olarak birkaç dakika sürebilir.`
            );
        }
    } else if (ollamaStatus.installed) {
        updateDepStatus(depOllama, 'warning', 'Yüklü ama çalışmıyor');
        updateDepStatus(depModel, 'pending', 'Ollama başlatılmalı');
        showActionInfo(actionInfo, 'warning',
            '🔄 Ollama Başlatılacak',
            'Ollama yüklü ancak çalışmıyor. Kurulum sırasında otomatik başlatılacak.'
        );
    } else {
        updateDepStatus(depOllama, 'error', 'Yüklü değil');
        updateDepStatus(depModel, 'pending', 'Önce Ollama gerekli');
        showActionInfo(actionInfo, 'warning',
            '📥 Ollama Kurulacak',
            'Ollama sisteminizde bulunamadı. Kurulum sırasında otomatik olarak indirilip yüklenecek. Bu işlem birkaç dakika sürebilir.'
        );
    }

    // Enable next button
    btnNext.textContent = 'Kuruluma Geç →';
    btnNext.disabled = false;
}

function updateDepStatus(element, status, text) {
    const iconEl = element.querySelector('.dep-icon');
    const statusEl = element.querySelector('.dep-status');

    statusEl.textContent = text;

    switch (status) {
        case 'checking':
            iconEl.innerHTML = '<span class="spinner"></span>';
            break;
        case 'success':
            iconEl.innerHTML = '<span class="success">✓</span>';
            break;
        case 'warning':
            iconEl.innerHTML = '<span style="color: #fbbf24; font-size: 24px;">⚠️</span>';
            break;
        case 'error':
            iconEl.innerHTML = '<span class="error">✗</span>';
            break;
        case 'pending':
            iconEl.innerHTML = '<span class="pending">⏳</span>';
            break;
    }
}

function showActionInfo(element, type, title, desc) {
    element.style.display = 'block';
    element.querySelector('.action-title').textContent = title;
    element.querySelector('.action-desc').textContent = desc;

    // Update border color based on type
    if (type === 'success') {
        element.style.borderColor = 'rgba(74, 222, 128, 0.3)';
        element.style.background = 'rgba(74, 222, 128, 0.1)';
        element.querySelector('.action-title').style.color = '#4ade80';
    }
}

// ============================================================================
// Step 3: Installation
// ============================================================================

async function runInstallation() {
    const progressFill = document.getElementById('progress-fill');
    const logContainer = document.getElementById('install-log');
    logContainer.innerHTML = '';

    let progress = 0;

    try {
        // Step 1: Install Ollama if needed
        if (!ollamaStatus.installed) {
            addLog('🔍 Ollama bulunamadı, indiriliyor...', 'info');
            updateProgress(5, 'Ollama indiriliyor...');

            const downloadResult = await window.gapFiller.downloadOllama();
            if (!downloadResult.success) {
                throw new Error(`Ollama indirilemedi: ${downloadResult.error}`);
            }

            addLog('✓ Ollama indirildi', 'success');
            updateProgress(20, 'Ollama kuruluyor...');

            addLog('📦 Ollama sessiz kurulum başlatılıyor...', 'info');
            addLog('⏳ Bu işlem birkaç dakika sürebilir, lütfen bekleyin...', 'warning');

            const installResult = await window.gapFiller.installOllama(downloadResult.path);
            if (!installResult.success) {
                throw new Error(`Ollama kurulamadı: ${installResult.error}`);
            }

            addLog('✓ Ollama başarıyla kuruldu', 'success');
            updateProgress(40, 'Ollama başlatılıyor...');
        } else {
            addLog('✓ Ollama zaten yüklü', 'success');
            updateProgress(40, 'Ollama kontrol ediliyor...');
        }

        // Step 2: Start Ollama if needed
        if (!ollamaStatus.running) {
            addLog('🔄 Ollama servisi başlatılıyor...', 'info');
            await window.gapFiller.startOllama();

            // Wait a bit for service to start
            await sleep(3000);

            // Check again
            const newStatus = await window.gapFiller.checkOllama();
            if (newStatus.running) {
                addLog('✓ Ollama servisi başlatıldı', 'success');
            } else {
                addLog('⚠️ Ollama başlatılamadı, manuel başlatma gerekebilir', 'warning');
            }
        } else {
            addLog('✓ Ollama zaten çalışıyor', 'success');
        }

        updateProgress(50, 'Model kontrol ediliyor...');

        // Step 3: Pull model if needed
        if (!modelInstalled) {
            addLog(`📥 ${defaultModel} modeli indiriliyor...`, 'info');
            addLog('⏳ Model boyutuna göre bu işlem 5-15 dakika sürebilir...', 'warning');

            updateProgress(55, 'Model indiriliyor...');

            const pullResult = await window.gapFiller.pullModel(defaultModel);
            if (!pullResult.success) {
                throw new Error(`Model indirilemedi: ${pullResult.error}`);
            }

            addLog(`✓ ${defaultModel} başarıyla indirildi`, 'success');
        } else {
            addLog(`✓ ${defaultModel} zaten mevcut`, 'success');
        }

        updateProgress(90, 'Backend başlatılıyor...');

        // Step 4: Start backend
        addLog('🚀 Gap Filler backend başlatılıyor...', 'info');
        const backendResult = await window.gapFiller.startBackend();
        if (backendResult.success) {
            addLog('✓ Backend başarıyla başlatıldı', 'success');
        } else {
            addLog('⚠️ Backend başlatılamadı, uygulama içinden başlatılacak', 'warning');
        }

        updateProgress(100, 'Tamamlandı!');
        addLog('🎉 Kurulum tamamlandı!', 'success');

        // Auto proceed to step 4
        await sleep(1500);
        goToStep(4);

    } catch (error) {
        addLog(`❌ Hata: ${error.message}`, 'error');
        btnNext.textContent = 'Tekrar Dene';
        btnNext.disabled = false;
        btnNext.onclick = () => runInstallation();
    }
}

function updateProgress(percent, text) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressFill.style.width = `${percent}%`;
    progressText.textContent = text;
}

function addLog(message, type = 'info') {
    const logContainer = document.getElementById('install-log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = message;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// ============================================================================
// Step 4: Finish
// ============================================================================

async function finishSetup() {
    btnNext.disabled = true;
    btnNext.textContent = 'Başlatılıyor...';
    await window.gapFiller.finishSetup();
}

// ============================================================================
// Utilities
// ============================================================================

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
