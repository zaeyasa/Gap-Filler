/**
 * GAP Filler - Frontend Application
 * Handles API communication and UI updates
 */

// Configuration
const API_BASE = 'http://127.0.0.1:5000/api';
const MAX_HISTORY_ITEMS = 10;

// State
let state = {
    species: [],
    models: [],
    currentModel: '',
    analysisResults: null,
    theme: localStorage.getItem('gap-filler-theme') || 'dark',
    searchHistory: JSON.parse(localStorage.getItem('gap-filler-history') || '[]'),
    // v3.0 - Selected gene for tools
    selectedGene: null,
    selectedSourceSpecies: null,
    selectedTargetSpecies: null
};

// ============================================================================
// Theme Toggle Functions
// ============================================================================

function toggleTheme() {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function setTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gap-filler-theme', theme);

    // Update icon
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.textContent = theme === 'dark' ? '🌙' : '☀️';
    }
}

function initTheme() {
    // Apply saved theme on page load
    setTheme(state.theme);
}

// ============================================================================
// Search History Functions
// ============================================================================

function addToSearchHistory(query, sourceSpecies, targetSpecies, resultsCount) {
    const historyItem = {
        query,
        sourceSpecies,
        targetSpecies,
        resultsCount,
        timestamp: new Date().toISOString(),
        id: Date.now()
    };

    // Add to beginning of array
    state.searchHistory.unshift(historyItem);

    // Keep only last N items
    if (state.searchHistory.length > MAX_HISTORY_ITEMS) {
        state.searchHistory = state.searchHistory.slice(0, MAX_HISTORY_ITEMS);
    }

    // Save to localStorage
    localStorage.setItem('gap-filler-history', JSON.stringify(state.searchHistory));

    // Update UI
    renderSearchHistory();
}

function toggleSearchHistory() {
    const menu = document.getElementById('history-menu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        if (menu.style.display === 'block') {
            renderSearchHistory();
        }
    }
}

function renderSearchHistory() {
    const list = document.getElementById('history-list');
    if (!list) return;

    if (state.searchHistory.length === 0) {
        list.innerHTML = '<div class="history-empty">No recent searches</div>';
        return;
    }

    list.innerHTML = state.searchHistory.map(item => `
        <div class="history-item" onclick="loadFromHistory(${item.id})">
            <div class="history-query">${item.query}</div>
            <div class="history-meta">
                ${item.sourceSpecies} → ${item.targetSpecies.length} species • 
                ${item.resultsCount || 0} gaps • 
                ${formatTimeAgo(item.timestamp)}
            </div>
        </div>
    `).join('');
}

function loadFromHistory(itemId) {
    const item = state.searchHistory.find(h => h.id === itemId);
    if (!item) return;

    // Fill in the form
    document.getElementById('search-input').value = item.query;

    // Set source species
    const sourceSelect = document.getElementById('source-species');
    if (sourceSelect) sourceSelect.value = item.sourceSpecies;

    // Set target species checkboxes
    if (item.targetSpecies) {
        document.querySelectorAll('#target-species input').forEach(cb => {
            cb.checked = item.targetSpecies.includes(cb.value);
        });
    }

    // Close menu
    toggleSearchHistory();
}

function clearSearchHistory() {
    state.searchHistory = [];
    localStorage.removeItem('gap-filler-history');
    renderSearchHistory();
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

// Close history dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('search-history-dropdown');
    const menu = document.getElementById('history-menu');
    if (dropdown && menu && !dropdown.contains(e.target)) {
        menu.style.display = 'none';
    }
});

// ============================================================================
// Personal Notes Functions
// ============================================================================

function getGeneNotes(gene, species) {
    const key = `gap-filler-note-${gene}-${species}`;
    return localStorage.getItem(key) || '';
}

function saveGeneNote(gene, species, note) {
    const key = `gap-filler-note-${gene}-${species}`;
    if (note.trim()) {
        localStorage.setItem(key, note);
    } else {
        localStorage.removeItem(key);
    }
    // Update save indicator
    const indicator = document.getElementById(`note-save-indicator-${gene.replace(/[^a-zA-Z0-9]/g, '')}`);
    if (indicator) {
        indicator.textContent = '✓ Saved';
        indicator.classList.add('saved');
        setTimeout(() => {
            indicator.textContent = '';
            indicator.classList.remove('saved');
        }, 2000);
    }
}

function getAllSavedNotes() {
    const notes = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith('gap-filler-note-')) {
            const parts = key.replace('gap-filler-note-', '').split('-');
            const gene = parts[0];
            const species = parts.slice(1).join('-');
            notes.push({
                gene,
                species,
                note: localStorage.getItem(key),
                key
            });
        }
    }
    return notes;
}

// Notes Modal Functions
function openNotesModal(gene, species) {
    const savedNote = getGeneNotes(gene, species);

    // Create modal if it doesn't exist
    let modal = document.getElementById('notes-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'notes-modal';
        modal.className = 'modal-overlay';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="modal-content notes-modal-content">
            <div class="modal-header">
                <h3>📝 Notes: ${gene}</h3>
                <button class="modal-close" onclick="closeNotesModal()">✕</button>
            </div>
            <div class="modal-body">
                <p class="notes-species">Species: <em>${species}</em></p>
                <textarea 
                    id="modal-note-textarea"
                    class="modal-textarea"
                    placeholder="Add your research notes about ${gene} in ${species}..."
                >${savedNote}</textarea>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeNotesModal()">Cancel</button>
                <button class="btn-primary" onclick="saveNoteFromModal('${gene}', '${species}')">
                    💾 Save Note
                </button>
            </div>
        </div>
    `;

    modal.style.display = 'flex';
    document.getElementById('modal-note-textarea').focus();
}

function closeNotesModal() {
    const modal = document.getElementById('notes-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function saveNoteFromModal(gene, species) {
    const textarea = document.getElementById('modal-note-textarea');
    if (textarea) {
        saveGeneNote(gene, species, textarea.value);

        // Update the notes button indicator
        const hasNote = textarea.value.trim().length > 0;
        document.querySelectorAll('.notes-btn').forEach(btn => {
            if (btn.onclick.toString().includes(gene) && btn.onclick.toString().includes(species)) {
                btn.classList.toggle('has-note', hasNote);
                btn.innerHTML = `📝 ${hasNote ? '1' : ''}`;
            }
        });
    }
    closeNotesModal();
}

// ============================================================================
// PDF Export Functions
// ============================================================================

async function exportPDF() {
    if (!state.analysisResults) {
        alert('No analysis results to export. Run a search first.');
        return;
    }

    // Open export options modal
    openExportModal();
}

function openExportModal() {
    const gaps = state.analysisResults.gaps || [];

    // Create modal if it doesn't exist
    let modal = document.getElementById('export-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'export-modal';
        modal.className = 'modal-overlay';
        document.body.appendChild(modal);
    }

    // Build organism checkboxes
    const orgCheckboxes = gaps.map((gap, idx) => `
        <label class="export-org-item">
            <input type="checkbox" name="export-org" value="${gap.species}" checked>
            <span class="org-name">${gap.species}</span>
            <span class="org-count">(${gap.gap_count} gaps)</span>
        </label>
    `).join('');

    modal.innerHTML = `
        <div class="modal-content export-modal-content">
            <div class="modal-header">
                <h3>📄 Export PDF Report</h3>
                <button class="modal-close" onclick="closeExportModal()">✕</button>
            </div>
            <div class="modal-body">
                <p class="export-instructions">Select organisms to include in the report:</p>
                
                <div class="export-actions-top">
                    <button class="btn-small" onclick="selectAllExportOrgs(true)">Select All</button>
                    <button class="btn-small" onclick="selectAllExportOrgs(false)">Deselect All</button>
                </div>
                
                <div class="export-org-list">
                    ${orgCheckboxes}
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeExportModal()">Cancel</button>
                <button class="btn-primary" onclick="generatePDFWithSelection()">
                    📄 Generate PDF
                </button>
            </div>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeExportModal() {
    const modal = document.getElementById('export-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function selectAllExportOrgs(selectAll) {
    document.querySelectorAll('input[name="export-org"]').forEach(cb => {
        cb.checked = selectAll;
    });
}

async function generatePDFWithSelection() {
    const selectedOrgs = Array.from(document.querySelectorAll('input[name="export-org"]:checked'))
        .map(cb => cb.value);

    if (selectedOrgs.length === 0) {
        alert('Please select at least one organism to export.');
        return;
    }

    closeExportModal();

    const exportBtn = document.getElementById('export-pdf-btn');
    const originalText = exportBtn.innerHTML;
    exportBtn.innerHTML = '⏳ Generating...';
    exportBtn.disabled = true;

    // Filter gaps to only selected organisms
    const filteredGaps = (state.analysisResults.gaps || []).filter(
        gap => selectedOrgs.includes(gap.species)
    );

    try {
        const response = await fetch(`${API_BASE}/export/pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: state.analysisResults.query || document.getElementById('search-input').value,
                source_species: document.getElementById('source-species').value,
                target_species: selectedOrgs,
                gaps: filteredGaps,
                genes: state.analysisResults.genes || [],
                summaries: state.analysisResults.summaries || []
            })
        });

        if (!response.ok) {
            throw new Error('Failed to generate PDF');
        }

        // Get the blob and download
        const blob = await response.blob();
        const pdfBlob = new Blob([blob], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(pdfBlob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = new Date().toISOString().slice(0, 10);
        a.download = `gap_report_${timestamp}.pdf`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);

        exportBtn.innerHTML = '✅ Downloaded!';
        setTimeout(() => {
            exportBtn.innerHTML = originalText;
        }, 2000);

    } catch (error) {
        console.error('PDF export failed:', error);
        alert('Failed to export PDF. Please try again.');
        exportBtn.innerHTML = originalText;
    } finally {
        exportBtn.disabled = false;
    }
}

// ============================================================================
// API Functions
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API request failed: ${endpoint}`, error);
        throw error;
    }
}

async function checkStatus() {
    try {
        const status = await apiRequest('/status');
        updateStatusIndicator(status);
        return status;
    } catch (error) {
        updateStatusIndicator({ api: 'error', error: error.message });
        return null;
    }
}

async function loadSpecies() {
    try {
        const data = await apiRequest('/species');
        state.species = data.species || [];
        populateSpeciesSelects();
    } catch (error) {
        console.error('Failed to load species:', error);
    }
}

async function loadModels() {
    try {
        const data = await apiRequest('/models');
        state.models = data.models || [];
        state.currentModel = data.current_model || '';
        populateModelSelect();
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

async function setModel(modelName) {
    try {
        const data = await apiRequest('/models/set', {
            method: 'POST',
            body: JSON.stringify({ model: modelName })
        });
        state.currentModel = data.current_model;
    } catch (error) {
        console.error('Failed to set model:', error);
    }
}

async function analyzeGaps(query, sourceSpecies, targetSpecies, maxArticles, model) {
    return await apiRequest('/analyze', {
        method: 'POST',
        body: JSON.stringify({
            query,
            source_species: sourceSpecies,
            target_species: targetSpecies,
            max_articles: maxArticles,
            model: model || null
        })
    });
}

async function fetchPublications(gene, species, maxResults = 5) {
    return await apiRequest('/publications', {
        method: 'POST',
        body: JSON.stringify({
            gene,
            species,
            max_results: maxResults
        })
    });
}

// ============================================================================
// UI Update Functions
// ============================================================================

function updateStatusIndicator(status) {
    const indicator = document.getElementById('status-indicator');
    const statusText = indicator.querySelector('.status-text');

    indicator.classList.remove('connected', 'error');

    if (status.api === 'running' && status.ollama?.status === 'connected') {
        indicator.classList.add('connected');
        statusText.textContent = `Connected • ${status.ollama.current_model}`;
    } else if (status.api === 'running') {
        indicator.classList.add('error');
        statusText.textContent = 'Ollama not connected';
    } else {
        indicator.classList.add('error');
        statusText.textContent = 'API not connected';
    }
}

function populateSpeciesSelects() {
    const sourceSelect = document.getElementById('source-species');
    const targetContainer = document.getElementById('target-species');

    // Populate source species dropdown
    sourceSelect.innerHTML = state.species.map(s =>
        `<option value="${s.scientific_name}" ${s.scientific_name === 'Arabidopsis thaliana' ? 'selected' : ''}>
            ${s.scientific_name} (${s.common_name})
        </option>`
    ).join('');

    // Populate target species checkboxes
    const defaultTargets = ['Triticum aestivum', 'Oryza sativa', 'Zea mays', 'Glycine max', 'Solanum lycopersicum'];

    targetContainer.innerHTML = state.species.map(s => `
        <label class="species-checkbox">
            <input type="checkbox" value="${s.scientific_name}" 
                   ${defaultTargets.includes(s.scientific_name) ? 'checked' : ''}>
            <span>${s.scientific_name}</span>
            <span class="common-name">(${s.common_name})</span>
        </label>
    `).join('');
}

function populateModelSelect() {
    const select = document.getElementById('model-select');

    if (state.models.length === 0) {
        select.innerHTML = '<option value="">No models available</option>';
        return;
    }

    select.innerHTML = state.models.map(model =>
        `<option value="${model}" ${model === state.currentModel ? 'selected' : ''}>
            ${model}
        </option>`
    ).join('');
}

function showLoading(text = 'Processing...') {
    document.getElementById('loading-state').style.display = 'flex';
    document.getElementById('loading-text').textContent = text;
    document.getElementById('results-container').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading-state').style.display = 'none';
}

function showResults(results) {
    state.analysisResults = results;

    hideLoading();
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('results-container').style.display = 'flex';

    renderStats(results);
    renderGaps(results.gaps || []);
    renderGenes(results.genes_found || []);
    renderSummaries(results.gene_summaries || {});
}

function renderStats(results) {
    const stats = results.statistics || {};
    const grid = document.getElementById('stats-grid');

    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${results.articles_analyzed || 0}</div>
            <div class="stat-label">Articles Analyzed</div>
        </div>
        <div class="stat-card purple">
            <div class="stat-value">${(results.genes_found || []).length}</div>
            <div class="stat-label">Genes Found</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-value">${stats.complete_gaps || stats.total_gaps || 0}</div>
            <div class="stat-label">Complete Gaps (0 pubs)</div>
        </div>
        <div class="stat-card warning">
            <div class="stat-value">${stats.species_with_gaps || 0}</div>
            <div class="stat-label">Species with Gaps</div>
        </div>
    `;
}

// Fetch GO Terms for a gene
async function fetchGOTerms(gene, species) {
    try {
        const response = await fetch(`${API_BASE}/go-terms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gene, species })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch GO terms');
        }

        return await response.json();
    } catch (error) {
        console.warn('GO terms fetch failed:', error);
        return { success: false, molecular_function: [], biological_process: [], cellular_component: [], pathways: [] };
    }
}

// Fetch Ortholog Info (Phase D & E)
async function fetchOrthologInfo(gene, sourceSpecies, targetSpecies) {
    try {
        const response = await fetch(`${API_BASE}/ortholog`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                gene,
                source_species: sourceSpecies,
                target_species: targetSpecies
            })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch ortholog info');
        }

        return await response.json();
    } catch (error) {
        console.warn('Ortholog info fetch failed:', error);
        return { success: false, ortholog_found: false, error: error.message };
    }
}

function renderGaps(gaps) {
    const list = document.getElementById('gaps-list');

    if (gaps.length === 0) {
        list.innerHTML = `
            <div class="empty-state" style="padding: 2rem;">
                <div class="empty-icon">✅</div>
                <h3>No Publication Gaps Found</h3>
                <p>All identified genes have publications in the selected target species.</p>
            </div>
        `;
        return;
    }

    // Store sourceSpecies for publication fetching
    const sourceSpecies = state.analysisResults?.source_species || 'Arabidopsis thaliana';

    list.innerHTML = gaps.map((gap, gapIdx) => `
        <div class="gap-card">
            <div class="gap-header" onclick="this.parentElement.classList.toggle('expanded')">
                <div class="gap-species">
                    <span class="scientific">${gap.species}</span>
                    <span class="common">${gap.common_name}</span>
                </div>
                <div class="gap-badges">
                    ${gap.complete_gaps ? `<span class="gap-badge complete">🔴 ${gap.complete_gaps} no pubs</span>` : ''}
                    ${gap.severe_gaps ? `<span class="gap-badge severe">🟠 ${gap.severe_gaps} low pubs</span>` : ''}
                    <span class="gap-count">🧬 ${gap.gap_count} total</span>
                </div>
            </div>
            <div class="gap-genes">
                ${(gap.missing_genes || []).map((g, geneIdx) => {
        const geneId = `${gapIdx}-${geneIdx}`;
        const savedNote = getGeneNotes(g.gene, gap.species);
        const hasNote = savedNote.trim().length > 0;
        const panelId = `pub-panel-${g.gene.replace(/[^a-zA-Z0-9]/g, '')}-${gap.species.replace(/[^a-zA-Z0-9]/g, '')}`;

        return `
                    <div class="gene-gap-item ${g.gap_level}" id="gene-${geneId}">
                        <div class="gene-gap-header" onclick="toggleGeneDetail('${gapIdx}', '${geneIdx}', '${g.gene}', '${sourceSpecies}', '${gap.species}')">
                            <div class="gene-gap-main">
                                <span class="gene-name-tag">${g.gene}</span>
                                ${g.priority_score ? `<span class="priority-badge" title="Research Priority Score">${g.priority_score}</span>` : ''}
                                <span class="pub-info">
                                    <span class="source-pubs" title="Publications in ${sourceSpecies}">📚 ${g.source_publications || '?'}</span>
                                    →
                                    <span class="target-pubs ${g.gap_level}" title="Publications in ${gap.species}">
                                        ${g.target_publications === 0 ? '❌ 0' : `⚠️ ${g.target_publications}`}
                                    </span>
                                </span>
                                <span class="gap-level-badge ${g.gap_level}">${formatGapLevel(g.gap_level)}</span>
                            </div>
                            <div class="gene-actions" onclick="event.stopPropagation()">
                                <button class="gene-action-btn select-tool-btn" 
                                        onclick="selectGeneForTools('${g.gene}', '${sourceSpecies}', '${gap.species}')" 
                                        title="Select for Funding/Proposal tools">🎯</button>
                                <button class="gene-action-btn filter-btn-small" onclick="toggleFilter('${panelId}', 'gwas', this)" title="Filter GWAS only">🧬</button>
                                <button class="gene-action-btn filter-btn-small" onclick="toggleFilter('${panelId}', 'functional', this)" title="Filter Functional only">🔬</button>
                                <button class="gene-action-btn notes-btn ${hasNote ? 'has-note' : ''}" 
                                        onclick="openNotesModal('${g.gene}', '${gap.species}')" 
                                        title="${hasNote ? 'Edit notes' : 'Add notes'}">
                                    📝${hasNote ? '¹' : ''}
                                </button>
                            </div>
                            <span class="expand-icon">▼</span>
                        </div>
                        <div class="gene-detail-panel" id="detail-${geneId}" style="display: none;">
                            <div class="loading-pubs">Loading publications...</div>
                        </div>
                    </div>
                `}).join('')}
            </div>
        </div>
    `).join('');
}

async function toggleGeneDetail(gapIdx, geneIdx, gene, sourceSpecies, targetSpecies) {
    const panel = document.getElementById(`detail-${gapIdx}-${geneIdx}`);
    const item = document.getElementById(`gene-${gapIdx}-${geneIdx}`);

    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        item.classList.add('expanded');

        // Check if already loaded
        if (panel.querySelector('.loading-pubs')) {
            try {
                // Fetch publications, GO terms, AND ortholog info in parallel
                const [sourcePubs, targetPubs, goTerms, orthologInfo] = await Promise.all([
                    fetchPublications(gene, sourceSpecies, 5),
                    fetchPublications(gene, targetSpecies, 5),
                    fetchGOTerms(gene, sourceSpecies),
                    fetchOrthologInfo(gene, sourceSpecies, targetSpecies)
                ]);

                panel.innerHTML = renderPublicationDetail(gene, sourceSpecies, sourcePubs, targetSpecies, targetPubs, goTerms, orthologInfo);
            } catch (error) {
                panel.innerHTML = `<div class="pub-error">Failed to load data: ${error.message}</div>`;
            }
        }
    } else {
        panel.style.display = 'none';
        item.classList.remove('expanded');
    }
}

function renderPublicationDetail(gene, sourceSpecies, sourcePubs, targetSpecies, targetPubs, goTerms = null, orthologInfo = null) {
    // Use unique ID per gene+species combo to avoid conflicts
    const uniqueId = `${gene.replace(/[^a-zA-Z0-9]/g, '')}-${targetSpecies.replace(/[^a-zA-Z0-9]/g, '')}`;
    const panelId = `pub-panel-${uniqueId}`;

    const hasTargetPubs = targetPubs.publications.length > 0;

    // Format trend emoji
    const getTrendIcon = (trend) => {
        switch (trend) {
            case 'increasing': return '📈';
            case 'decreasing': return '📉';
            default: return '➡️';
        }
    };

    // Format year range
    const formatYearRange = (yearRange) => {
        if (!yearRange) return '';
        if (yearRange.earliest === yearRange.latest) return `(${yearRange.earliest})`;
        return `(${yearRange.earliest}-${yearRange.latest})`;
    };

    return `
        <div class="pub-detail-content" id="${panelId}">
            <!-- Source Publications Section (collapsed by default) -->
            <div class="pub-accordion source">
                <div class="pub-accordion-header" onclick="togglePubSection(this)">
                    <span class="accordion-icon">▶</span>
                    <span class="accordion-title">📗 ${sourceSpecies}</span>
                    <span class="accordion-count">${sourcePubs.total_count >= 0 ? sourcePubs.total_count : '?'} pubs ${formatYearRange(sourcePubs.year_range)}</span>
                    <span class="trend-indicator" title="Research trend">${getTrendIcon(sourcePubs.trend)}</span>
                    <span class="accordion-badges">
                        ${sourcePubs.gwas_count > 0 ? `<span class="mini-badge gwas">${sourcePubs.gwas_count} GWAS</span>` : ''}
                        ${sourcePubs.functional_count > 0 ? `<span class="mini-badge func">${sourcePubs.functional_count} FUNC</span>` : ''}
                    </span>
                </div>
                <div class="pub-accordion-body" style="display: none;">
                    ${renderPubList(sourcePubs, sourceSpecies)}
                </div>
            </div>
            
            <!-- Target Publications Section (collapsed by default) -->
            <div class="pub-accordion target ${!hasTargetPubs ? 'is-gap' : ''}">
                <div class="pub-accordion-header" onclick="togglePubSection(this)">
                    <span class="accordion-icon">▶</span>
                    <span class="accordion-title">${hasTargetPubs ? '📙' : '🔴'} ${targetSpecies}</span>
                    <span class="accordion-count">${targetPubs.total_count >= 0 ? targetPubs.total_count : '?'} pubs ${formatYearRange(targetPubs.year_range)}</span>
                    ${hasTargetPubs ? `<span class="trend-indicator" title="Research trend">${getTrendIcon(targetPubs.trend)}</span>` : ''}
                    ${!hasTargetPubs ? '<span class="gap-label">Research Gap!</span>' : ''}
                </div>
                <div class="pub-accordion-body" style="display: none;">
                    ${hasTargetPubs ?
            renderPubList(targetPubs, targetSpecies) :
            `<div class="gap-opportunity">
                            <p class="no-pubs">❌ No publications found - <strong>Research opportunity!</strong></p>
                            <p class="gap-suggestion">This gene has been studied in ${sourceSpecies} but not yet in ${targetSpecies}.</p>
                        </div>`
        }
                </div>
            </div>
            
            <!-- GO Terms Section (collapsed by default) -->
            ${goTerms && goTerms.success ? `
            <div class="pub-accordion go-terms">
                <div class="pub-accordion-header" onclick="togglePubSection(this)">
                    <span class="accordion-icon">▶</span>
                    <span class="accordion-title">🏷️ Gene Function & Pathways</span>
                    <span class="accordion-count">${goTerms.description ? 'UniProt' : 'GO Terms'}</span>
                </div>
                <div class="pub-accordion-body" style="display: none;">
                    ${goTerms.description ? `<p class="go-description"><strong>Description:</strong> ${goTerms.description}</p>` : ''}
                    
                    ${goTerms.molecular_function.length > 0 ? `
                        <div class="go-category">
                            <h6>⚙️ Molecular Function</h6>
                            <ul>${goTerms.molecular_function.slice(0, 5).map(go =>
            `<li><span class="go-id">${go.id}</span> ${go.name}</li>`
        ).join('')}</ul>
                        </div>
                    ` : ''}
                    
                    ${goTerms.biological_process.length > 0 ? `
                        <div class="go-category">
                            <h6>🧬 Biological Process</h6>
                            <ul>${goTerms.biological_process.slice(0, 5).map(go =>
            `<li><span class="go-id">${go.id}</span> ${go.name}</li>`
        ).join('')}</ul>
                        </div>
                    ` : ''}
                    
                    ${goTerms.cellular_component.length > 0 ? `
                        <div class="go-category">
                            <h6>📍 Cellular Component</h6>
                            <ul>${goTerms.cellular_component.slice(0, 5).map(go =>
            `<li><span class="go-id">${go.id}</span> ${go.name}</li>`
        ).join('')}</ul>
                        </div>
                    ` : ''}
                    
                    ${goTerms.pathways && goTerms.pathways.length > 0 ? `
                        <div class="go-category">
                            <h6>🛤️ Pathways</h6>
                            <ul>${goTerms.pathways.slice(0, 5).map(pw =>
            `<li class="pathway-item">${pw}</li>`
        ).join('')}</ul>
                        </div>
                    ` : ''}
                </div>
            </div>
            ` : `
            <!-- GO Terms Not Found -->
            <div class="pub-accordion go-terms not-found">
                <div class="pub-accordion-header" onclick="togglePubSection(this)">
                    <span class="accordion-icon">▶</span>
                    <span class="accordion-title">🏷️ Gene Function & Pathways</span>
                    <span class="accordion-count">Not available</span>
                </div>
                <div class="pub-accordion-body" style="display: none;">
                    <p class="go-not-found">No GO term annotations found in UniProt/QuickGO for this gene. 
                    This could be because: (1) the gene uses a different symbol in UniProt, 
                    (2) it hasn't been annotated yet, or (3) pathway information isn't available.</p>
                </div>
            </div>
            `}
            
            <!-- Ortholog Info Section (Phase D & E) -->
            ${orthologInfo ? `
            <div class="pub-accordion ortholog-info">
                <div class="pub-accordion-header" onclick="togglePubSection(this)">
                    <span class="accordion-icon">▶</span>
                    <span class="accordion-title">🔀 Ortholog in ${targetSpecies.split(' ')[0]}</span>
                    ${orthologInfo.success && orthologInfo.ortholog_found ? `
                        <span class="accordion-count ortholog-confidence ${orthologInfo.ortholog.confidence}">
                            ${orthologInfo.ortholog.sequence_identity}% identity
                        </span>
                        <span class="ortholog-type-badge">${orthologInfo.ortholog.ortholog_type}</span>
                    ` : orthologInfo.success && !orthologInfo.ortholog_found ? `
                        <span class="accordion-count">Not found</span>
                    ` : `
                        <span class="accordion-count" style="color: var(--accent-warning);">API Error</span>
                    `}
                </div>
                <div class="pub-accordion-body" style="display: none;">
                    ${orthologInfo.success && orthologInfo.ortholog_found ? `
                        <div class="ortholog-details">
                            <div class="ortholog-stat">
                                <span class="stat-label">Sequence Identity</span>
                                <span class="stat-value">${orthologInfo.ortholog.sequence_identity}%</span>
                            </div>
                            <div class="ortholog-stat">
                                <span class="stat-label">Confidence</span>
                                <span class="stat-value confidence-${orthologInfo.ortholog.confidence}">
                                    ${orthologInfo.ortholog.confidence === 'high' ? '🟢 High' : orthologInfo.ortholog.confidence === 'medium' ? '🟡 Medium' : '🔴 Low'}
                                </span>
                            </div>
                            <div class="ortholog-stat">
                                <span class="stat-label">Ortholog Type</span>
                                <span class="stat-value">${orthologInfo.ortholog.ortholog_type}</span>
                            </div>
                            <div class="ortholog-stat">
                                <span class="stat-label">Target Gene ID</span>
                                <span class="stat-value">${orthologInfo.ortholog.target_gene || 'Unknown'}</span>
                            </div>
                            ${orthologInfo.ortholog.ensembl_url ? `
                                <a href="${orthologInfo.ortholog.ensembl_url}" target="_blank" class="ensembl-link">
                                    🔗 View in Ensembl Plants
                                </a>
                            ` : ''}
                        </div>
                    ` : orthologInfo.success && !orthologInfo.ortholog_found ? `
                        <p class="ortholog-not-found">No ortholog found for this gene in ${targetSpecies}. 
                        ${orthologInfo.message || 'The gene symbol may not be recognized by Ensembl Plants.'}</p>
                    ` : `
                        <p class="ortholog-not-found">⚠️ ${orthologInfo.error || 'Could not fetch ortholog data from Ensembl.'}
                        <br><br>This usually means the gene symbol "${gene}" is not in Ensembl's plant database. 
                        Try searching on <a href="https://plants.ensembl.org/Multi/Search/Results?q=${encodeURIComponent(gene)}" target="_blank" style="color: var(--accent-primary);">Ensembl Plants</a> directly.</p>
                    `}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

function renderPubList(pubs, species) {
    if (pubs.publications.length === 0) {
        return '<p class="no-pubs">No publications found</p>';
    }

    return `
        <ul class="pub-list">
            ${pubs.publications.map(pub => `
                <li class="pub-item" data-study-type="${pub.study_type || 'unknown'}">
                    <a href="${pub.url}" target="_blank" class="pub-link">
                        ${pub.is_gwas ? '<span class="gwas-badge">GWAS</span>' : '<span class="func-badge">FUNC</span>'}
                        <span class="pub-title">${pub.title}</span>
                        <span class="pub-meta">${pub.authors} • ${pub.journal} (${pub.year})</span>
                    </a>
                </li>
            `).join('')}
        </ul>
        ${pubs.total_count > 10 ? `
            <a href="https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(pubs.query)}" 
               target="_blank" class="view-all-link">
                View all ${pubs.total_count} publications on PubMed →
            </a>
        ` : ''}
    `;
}

// Toggle accordion section visibility
function togglePubSection(header) {
    const body = header.nextElementSibling;
    const icon = header.querySelector('.accordion-icon');

    if (body.style.display === 'none') {
        body.style.display = 'block';
        header.classList.add('open');
        icon.textContent = '▼';
    } else {
        body.style.display = 'none';
        header.classList.remove('open');
        icon.textContent = '▶';
    }
}

function filterPublications(panelId, filterType) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    // Update button states
    panel.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(filterType) ||
            (filterType === 'all' && btn.textContent.includes('All'))) {
            btn.classList.add('active');
        }
    });

    // Filter publications
    panel.querySelectorAll('.pub-item').forEach(item => {
        const studyType = item.dataset.studyType;

        if (filterType === 'all') {
            item.style.display = '';
        } else if (filterType === 'gwas') {
            item.style.display = studyType === 'gwas' ? '' : 'none';
        } else if (filterType === 'functional') {
            item.style.display = studyType === 'functional' ? '' : 'none';
        }
    });
}

// Toggle filter from header row buttons
function toggleFilter(panelId, filterType, button) {
    const panel = document.getElementById(panelId);

    // Toggle active state on button
    if (button.classList.contains('active')) {
        // Turn off filter - show all
        button.classList.remove('active');
        if (panel) {
            panel.querySelectorAll('.pub-item').forEach(item => {
                item.style.display = '';
            });
        }
    } else {
        // Turn on filter - deactivate other filters first
        button.parentElement.querySelectorAll('.filter-btn-small').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        // Apply filter
        if (panel) {
            panel.querySelectorAll('.pub-item').forEach(item => {
                const studyType = item.dataset.studyType;
                if (filterType === 'gwas') {
                    item.style.display = studyType === 'gwas' ? '' : 'none';
                } else if (filterType === 'functional') {
                    item.style.display = studyType === 'functional' ? '' : 'none';
                }
            });
        }
    }
}

function formatGapLevel(level) {
    switch (level) {
        case 'complete_gap': return '🔴 No publications';
        case 'severe_gap': return '🟠 1-3 publications';
        case 'moderate_gap': return '🟡 4-10 publications';
        case 'studied': return '🟢 Well studied';
        default: return level;
    }
}

function renderGenes(genes) {
    const tbody = document.getElementById('genes-tbody');

    if (genes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--text-muted);">
                    No genes extracted
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = genes.slice(0, 50).map(gene => `
        <tr>
            <td class="gene-name">${gene.name}</td>
            <td>${gene.symbol || '-'}</td>
            <td>${gene.mentions}</td>
        </tr>
    `).join('');
}

function renderSummaries(summaries) {
    const list = document.getElementById('summaries-list');
    const entries = Object.entries(summaries);

    if (entries.length === 0) {
        list.innerHTML = `
            <div class="empty-state" style="padding: 2rem;">
                <div class="empty-icon">📚</div>
                <h3>No Summaries Available</h3>
                <p>Gene function summaries will appear here after analysis.</p>
            </div>
        `;
        return;
    }

    list.innerHTML = entries.map(([gene, summary]) => `
        <div class="summary-card">
            <div class="summary-gene">
                <span>🧬</span>
                <h4>${gene}</h4>
            </div>
            <p class="summary-text">${summary}</p>
        </div>
    `).join('');
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// ============================================================================
// Event Handlers
// ============================================================================

async function handleSearch() {
    const query = document.getElementById('search-input').value.trim();

    if (!query) {
        alert('Please enter a search query');
        return;
    }

    const sourceSpecies = document.getElementById('source-species').value;
    const targetCheckboxes = document.querySelectorAll('#target-species input:checked');
    const targetSpecies = Array.from(targetCheckboxes).map(cb => cb.value);
    const maxArticles = parseInt(document.getElementById('max-articles').value) || 20;
    const model = document.getElementById('model-select').value;

    if (targetSpecies.length === 0) {
        alert('Please select at least one target species');
        return;
    }

    // Disable search button
    const searchBtn = document.getElementById('search-btn');
    searchBtn.disabled = true;

    try {
        showLoading('Searching PubMed for articles...');

        // Update loading text as analysis progresses
        setTimeout(() => {
            document.getElementById('loading-text').textContent = 'Extracting genes using LLM...';
        }, 3000);

        setTimeout(() => {
            document.getElementById('loading-text').textContent = 'Checking publication counts per species...';
        }, 8000);

        setTimeout(() => {
            document.getElementById('loading-text').textContent = 'Identifying publication gaps...';
        }, 15000);

        setTimeout(() => {
            document.getElementById('loading-text').textContent = 'Generating gene function summaries...';
        }, 25000);

        const results = await analyzeGaps(query, sourceSpecies, targetSpecies, maxArticles, model);
        showResults(results);

        // Save to search history
        const gapsCount = results.gaps?.reduce((sum, g) => sum + g.gap_count, 0) || 0;
        addToSearchHistory(query, sourceSpecies, targetSpecies, gapsCount);

    } catch (error) {
        hideLoading();
        alert(`Analysis failed: ${error.message}`);
        document.getElementById('empty-state').style.display = 'flex';
    } finally {
        searchBtn.disabled = false;
    }
}

function handleModelChange(event) {
    const model = event.target.value;
    if (model) {
        setModel(model);
    }
}

function handleHintClick(event) {
    const query = event.target.dataset.query;
    if (query) {
        document.getElementById('search-input').value = query;
    }
}

function handleSelectAll() {
    document.querySelectorAll('#target-species input').forEach(cb => cb.checked = true);
}

function handleDeselectAll() {
    document.querySelectorAll('#target-species input').forEach(cb => cb.checked = false);
}

// ============================================================================
// Initialization
// ============================================================================

async function init() {
    console.log('🧬 GAP Filler initializing...');

    // Initialize theme
    initTheme();

    // Initialize search history
    renderSearchHistory();

    // Bind event listeners
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    document.getElementById('model-select').addEventListener('change', handleModelChange);

    document.querySelectorAll('.hint-tag').forEach(tag => {
        tag.addEventListener('click', handleHintClick);
    });

    document.getElementById('select-all-btn').addEventListener('click', handleSelectAll);
    document.getElementById('deselect-all-btn').addEventListener('click', handleDeselectAll);

    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Load initial data
    await Promise.all([
        checkStatus(),
        loadSpecies(),
        loadModels()
    ]);

    // Periodic status check
    setInterval(checkStatus, 30000);

    // v3.0 - Initialize tool buttons
    initToolButtons();

    console.log('🌱 GAP Filler ready!');
}

// ============================================================================
// v3.0 - Analysis Tools Functions
// ============================================================================

function toggleToolSection(sectionId) {
    const section = document.getElementById(sectionId);
    const content = section.querySelector('.tool-content');
    const toggle = section.querySelector('.tool-toggle');

    const isHidden = content.style.display === 'none';
    content.style.display = isHidden ? 'block' : 'none';
    section.classList.toggle('expanded', isHidden);
}

function selectGeneForTools(geneName, sourceSpecies, targetSpecies) {
    state.selectedGene = geneName;
    state.selectedSourceSpecies = sourceSpecies;
    state.selectedTargetSpecies = targetSpecies;

    // Remove selected state from all target buttons
    document.querySelectorAll('.select-tool-btn').forEach(btn => {
        btn.classList.remove('selected');
    });

    // Find and highlight the clicked button (find by gene name match)
    document.querySelectorAll('.gene-gap-item').forEach(item => {
        const geneNameTag = item.querySelector('.gene-name-tag');
        if (geneNameTag && geneNameTag.textContent.trim() === geneName) {
            const btn = item.querySelector('.select-tool-btn');
            if (btn) btn.classList.add('selected');
        }
    });

    // Update displays
    const fundingDisplay = document.getElementById('funding-gene-display');
    const proposalDisplay = document.getElementById('proposal-gene-display');

    const geneHtml = `<span class="gene-tag">${geneName}</span> → ${targetSpecies}`;

    if (fundingDisplay) fundingDisplay.innerHTML = geneHtml;
    if (proposalDisplay) proposalDisplay.innerHTML = geneHtml;

    // Update NIH RePORTER link text and add click handler to copy gene to clipboard
    const nihLink = document.getElementById('nih-reporter-link');
    if (nihLink) {
        nihLink.innerHTML = `🔗 Search "${geneName}" on NIH RePORTER`;
        nihLink.onclick = function (e) {
            // Copy gene name to clipboard before opening the link
            navigator.clipboard.writeText(geneName).then(() => {
                console.log(`Copied "${geneName}" to clipboard`);
            }).catch(err => {
                console.warn('Could not copy gene name:', err);
            });
            // Link still opens normally (don't prevent default)
        };
    }

    // Enable proposal button only (funding is now a direct link)
    const proposalBtn = document.getElementById('generate-proposal-btn');
    if (proposalBtn) proposalBtn.disabled = false;
}

function initToolButtons() {
    // Proposal button only - funding is now a direct link
    const proposalBtn = document.getElementById('generate-proposal-btn');
    if (proposalBtn) {
        proposalBtn.addEventListener('click', generateProposal);
    }
}

async function searchFunding() {
    if (!state.selectedGene) return;

    const resultsDiv = document.getElementById('funding-results');
    const btn = document.getElementById('search-funding-btn');

    btn.disabled = true;
    btn.textContent = '⏳ Searching...';
    resultsDiv.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem;">Searching NIH grants...</p>';

    try {
        const response = await fetch(`${API_BASE}/funding`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gene: state.selectedGene })
        });

        if (!response.ok) throw new Error('Funding search failed');

        const data = await response.json();
        resultsDiv.innerHTML = renderFundingResults(data);

    } catch (error) {
        resultsDiv.innerHTML = `<p style="color: var(--accent-danger); font-size: 0.8rem;">❌ ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Search Funding';
    }
}

function renderFundingResults(data) {
    // Handle error case
    if (!data.success && data.error) {
        return `
            <div style="padding: 8px; background: var(--bg-primary); border-radius: 4px;">
                <p style="color: var(--accent-danger); font-size: 0.8rem;">⚠️ ${data.error}</p>
                <a href="https://reporter.nih.gov/" target="_blank" 
                   style="font-size: 0.75rem; color: var(--accent-cyan); text-decoration: underline;">
                    🔗 Search manually on NIH RePORTER
                </a>
            </div>
        `;
    }

    if (!data.grants || data.grants.length === 0) {
        return `
            <div style="padding: 8px; background: var(--bg-primary); border-radius: 4px;">
                <p style="color: var(--text-muted); font-size: 0.8rem;">No active grants found for "${data.gene || state.selectedGene}".</p>
                <a href="https://reporter.nih.gov/" target="_blank" 
                   style="font-size: 0.75rem; color: var(--accent-cyan); text-decoration: underline;">
                    🔗 Try searching on NIH RePORTER directly
                </a>
            </div>
        `;
    }

    return `
        <div class="funding-list">
            <p style="font-size: 0.75rem; color: var(--accent-success);">Found ${data.grants.length} grants</p>
            ${data.grants.slice(0, 5).map(g => `
                <div class="funding-item" style="padding: 8px; background: var(--bg-primary); border-radius: 4px; margin-bottom: 8px;">
                    <div style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">${g.title}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">${g.pi} • ${g.org}</div>
                    ${g.amount ? `<div style="font-size: 0.7rem; color: var(--accent-success);">$${g.amount.toLocaleString()}</div>` : ''}
                    ${g.link ? `<a href="${g.link}" target="_blank" style="font-size: 0.7rem; color: var(--accent-cyan); text-decoration: underline;">🔗 View on NIH Reporter</a>` : ''}
                </div>
            `).join('')}
            <a href="https://reporter.nih.gov/?searchId=&searchType=advanced" target="_blank" 
               style="display: block; margin-top: 8px; font-size: 0.7rem; color: var(--accent-cyan); text-decoration: underline;">
                🔍 Advanced search on NIH RePORTER
            </a>
        </div>
    `;
}

async function generateProposal() {
    if (!state.selectedGene) return;

    const resultsDiv = document.getElementById('proposal-results');
    const btn = document.getElementById('generate-proposal-btn');
    const lengthInput = document.querySelector('input[name="proposal-length"]:checked');
    const length = lengthInput ? lengthInput.value : 'medium';

    btn.disabled = true;
    btn.textContent = '⏳ Generating...';
    resultsDiv.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem;">AI is writing your proposal... This may take a minute.</p>';

    try {
        const response = await fetch(`${API_BASE}/proposal/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                gene: state.selectedGene,
                source_species: state.selectedSourceSpecies,
                target_species: state.selectedTargetSpecies,
                length: length
            })
        });

        // Parse response body regardless of status - backend returns error info in JSON
        const data = await response.json();

        // Use renderProposalResult which now handles error cases properly
        resultsDiv.innerHTML = renderProposalResult(data);

    } catch (error) {
        // Network error or JSON parse error
        resultsDiv.innerHTML = `
            <div style="padding: 8px; background: var(--bg-primary); border-radius: 4px;">
                <p style="color: var(--accent-danger); font-size: 0.8rem;">❌ Network error</p>
                <p style="color: var(--text-muted); font-size: 0.75rem; margin-top: 4px;">${error.message}</p>
                <p style="color: var(--text-muted); font-size: 0.7rem; margin-top: 8px;">
                    💡 Check that the backend server is running on port 5000.
                </p>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = '✨ Generate Proposal';
    }
}

function renderProposalResult(data) {
    // Handle explicit failure from backend
    if (!data.success || !data.proposal) {
        const errorMsg = data.error || 'Unknown error occurred';
        return `
            <div style="padding: 8px; background: var(--bg-primary); border-radius: 4px;">
                <p style="color: var(--accent-danger); font-size: 0.8rem;">❌ Failed to generate proposal</p>
                <p style="color: var(--text-muted); font-size: 0.75rem; margin-top: 4px;">${errorMsg}</p>
                <p style="color: var(--text-muted); font-size: 0.7rem; margin-top: 8px;">
                    💡 Make sure Ollama is running and the LLM model is available.
                </p>
            </div>
        `;
    }

    return `
        <div class="proposal-result" style="background: var(--bg-primary); border-radius: 4px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; color: var(--accent-success);">✓ Generated</span>
                <button onclick="copyProposal()" class="btn-small" style="font-size: 0.7rem;">📋 Copy</button>
            </div>
            <div id="proposal-text" style="font-size: 0.8rem; line-height: 1.5; color: var(--text-secondary); white-space: pre-wrap; max-height: 250px; overflow-y: auto;">
${data.proposal}
            </div>
        </div>
    `;
}

function copyProposal() {
    const proposalText = document.getElementById('proposal-text');
    if (proposalText) {
        navigator.clipboard.writeText(proposalText.textContent);
        alert('Proposal copied to clipboard!');
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', init);
