/**
 * EcoLens Frontend Application Logic
 *
 * Handles tab switching, text analysis, image upload with drag-and-drop,
 * Chart.js donut rendering, and dynamic result display with accessibility.
 */

// ====== DOM REFERENCES ======
const tabText = document.getElementById('tab-text');
const tabImage = document.getElementById('tab-image');
const panelText = document.getElementById('panel-text');
const panelImage = document.getElementById('panel-image');
const textInput = document.getElementById('text-input');
const charCount = document.getElementById('text-char-count');
const btnAnalyzeText = document.getElementById('btn-analyze-text');
const btnAnalyzeImage = document.getElementById('btn-analyze-image');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const previewImage = document.getElementById('preview-image');
const fileName = document.getElementById('file-name');
const btnRemoveFile = document.getElementById('btn-remove-file');
const loadingOverlay = document.getElementById('loading-overlay');
const resultsSection = document.getElementById('results-section');
const inputSection = document.getElementById('input-section');
const errorCard = document.getElementById('error-card');
const errorText = document.getElementById('error-text');
const btnDismissError = document.getElementById('btn-dismiss-error');
const btnNewAnalysis = document.getElementById('btn-new-analysis');

// Result elements
const resultCategory = document.getElementById('result-category');
const resultCarbonKg = document.getElementById('result-carbon-kg');
const resultRationale = document.getElementById('result-rationale');
const resultAccessibility = document.getElementById('result-accessibility');
const swapsGrid = document.getElementById('swaps-grid');

// Chart instance reference
let carbonChart = null;
let selectedFile = null;

// ====== TAB SWITCHING ======
function switchTab(tabName) {
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
    });
    panels.forEach(p => p.classList.remove('active'));

    if (tabName === 'text') {
        tabText.classList.add('active');
        tabText.setAttribute('aria-selected', 'true');
        panelText.classList.add('active');
    } else {
        tabImage.classList.add('active');
        tabImage.setAttribute('aria-selected', 'true');
        panelImage.classList.add('active');
    }
}

tabText.addEventListener('click', () => switchTab('text'));
tabImage.addEventListener('click', () => switchTab('image'));

// ====== CHARACTER COUNT ======
textInput.addEventListener('input', () => {
    charCount.textContent = `${textInput.value.length} / 2000`;
});

// ====== FILE UPLOAD (DRAG & DROP) ======
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

function handleFile(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showError('Invalid file type. Please upload a JPG, PNG, or WebP image.');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showError('File too large. Maximum size is 10MB.');
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewImage.alt = `Preview of uploaded file: ${file.name}`;
        dropZone.style.display = 'none';
        filePreview.style.display = 'flex';
        btnAnalyzeImage.disabled = false;
    };
    reader.readAsDataURL(file);
}

btnRemoveFile.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    dropZone.style.display = 'block';
    filePreview.style.display = 'none';
    btnAnalyzeImage.disabled = true;
});

// ====== API CALLS ======
async function analyzeText() {
    const description = textInput.value.trim();
    if (description.length < 3) {
        showError('Please enter at least 3 characters describing your activity.');
        return;
    }

    showLoading();
    try {
        const formData = new FormData();
        formData.append('description', description);

        const response = await fetch('/api/analyze/text', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.success && data.result) {
            renderResults(data.result);
        } else {
            throw new Error(data.error || 'Analysis failed. Please try again.');
        }
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

async function analyzeImage() {
    if (!selectedFile) {
        showError('Please upload an image first.');
        return;
    }

    showLoading();
    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch('/api/analyze/image', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.success && data.result) {
            renderResults(data.result);
        } else {
            throw new Error(data.error || 'Image analysis failed. Please try again.');
        }
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

btnAnalyzeText.addEventListener('click', analyzeText);
btnAnalyzeImage.addEventListener('click', analyzeImage);

// Allow Enter key submission for text input
textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        analyzeText();
    }
});

// ====== RENDER RESULTS ======
function renderResults(result) {
    // Hide input, show results
    inputSection.style.display = 'none';
    errorCard.style.display = 'none';
    resultsSection.style.display = 'flex';

    // Category badge
    resultCategory.textContent = result.category;

    // Animated carbon value
    animateValue(resultCarbonKg, 0, result.estimated_carbon_kg, 1200);

    // Rationale
    resultRationale.textContent = result.calculation_rationale;

    // Accessibility summary
    resultAccessibility.textContent = result.accessibility_summary;

    // Render swap cards
    renderSwaps(result.personalized_swaps);

    // Render Chart.js donut
    renderChart(result);

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function animateValue(element, start, end, duration) {
    const startTime = performance.now();
    const decimals = end < 10 ? 2 : 1;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;
        element.textContent = current.toFixed(decimals);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

function renderSwaps(swaps) {
    swapsGrid.innerHTML = '';
    swaps.forEach((swap, index) => {
        const card = document.createElement('div');
        card.className = 'swap-card';
        card.innerHTML = `
            <div class="swap-number">${index + 1}</div>
            <div class="swap-content">
                <div class="swap-action">${escapeHtml(swap.action)}</div>
                <div class="swap-rationale">${escapeHtml(swap.rationale)}</div>
            </div>
            <div class="swap-impact">-${swap.impact_reduction_percent.toFixed(0)}%</div>
        `;
        swapsGrid.appendChild(card);
    });
}

function renderChart(result) {
    const ctx = document.getElementById('carbon-chart').getContext('2d');

    // Destroy previous chart if it exists
    if (carbonChart) {
        carbonChart.destroy();
    }

    const currentKg = result.estimated_carbon_kg;
    const swaps = result.personalized_swaps;

    // Build chart data: current vs potential savings
    const labels = ['Your Footprint', ...swaps.map(s => s.action)];
    const savings = swaps.map(s => currentKg * (s.impact_reduction_percent / 100));
    const remaining = Math.max(0, currentKg - savings.reduce((a, b) => a + b, 0));

    const data = [remaining, ...savings];
    const colors = [
        'rgba(239, 68, 68, 0.8)',   // Red for current footprint
        'rgba(16, 185, 129, 0.8)',  // Emerald
        'rgba(163, 230, 53, 0.8)', // Lime
        'rgba(56, 189, 248, 0.8)', // Sky blue
    ];
    const borderColors = [
        'rgba(239, 68, 68, 1)',
        'rgba(16, 185, 129, 1)',
        'rgba(163, 230, 53, 1)',
        'rgba(56, 189, 248, 1)',
    ];

    carbonChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: borderColors.slice(0, data.length),
                borderWidth: 2,
                hoverBorderWidth: 3,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 16,
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12,
                            weight: '500',
                        },
                        usePointStyle: true,
                        pointStyleWidth: 12,
                    },
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { family: "'Inter', sans-serif", weight: '600' },
                    bodyFont: { family: "'Inter', sans-serif" },
                    callbacks: {
                        label: function (context) {
                            return ` ${context.label}: ${context.parsed.toFixed(2)} kg CO₂e`;
                        },
                    },
                },
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000,
                easing: 'easeOutQuart',
            },
        },
    });
}

// ====== UI STATE HELPERS ======
function showLoading() {
    loadingOverlay.style.display = 'block';
    errorCard.style.display = 'none';
    btnAnalyzeText.disabled = true;
    btnAnalyzeImage.disabled = true;
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
    btnAnalyzeText.disabled = false;
    if (selectedFile) btnAnalyzeImage.disabled = false;
}

function showError(message) {
    hideLoading();
    errorText.textContent = message;
    errorCard.style.display = 'flex';
    errorCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

btnDismissError.addEventListener('click', () => {
    errorCard.style.display = 'none';
});

// New Analysis button
btnNewAnalysis.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    inputSection.style.display = 'block';
    textInput.value = '';
    charCount.textContent = '0 / 2000';

    // Reset file upload
    selectedFile = null;
    fileInput.value = '';
    dropZone.style.display = 'block';
    filePreview.style.display = 'none';
    btnAnalyzeImage.disabled = true;

    // Destroy chart
    if (carbonChart) {
        carbonChart.destroy();
        carbonChart = null;
    }

    inputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

// ====== SECURITY: HTML ESCAPE ======
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
