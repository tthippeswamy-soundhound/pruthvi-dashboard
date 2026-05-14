// === State ===
let selectedFiles = [];
let results = [];
let llmEnabled = false;

// === DOM References ===
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const fileCount = document.getElementById('fileCount');
const uploadActions = document.getElementById('uploadActions');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressCount = document.getElementById('progressCount');
const progressFile = document.getElementById('progressFile');
const progressPercent = document.getElementById('progressPercent');
const resultsSection = document.getElementById('resultsSection');
const resultsBody = document.getElementById('resultsBody');
const resultCount = document.getElementById('resultCount');
const analyzeBtn = document.getElementById('analyzeBtn');
const analysisHeader = document.getElementById('analysisHeader');

// === File Upload Handling ===
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

function handleFiles(fileListInput) {
    const newFiles = Array.from(fileListInput);
    for (const file of newFiles) {
        if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            selectedFiles.push(file);
        }
    }
    renderFileList();
}

function renderFileList() {
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        fileCount.style.display = 'none';
        uploadActions.style.display = 'none';
        return;
    }

    fileCount.textContent = `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`;
    fileCount.style.display = 'inline';
    uploadActions.style.display = 'block';

    fileList.innerHTML = selectedFiles.map((file, idx) => `
        <div class="file-item">
            <div class="file-icon">&#9835;</div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-size">${formatSize(file.size)}</div>
            </div>
            <button class="file-remove" onclick="removeFile(${idx})" title="Remove file">&times;</button>
        </div>
    `).join('');
}

function removeFile(idx) {
    selectedFiles.splice(idx, 1);
    renderFileList();
}

function clearFiles() {
    selectedFiles = [];
    fileInput.value = '';
    renderFileList();
}

// === Transcription ===
async function transcribeFiles() {
    if (selectedFiles.length === 0) {
        showToast('Please select audio files first.', 'error');
        return;
    }

    const transcribeBtn = document.getElementById('transcribeBtn');
    transcribeBtn.disabled = true;
    progressSection.classList.add('visible');
    resultsSection.classList.remove('visible');
    results = [];

    const total = selectedFiles.length;
    let completed = 0;

    progressBar.style.width = '0%';
    progressCount.textContent = `0/${total}`;
    progressFile.textContent = 'Starting transcription...';
    progressPercent.textContent = '0%';

    // Send all files at once
    const diarize = document.getElementById('enableDiarize').checked;
    const formData = new FormData();
    for (const file of selectedFiles) {
        formData.append('files', file);
    }
    formData.append('diarize', diarize);

    progressFile.textContent = `Processing ${total} file${total !== 1 ? 's' : ''}...`;
    progressBar.style.width = '30%';
    progressPercent.textContent = '30%';

    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(err.detail || 'Transcription failed');
        }

        const data = await response.json();
        results = data.results.map(r => ({
            filename: r.filename,
            transcript: r.transcript || '',
            analysis: '',
            error: r.error || '',
        }));

        progressBar.style.width = '100%';
        progressPercent.textContent = '100%';
        progressCount.textContent = `${total}/${total}`;
        progressFile.textContent = 'Transcription complete!';

        setTimeout(() => {
            progressSection.classList.remove('visible');
            renderResults();
            resultsSection.classList.add('visible');
            showToast(`Successfully transcribed ${results.filter(r => !r.error).length} file(s).`, 'success');
        }, 800);

    } catch (err) {
        showToast(`Transcription error: ${err.message}`, 'error');
        progressSection.classList.remove('visible');
    } finally {
        transcribeBtn.disabled = false;
    }
}

// === Results Rendering ===
function renderResults() {
    resultCount.textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;

    resultsBody.innerHTML = results.map((r, idx) => `
        <tr>
            <td class="col-num">${idx + 1}</td>
            <td class="col-file">${escapeHtml(r.filename)}</td>
            <td class="col-transcript">
                <div class="transcript-cell">${r.error
                    ? `<span class="error-text">Error: ${escapeHtml(r.error)}</span>`
                    : formatTranscript(r.transcript) || '<span class="analysis-pending">No speech detected</span>'
                }</div>
            </td>
            ${llmEnabled ? `
            <td class="col-analysis">
                <div class="analysis-cell">${r.analysis
                    ? escapeHtml(r.analysis)
                    : '<span class="analysis-pending">Not analyzed yet</span>'
                }</div>
            </td>` : ''}
        </tr>
    `).join('');
}

// === LLM Analysis ===
function toggleLLMOption() {
    llmEnabled = document.getElementById('enableLLM').checked;
    analyzeBtn.style.display = llmEnabled ? 'inline-flex' : 'none';
    analysisHeader.style.display = llmEnabled ? '' : 'none';
    renderResults();
}

async function analyzeTranscripts() {
    const apiKey = document.getElementById('apiKey').value.trim();
    if (!apiKey) {
        showToast('Please enter your OpenAI API key in Settings.', 'error');
        document.getElementById('settingsPanel').classList.add('visible');
        return;
    }

    const validResults = results.filter(r => r.transcript && !r.error);
    if (validResults.length === 0) {
        showToast('No valid transcripts to analyze.', 'error');
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing...';

    const customPrompt = document.getElementById('customPrompt').value.trim();
    const model = document.getElementById('llmModel').value;

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transcripts: validResults.map(r => ({
                    filename: r.filename,
                    transcript: r.transcript,
                })),
                api_key: apiKey,
                prompt: customPrompt || null,
                model: model,
            }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Analysis failed' }));
            throw new Error(err.detail || 'Analysis failed');
        }

        const data = await response.json();

        // Merge analysis back into results
        for (const analyzed of data.results) {
            const match = results.find(r => r.filename === analyzed.filename);
            if (match) {
                match.analysis = analyzed.analysis;
            }
        }

        renderResults();
        showToast('LLM analysis complete!', 'success');

    } catch (err) {
        showToast(`Analysis error: ${err.message}`, 'error');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '&#129302; Run LLM Analysis';
    }
}

// === Excel Export ===
async function exportToExcel() {
    if (results.length === 0) {
        showToast('No results to export.', 'error');
        return;
    }

    const exportBtn = document.getElementById('exportBtn');
    exportBtn.disabled = true;
    exportBtn.innerHTML = '<span class="spinner spinner-sm"></span> Exporting...';

    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                results: results.map(r => ({
                    filename: r.filename,
                    transcript: r.transcript,
                    analysis: r.analysis || '',
                })),
            }),
        });

        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'transcription_results.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('Excel file downloaded!', 'success');

    } catch (err) {
        showToast(`Export error: ${err.message}`, 'error');
    } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = '&#128202; Export to Excel';
    }
}

// === Settings Toggle ===
function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    panel.classList.toggle('visible');
}

// === Toast Notifications ===
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// === Utilities ===
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTranscript(text) {
    if (!text) return '';
    // If transcript has speaker labels (Agent:/User:), format them with styling
    const lines = text.split('\n');
    const hasSpeakerLabels = lines.some(l => /^(Agent|User):/.test(l.trim()));

    if (!hasSpeakerLabels) {
        return escapeHtml(text);
    }

    return lines.map(line => {
        const match = line.match(/^(Agent|User):\s*(.*)/);
        if (match) {
            const speaker = match[1];
            const content = match[2];
            const cls = speaker === 'Agent' ? 'speaker-agent' : 'speaker-user';
            return `<div class="speaker-line"><span class="speaker-label ${cls}">${escapeHtml(speaker)}:</span> ${escapeHtml(content)}</div>`;
        }
        return `<div>${escapeHtml(line)}</div>`;
    }).join('');
}
