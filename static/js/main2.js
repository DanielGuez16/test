/**
 * static/js/main.js
 * 
 * Steering ALM Metrics - Interface JavaScript
 * ==========================================
 * 
 * Gestion des uploads, analyses et affichage des résultats TCD
 */

// Variables globales
let filesReady = { j: false, j1: false };

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Interface ALM initialisée');
    initializeDateSelection(); 
});

function initializeDragAndDrop() {
    const uploadAreas = document.querySelectorAll('.upload-area');
    
    uploadAreas.forEach(area => {
        area.addEventListener('dragover', handleDragOver);
        area.addEventListener('dragenter', handleDragEnter);
        area.addEventListener('dragleave', handleDragLeave);
        area.addEventListener('drop', handleDrop);
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragEnter(e) {
    e.preventDefault();
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const isFileJ = e.currentTarget.closest('.card').querySelector('h5').textContent.includes('D (');
        const fileType = isFileJ ? 'j' : 'jMinus1';
        uploadFile(files[0], fileType);
    }
}


function initializeDateSelection() {
    const dateInput = document.getElementById('analysis-date');
    const today = new Date();
    
    // Définir la date max à aujourd'hui
    dateInput.max = today.toISOString().split('T')[0];
    
    // Définir une date par défaut (hier)
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    dateInput.value = yesterday.toISOString().split('T')[0];
    
    // Listener pour le changement de date
    dateInput.addEventListener('change', function() {
        if (this.value) {
            checkAnalyzeButtonState();
            showSelectedDateInfo(this.value);
        }
    });
    
    // Afficher les infos pour la date par défaut
    showSelectedDateInfo(dateInput.value);
}

function showSelectedDateInfo(selectedDate) {
    const statusDiv = document.getElementById('date-status');
    const dateObj = new Date(selectedDate);
    const nextDay = new Date(dateObj);
    nextDay.setDate(nextDay.getDate() + 1);
    
    const formatDate = (date) => date.toLocaleDateString('fr-FR');
    
    statusDiv.innerHTML = `
        <div class="alert alert-info fade-in-up">
            <div class="text-start">
                <strong>Files to be retrieved:</strong><br>
                <small>
                    • File J-1: D_PA_${selectedDate.replace(/-/g, '')}xxxx.csv (data for ${formatDate(new Date(dateObj.getTime() - 24*60*60*1000))})<br>
                    • File J: D_PA_${nextDay.toISOString().split('T')[0].replace(/-/g, '')}xxxx.csv (data for ${formatDate(dateObj)})
                </small>
            </div>
        </div>
    `;
}


async function logout() {
    if (confirm('Are you sure you want to logout?')) {
        const response = await fetch('/api/logout', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            window.location.href = result.redirect;
        }
    }
}

/**
 * Initialise le bouton d'analyse
 */
function initializeAnalyzeButton() {
    document.getElementById('analyzeBtn').addEventListener('click', analyze);
}

/**
 * Upload d'un fichier vers l'API
 * @param {File} file - Fichier à uploader
 * @param {string} type - Type de fichier ('j' ou 'jMinus1')
 */
async function uploadFile(file, type) {
    const statusDiv = document.getElementById('status' + (type === 'j' ? 'J' : 'J1'));
    
    try {
        console.log(`📤 Upload ${type}:`, file.name);

        // Affichage du statut de progression
        statusDiv.innerHTML = `
            <div class="alert alert-info fade-in-up">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-3"></div>
                    <div>
                        <strong>Uploading...</strong><br>
                        <small>${file.name} (${formatFileSize(file.size)})</small>
                    </div>
                </div>
            </div>
        `;
                
        // Préparation de la requête
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', type);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.log('Upload timeout après 5 minutes');
            controller.abort();
        }, 1800000);

        // Envoi à l'API
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const result = await response.json();
            console.log(`✅ Upload ${type} réussi:`, result);
            
            // Mise à jour du statut
            statusDiv.innerHTML = `
                <div class="alert alert-success fade-in-up">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="d-flex align-items-center mb-1">
                                <i class="fas fa-check-circle text-success me-2"></i>
                                <strong>${file.name}</strong>
                            </div>
                            <small class="text-muted">
                                ${result.rows?.toLocaleString()} rows • 
                                ${result.columns} columns • 
                                ${formatFileSize(file.size)}
                            </small>
                        </div>
                        <span class="badge bg-success">OK</span>
                    </div>
                </div>
            `;
            
            // Marquer le fichier comme prêt
            filesReady[type === 'j' ? 'j' : 'j1'] = true;
            
            // Vérifier si on peut activer l'analyse
            checkAnalyzeButtonState();
            
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Erreur inconnue' }));
            throw new Error(errorData.message || `Erreur HTTP ${response.status}`);
        }
        
    } catch (error) {
    clearTimeout(timeoutId); // Ajouter cette ligne
    console.error(`❌ Erreur upload ${type}:`, error);
    
    // Gestion spécifique pour les timeouts/abort
    if (error.name === 'AbortError') {
        statusDiv.innerHTML = `
            <div class="alert alert-warning fade-in-up">
                <div class="d-flex align-items-center">
                    <i class="fas fa-clock me-2"></i>
                    <div>
                        <strong>Upload timeout</strong><br>
                        <small>Le fichier est trop volumineux ou la connexion trop lente</small>
                    </div>
                </div>
            </div>
        `;
    } else {
        statusDiv.innerHTML = `
            <div class="alert alert-danger fade-in-up">
                <div class="d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <div>
                        <strong>Erreur d'upload</strong><br>
                        <small>${error.message}</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    filesReady[type === 'j' ? 'j' : 'j1'] = false;
    checkAnalyzeButtonState();
}
}

/**
 * Vérifie l'état du bouton d'analyse
 */
function checkAnalyzeButtonState() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const dateInput = document.getElementById('analysis-date');
    
    if (dateInput.value) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.add('pulse');
        
        showNotification('Date selected! You can start the analysis.', 'success');
    } else {
        analyzeBtn.disabled = true;
        analyzeBtn.classList.remove('pulse');
    }
}

// NOUVELLE FONCTION
async function cleanupMemory() {
    try {
        showNotification('Cleaning memory...', 'info');
        const response = await fetch('/api/cleanup-memory', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showNotification(result.message, 'success');
        }
    } catch (error) {
        showNotification('Memory cleanup failed', 'error');
    }
}

/**
 * Lance l'analyse des fichiers
 */
async function analyze() {
    const selectedDate = document.getElementById('analysis-date').value;
    
    if (!selectedDate) {
        showNotification('Please select a date first', 'error');
        return;
    }
    
    console.log('🔍 Lancement de l\'analyse pour la date:', selectedDate);
    
    // Affichage du statut d'analyse
    document.getElementById('results').innerHTML = `
        <div class="analysis-section fade-in-up">
            <div class="card border-0">
                <div class="card-body text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
                    <h4 class="text-primary">Retrieving files from SharePoint...</h4>
                    <p class="text-muted">
                        Date: ${selectedDate}<br>
                        <small>Loading D_PA files and generating analysis</small>
                    </p>
                    <div class="progress mt-3" style="height: 6px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             style="width: 100%"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    try {
        const response = await fetch('/api/analyze-by-date', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date: selectedDate })
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('📊 Résultats de l\'analyse par date:', result);
            
            if (result.success) {
                await displayCompleteResults(result.results);
                
                document.getElementById('context-loading').style.display = 'block';
                
                if (result.context_ready) {
                    showNotification(`Analysis completed for ${selectedDate}!`, 'success');
                    
                    setTimeout(async () => {
                        document.getElementById('context-loading').style.display = 'none';
                        showNotification('AI Assistant ready!', 'success');
                        showChatbot();
                        
                        // Afficher les fichiers utilisés
                        if (result.files_used) {
                            showNotification(`Files used: ${result.files_used.jMinus1} & ${result.files_used.j}`, 'info');
                        }
                    }, 1000);
                }
            } else {
                throw new Error(result.message || 'Erreur dans l\'analyse');
            }
        } else {
            const errorText = await response.text();
            throw new Error(`Erreur serveur ${response.status}: ${errorText}`);
        }
    } catch (error) {
        console.error('❌ Erreur analyse par date:', error);
        
        document.getElementById('context-loading').style.display = 'none';
        
        document.getElementById('results').innerHTML = `
            <div class="analysis-section fade-in-up">
                <div class="alert alert-danger">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
                        <div>
                            <h5 class="mb-1">Erreur lors de l'analyse</h5>
                            <p class="mb-0">${error.message}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        showNotification('Erreur lors de l\'analyse SharePoint', 'error');
    }
}

/**
 * Vérifie que le contexte du chatbot est vraiment prêt côté serveur
 */
async function verifyContextReady() {
    try {
        console.log('🔍 Vérification du statut du contexte...');
        const response = await fetch('/api/context-status');
        
        if (response.ok) {
            const result = await response.json();
            console.log('📋 Statut contexte:', result);
            return result.context_ready;
        } else {
            console.error('❌ Erreur vérification contexte:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Erreur checking context status:', error);
        return false;
    }
}

/**
 * Affiche les résultats complets incluant Balance Sheet et Consumption
 * @param {Object} analysisResults - Résultats complets de l'analyse
 */
function displayCompleteResults(analysisResults) {
    return new Promise((resolve) => {
        if (!analysisResults) {
            document.getElementById('results').innerHTML = '<div class="alert alert-danger">Aucun résultat d\'analyse disponible</div>';
            resolve();
            return;
        }
        
        let html = '';
        
        // Section Balance Sheet
        if (analysisResults.balance_sheet) {
            html += generateBalanceSheetSection(analysisResults.balance_sheet);
        }
        
        // Section Consumption
        if (analysisResults.consumption) {
            html += generateConsumptionSection(analysisResults.consumption);
        }

    html += `
    <div class="text-center my-4">
        <button class="btn btn-analyze btn-lg" onclick="exportToPDF()">
            <i class="fas fa-file-pdf me-2"></i>DOWNLOAD PDF REPORT
        </button>
        <div class="mt-2">
            <small class="text-muted">
                <i class="fas fa-lightbulb me-1"></i>
                Report includes analysis results and the latest AI response
            </small>
        </div>
    </div>
    `;
        
        document.getElementById('results').innerHTML = html;
        
        // Attendre que le DOM soit mis à jour
        setTimeout(() => {
            const firstSection = document.querySelector('.analysis-section');
            
            // INITIALISER LES GRAPHIQUES ICI
            if (window.pendingCharts) {
                initializeMetierCharts(window.pendingCharts.significantGroups, window.pendingCharts.metierDetails);
                delete window.pendingCharts;
            }
            
            setTimeout(() => {
                resolve();
            }, 1000);
            
        }, 500);
    });
}

/**
 * Variables globales pour le chatbot
 */
let chatMessages = [];

/**
 * Affiche la section chatbot après les analyses
 */
function showChatbot() {
    document.getElementById('chatbot-section').style.display = 'block';

    // Initialiser le drag & drop pour les documents
    initializeDocumentDragAndDrop();
    
    // Message initial du bot
    if (chatMessages.length === 0) {
        addChatMessage('assistant', 'Hello! I can help you analyze the LCR data that was just processed. You can ask me questions about the Balance Sheet variations, Consumption trends, or upload additional documents for context.');
    }
}

/**
 * Toggle l'affichage du chatbot
 */
function toggleChatbot() {
    const chatSection = document.getElementById('chatbot-section');
    chatSection.style.display = chatSection.style.display === 'none' ? 'block' : 'none';
}

/**
 * Envoie un message au chatbot
 */
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Ajouter le message utilisateur
    addChatMessage('user', message);
    input.value = '';
    
    // Afficher l'indicateur de frappe
    addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        if (response.ok) {
            const result = await response.json();
            removeTypingIndicator();
            addChatMessage('assistant', result.response);
        } else {
            removeTypingIndicator();
            addChatMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator();
        addChatMessage('assistant', 'Connection error. Please check your network.');
    }
}

/**
 * Ajoute un message au chat avec rendu Markdown
 */
function addChatMessage(type, message) {
    const container = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    
    if (type === 'user') {
        messageDiv.innerHTML = `<strong>You:</strong> ${message}`;
    } else {
        // Parser le markdown pour l'IA
        const formattedMessage = parseMarkdownToHtml(message);
        messageDiv.innerHTML = `<strong>AI:</strong> <div class="ai-response">${formattedMessage}</div>`;
    }
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    // Sauvegarder en mémoire
    chatMessages.push({ type, message, timestamp: new Date() });
}

function initializeDocumentDragAndDrop() {
    const docUploadArea = document.getElementById('doc-upload-area');
    
    if (docUploadArea) {
        docUploadArea.addEventListener('dragover', handleDocDragOver);
        docUploadArea.addEventListener('dragenter', handleDocDragEnter);
        docUploadArea.addEventListener('dragleave', handleDocDragLeave);
        docUploadArea.addEventListener('drop', handleDocDrop);
    }
}

function handleDocDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDocDragEnter(e) {
    e.preventDefault();
}

function handleDocDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function handleDocDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadDocument(files[0]);
    }
}

/**
 * Convertit le markdown simple en HTML propre
 */
function parseMarkdownToHtml(text) {
    try {
        // Configuration de Marked pour être plus permissif
        marked.setOptions({
            breaks: true,        // Conversion des \n en <br>
            gfm: true,          // GitHub Flavored Markdown
            tables: true,       // Support des tableaux
            sanitize: false,    // On utilisera DOMPurify après
            smartypants: true,  // Typographie intelligente
            highlight: function(code, lang) {
                // Coloration syntaxique basique
                return `<code class="language-${lang || 'text'}">${code}</code>`;
            }
        });
        
        // Parser le markdown
        let html = marked.parse(text);
        
        // Nettoyer et sécuriser le HTML avec DOMPurify
        html = DOMPurify.sanitize(html, {
            ALLOWED_TAGS: [
                'p', 'br', 'strong', 'em', 'u', 'del', 's', 'strike',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'dl', 'dt', 'dd',
                'blockquote', 'pre', 'code',
                'table', 'thead', 'tbody', 'tr', 'th', 'td',
                'a', 'img', 'hr', 'div', 'span',
                'sup', 'sub', 'mark', 'small'
            ],
            ALLOWED_ATTR: [
                'href', 'title', 'alt', 'src', 'class', 'id',
                'target', 'rel', 'colspan', 'rowspan'
            ]
        });
        
        // Ajouter les classes Bootstrap/CSS personnalisées
        html = html
            .replace(/<h1/g, '<h1 class="mt-4 mb-3 text-primary"')
            .replace(/<h2/g, '<h2 class="mt-4 mb-3 text-primary"')
            .replace(/<h3/g, '<h3 class="mt-3 mb-2 text-primary"')
            .replace(/<h4/g, '<h4 class="mt-3 mb-2 text-secondary"')
            .replace(/<h5/g, '<h5 class="mt-2 mb-1 text-secondary"')
            .replace(/<h6/g, '<h6 class="mt-2 mb-1"')
            .replace(/<table/g, '<table class="table table-bordered table-sm my-3"')
            .replace(/<blockquote/g, '<blockquote class="border-start border-primary ps-3 ms-3 fst-italic"')
            .replace(/<pre/g, '<pre class="bg-light p-3 rounded"')
            .replace(/<code(?![^>]*class)/g, '<code class="bg-light px-1 rounded"')
            .replace(/<ul/g, '<ul class="mb-2"')
            .replace(/<ol/g, '<ol class="mb-2"')
            .replace(/<hr/g, '<hr class="my-3"')
            .replace(/<img/g, '<img class="img-fluid rounded my-2"')
            .replace(/<a(?![^>]*target)/g, '<a class="text-primary" target="_blank" rel="noopener noreferrer"');
        
        return html;
        
    } catch (error) {
        console.error('Erreur parsing Markdown:', error);
        // Fallback en cas d'erreur
        return `<p class="text-danger">Erreur de formatage du message</p><pre>${text}</pre>`;
    }
}

/**
 * Gère la touche Entrée dans l'input de chat
 */
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

/**
 * Affiche l'indicateur de frappe
 */
function addTypingIndicator() {
    const container = document.getElementById('chat-container');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.className = 'chat-message assistant';
    typingDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm me-2" style="width: 1rem; height: 1rem;"></div>
            <em>AI is thinking...</em>
        </div>
    `;
    
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

/**
 * Supprime l'indicateur de frappe
 */
function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Upload d'un document pour le contexte
 */
async function uploadDocument(file) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showNotification(`Uploading ${file.name}...`, 'info');
        
        const response = await fetch('/api/upload-document', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            updateUploadedDocsList();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Document upload error:', error);
        showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
    }
}

/**
 * Met à jour la liste des documents uploadés
 */
async function updateUploadedDocsList() {
    try {
        const response = await fetch('/api/uploaded-documents');
        const result = await response.json();
        
        const docsContainer = document.getElementById('uploaded-docs');
        if (result.success && result.count > 0) {
            let docsHtml = `<h6 class="mb-2">Documents (${result.count})</h6>`;
            
            result.documents.forEach(doc => {
                docsHtml += `
                    <div class="doc-item">
                        <i class="fas fa-file-alt me-2"></i>
                        <strong>${doc.filename}</strong>
                        <br><small class="text-muted">${formatFileSize(doc.size)} - ${new Date(doc.upload_time).toLocaleTimeString()}</small>
                    </div>
                `;
            });
            
            docsContainer.innerHTML = docsHtml;
        } else {
            docsContainer.innerHTML = '';
        }
        
    } catch (error) {
        console.error('Error updating docs list:', error);
    }
}

/**
 * Vide l'historique du chat
 */
async function clearChat() {
    if (!confirm('Clear all chat history and documents?')) return;
    
    try {
        const response = await fetch('/api/chat-clear', { method: 'DELETE' });
        
        if (response.ok) {
            document.getElementById('chat-container').innerHTML = '';
            document.getElementById('uploaded-docs').innerHTML = '';
            chatMessages = [];
            showNotification('Chat history cleared', 'success');
        }
        
    } catch (error) {
        console.error('Error clearing chat:', error);
        showNotification('Error clearing chat', 'error');
    }
}

/**
 * Génère la section Balance Sheet
 */
function generateBalanceSheetSection(balanceSheetData) {
    if (balanceSheetData.error) {
        return `
            <div class="analysis-section">
                <div class="alert alert-danger">
                    <h5>Erreur Balance Sheet</h5>
                    <p>${balanceSheetData.error}</p>
                </div>
            </div>
        `;
    }
    
    let html = `
        <div class="analysis-section fade-in-up">
            <div class="card border-0">
                <div class="card-header no-background">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 style="color: #76279b;" class="mb-1"> ${balanceSheetData.title || '1. Balance Sheet'}</h2>
                        </div>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-container">
                        ${balanceSheetData.pivot_table_html || '<p class="p-3">Données non disponibles</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;

        
    // Résumé Balance Sheet
    if (balanceSheetData.summary) {
        html += `
            <div class="analysis-section fade-in-up">
                <div class="summary-box">
                    <div class="d-flex align-items-start">
                        <div>
                            <p class="mb-0">${balanceSheetData.summary}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    
    // Variations Balance Sheet
    if (balanceSheetData.variations) {
        html += `
            <div class="analysis-section fade-in-up">
                <div class="row justify-content-center">
        `;

        const variations = balanceSheetData.variations;

        // Carte ACTIF
        if (variations.ACTIF) {
            const actif = variations.ACTIF;
            const isPositive = actif.variation >= 0;
            
            html += `
                <div class="col-md-5 mb-3">
                    <div class="metric-card p-3">
                        <div class="text-center">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="mb-0">ASSET</h6>
                                <span class="badge ${isPositive ? 'bg-success' : 'bg-danger'}">
                                    ${isPositive ? '📈 Increase' : '📉 Decrease'}
                                </span>
                            </div>
                            <div class="row text-center">
                                <div class="col-6">
                                    <small class="opacity-75">D-1</small>
                                    <h4>${actif.j_minus_1} Bn €</h4>
                                </div>
                                <div class="col-6">
                                    <small class="opacity-75">D</small>
                                    <h4>${actif.j} Bn €</h4>
                                </div>
                            </div>
                            <hr class="my-3 opacity-50">
                            <h3 class="${isPositive ? 'text-success' : 'text-danger'}">
                                ${isPositive ? '+' : ''}${actif.variation} Bn €
                            </h3>
                            <small class="opacity-75">Variation</small>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Carte PASSIF
        if (variations.PASSIF) {
            const passif = variations.PASSIF;
            const isPositive = passif.variation >= 0;
            
            html += `
                <div class="col-md-5 mb-3">
                    <div class="metric-card p-3">
                        <div class="text-center">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="mb-0">LIABILITY</h6>
                                <span class="badge ${isPositive ? 'bg-success' : 'bg-danger'}">
                                    ${isPositive ? '📈 Increase' : '📉 Decrease'}
                                </span>
                            </div>
                            <div class="row text-center">
                                <div class="col-6">
                                    <small class="opacity-75">D-1</small>
                                    <h4>${passif.j_minus_1} Bn €</h4>
                                </div>
                                <div class="col-6">
                                    <small class="opacity-75">D</small>
                                    <h4>${passif.j} Bn €</h4>
                                </div>
                            </div>
                            <hr class="my-3 opacity-50">
                            <h3 class="${isPositive ? 'text-success' : 'text-danger'}">
                                ${isPositive ? '+' : ''}${passif.variation} Bn €
                            </h3>
                            <small class="opacity-75">Variation</small>
                        </div>
                    </div>
                </div>
            `;
        }

        html += `
                </div>
            </div>
        `;

        // Trait de séparation à la fin 
        html += `
            <div class="analysis-section">
                <hr class="balance-sheet-separator">
            </div>
        `;
    }
    
    return html;
}

/**
 * Génère la section Consumption avec graphiques par métier
 */
function generateConsumptionSection(consumptionData) {
    if (consumptionData.error) {
        return `
            <div class="analysis-section">
                <div class="alert alert-danger">
                    <h5>Erreur Consumption</h5>
                    <p>${consumptionData.error}</p>
                </div>
            </div>
        `;
    }
    
    let html = `
        <div class="analysis-section fade-in-up mt-5">
            <div class="card border-0">
                <div class="card-header no-background">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 style="color: #76279b;" class="mb-1"> ${consumptionData.title || '2. LCR Consumption'}</h2>
                        </div>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-container">
                        ${consumptionData.consumption_table_html || '<p class="p-3">Données non disponibles</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Analyse textuelle Consumption
    if (consumptionData.analysis_text) {
        html += `
            <div class="analysis-section fade-in-up">
                <div class="summary-box">
                    <div class="d-flex align-items-start">
                        <div>
                            <p class="mb-0">${consumptionData.analysis_text}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Métriques Consumption globales
    if (consumptionData.variations && consumptionData.variations.global) {
        const globalVar = consumptionData.variations.global;
        const isPositive = globalVar.variation >= 0;
        
        html += `
            <div class="analysis-section fade-in-up">
                <div class="row justify-content-center">
                    <div class="col-md-8">
                        <div class="metric-card p-2">
                            <div class="text-center">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h6 class="mb-0">CONSUMPTION</h6>
                                    <span class="badge ${isPositive ? 'bg-success' : 'bg-danger'}">
                                        ${isPositive ? '📈 Increase' : '📉 Decrease'}
                                    </span>
                                </div>
                                <div class="row text-center">
                                    <div class="col-4">
                                        <small class="opacity-75">D-1</small>
                                        <h4>${globalVar.j_minus_1} Bn</h4>
                                    </div>
                                    <div class="col-4">
                                        <small class="opacity-75">D</small>
                                        <h4>${globalVar.j} Bn</h4>
                                    </div>
                                    <div class="col-4">
                                        <small class="opacity-75">Variation</small>
                                        <h4 class="${isPositive ? 'text-success' : 'text-danger'}">
                                            ${isPositive ? '+' : ''}${globalVar.variation} Bn
                                        </h4>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Graphiques par métier pour les groupes significatifs
    if (consumptionData.significant_groups && consumptionData.significant_groups.length > 0 && consumptionData.metier_details) {
        html += generateMetierChartsSection(consumptionData.significant_groups, consumptionData.metier_details);
    }
    
    // Analyse textuelle par métier
    if (consumptionData.metier_detailed_analysis) {
        html += `
            <div class="analysis-section fade-in-up">
                <div class="summary-box">
                    <div class="d-flex align-items-start">
                        <div>
                            <p class="mb-0">${consumptionData.metier_detailed_analysis}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    ;

    // Trait de séparation à la fin 
    html += `
        <div class="analysis-section">
            <hr class="balance-sheet-separator">
        </div>
    `;
    
    return html;
}

/**
 * Génère la section des graphiques par métier
 */
function generateMetierChartsSection(significantGroups, metierDetails) {
    console.log('📊 Génération des graphiques métiers pour:', significantGroups);
    console.log('📊 Données métiers:', metierDetails);
    
    let html = `
        <div class="analysis-section fade-in-up">
            <div class="card border-0">
                <div class="card-header no-background">
                    <h4 class="mb-0">Details by group (LCR Consumption)</h4>
                </div>
                <div class="card-body">
                    <div class="row">
    `;
    
    // Générer un graphique pour chaque groupe significatif
    significantGroups.forEach((groupe, index) => {
        const chartId = `metierChart_${index}`;
        html += `
            <div class="col-lg-6 mb-4">
                <div class="chart-container">
                    <h5 class="text-center mb-3">${groupe}</h5>
                    <canvas id="${chartId}" width="400" height="300"></canvas>
                </div>
            </div>
        `;
    });
    
    html += `
                    </div>
                </div>
            </div>
        </div>
    `;
    
    window.pendingCharts = { significantGroups, metierDetails };

    return html;
}

/**
 * Initialise les graphiques métiers avec Chart.js
 */
function initializeMetierCharts(significantGroups, metierDetails) {
    console.log('🎨 Initialisation des graphiques métiers');
    
    // Vérifier que Chart.js est disponible
    if (typeof Chart === 'undefined') {
        console.error('❌ Chart.js non disponible');
        return;
    }
    
    significantGroups.forEach((groupe, index) => {
        const chartId = `metierChart_${index}`;
        const canvas = document.getElementById(chartId);
        
        if (!canvas) {
            console.error(`❌ Canvas ${chartId} non trouvé`);
            return;
        }
        
        // Préparer les données pour ce groupe
        const chartData = prepareMetierChartData(groupe, metierDetails);
        
        if (!chartData) {
            console.error(`❌ Pas de données pour ${groupe}`);
            return;
        }
        
        // Créer le graphique
        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `LCR variations detailed for - ${groupe}`,
                        font: { size: 14, weight: 'bold' }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'LCR Impact (Bn €)'
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: ''
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0
                        }
                    }
                },
                elements: {
                    bar: {
                        borderWidth: 1
                    }
                }
            }
        });
        
        console.log(`✅ Graphique créé pour ${groupe}`);
    });
}

/**
 * Prépare les données pour un graphique métier
 */
function prepareMetierChartData(groupe, metierDetails) {
    try {
        // Récupérer les données J et J-1 pour ce groupe
        const dataJ = metierDetails.j ? metierDetails.j.filter(item => item.LCR_ECO_GROUPE_METIERS === groupe) : [];
        const dataJ1 = metierDetails.jMinus1 ? metierDetails.jMinus1.filter(item => item.LCR_ECO_GROUPE_METIERS === groupe) : [];
        
        if (dataJ.length === 0 && dataJ1.length === 0) {
            return null;
        }
        
        // Créer un mapping par métier
        const metiersMap = new Map();
        
        // Ajouter les données J-1
        dataJ1.forEach(item => {
            metiersMap.set(item.Métier, {
                metier: item.Métier,
                j_minus_1: item.LCR_ECO_IMPACT_LCR_Bn,
                j: 0
            });
        });
        
        // Ajouter/mettre à jour avec les données J
        dataJ.forEach(item => {
            if (metiersMap.has(item.Métier)) {
                metiersMap.get(item.Métier).j = item.LCR_ECO_IMPACT_LCR_Bn;
            } else {
                metiersMap.set(item.Métier, {
                    metier: item.Métier,
                    j_minus_1: 0,
                    j: item.LCR_ECO_IMPACT_LCR_Bn
                });
            }
        });
        
        // Calculer les variations et trier par ordre décroissant
        const metierVariations = Array.from(metiersMap.entries()).map(([metier, data]) => ({
            metier: metier,
            variation: data.j - data.j_minus_1,
            j: data.j,
            j_minus_1: data.j_minus_1
        }));
        
        // TRIER PAR VARIATION DÉCROISSANTE (positives d'abord, puis négatives)
        metierVariations.sort((a, b) => b.variation - a.variation);
        
        // Calculer la variation totale du groupe
        const totalVariation = metierVariations.reduce((sum, item) => sum + item.variation, 0);
        
        // NOUVEAU: Positionner intelligemment la barre TOTAL
        let labels = [];
        let variations = [];
        
        if (totalVariation >= 0) {
            // Si le total est positif, le mettre tout à gauche
            labels.push('TOTAL GROUP');
            variations.push(totalVariation);
            
            // Ajouter les métiers ensuite
            metierVariations.forEach(item => {
                labels.push(item.metier);
                variations.push(item.variation);
            });
        } else {
            // Si le total est négatif, mettre d'abord les métiers
            metierVariations.forEach(item => {
                labels.push(item.metier);
                variations.push(item.variation);
            });
            
            // Puis mettre le total à droite
            labels.push('TOTAL GROUP');
            variations.push(totalVariation);
        }
        
        return {
            labels: labels,
            datasets: [
                {
                    label: 'Variation (D - D-1)',
                    data: variations,
                    backgroundColor: variations.map((v, index) => {
                        // Identifier si c'est la barre TOTAL
                        const isTotalBar = labels[index] === 'TOTAL GROUP';
                        
                        if (isTotalBar) {
                            return v >= 0 ? '#6B218D' : '#6B218D'; // Couleur spéciale pour le total
                        }
                        // Couleurs normales pour les métiers
                        return v >= 0 ? '#51A0A2' : '#805bed';
                    }),
                    borderColor: variations.map((v, index) => {
                        const isTotalBar = labels[index] === 'TOTAL GROUP';
                        
                        if (isTotalBar) {
                            return v >= 0 ? '#6B218D' : '#6B218D';
                        }
                        return v >= 0 ? '#51A0A2' : '#805bed';
                    }),
                    borderWidth: variations.map((v, index) => {
                        const isTotalBar = labels[index] === 'TOTAL GROUP';
                        // Bordure plus épaisse pour le total
                        return isTotalBar ? 3 : 2;
                    })
                }
            ]
        };
        
    } catch (error) {
        console.error(`⚠ Erreur préparation données pour ${groupe}:`, error);
        return null;
    }
}


/**
 * Affiche une notification toast
 * @param {string} message - Message à afficher
 * @param {string} type - Type de notification ('success', 'error', 'info')
 */
function showNotification(message, type = 'info') {
    // Création de l'élément notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-suppression après 5 secondes
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

async function loadLogsStats() {
    try {
        const response = await fetch('/api/logs-stats');
        const result = await response.json();
        
        if (result.success) {
            const stats = result.stats;
            const statsHtml = `
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-primary">${stats.total}</h5>
                                <p class="card-text">Total Logs</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-success">${stats.users}</h5>
                                <p class="card-text">Active Users</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-info">${stats.actions}</h5>
                                <p class="card-text">Action Types</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-success">Online</h5>
                                <p class="card-text">System Status</p>
                            </div>
                        </div>
                    </div>
                </div>
                <hr>
            `;
            
            document.getElementById('logs-container').innerHTML = statsHtml;
            // Charger les logs après les statistiques
            loadActivityLogs();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('logs-container').innerHTML = '<div class="alert alert-danger">Error loading statistics</div>';
    }
}
/**
 * Retourne l'icône appropriée pour le type de notification
 * @param {string} type - Type de notification
 * @returns {string} Nom de l'icône Font Awesome
 */
function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'info': 'info-circle',
        'warning': 'exclamation-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Formate la taille d'un fichier en unités lisibles
 * @param {number} bytes - Taille en bytes
 * @returns {string} Taille formatée
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Formate un nombre avec des séparateurs de milliers
 * @param {number} number - Nombre à formater
 * @returns {string} Nombre formaté
 */
function formatNumber(number) {
    return new Intl.NumberFormat('fr-FR').format(number);
}

/**
 * Débuggage - Affiche les informations de débogage dans la console
 */
function debugInfo() {
    console.log('🔍 Debug Info:', {
        filesReady,
        analyzeButtonState: document.getElementById('analyzeBtn').disabled,
        timestamp: new Date().toISOString()
    });
}


// Dans main.js, après l'affichage des résultats
function addExportButton() {
    const exportButton = `
        <div class="text-center my-4">
            <button class="btn btn-secondary" onclick="exportToPDF()">
                <i class="fas fa-download me-2"></i>Export to PDF
            </button>
        </div>
    `;
    document.getElementById('results').insertAdjacentHTML('beforeend', exportButton);
}


async function exportToPDF() {
    const exportButton = document.querySelector('button[onclick="exportToPDF()"]');
    const originalContent = exportButton.innerHTML;
    
    try {
        exportButton.disabled = true;
        exportButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>GENERATING REPORT...';
        
        showNotification('Generating report...', 'info');
        
        const response = await fetch('/api/export-pdf', { method: 'POST' });
        
        if (response.ok) {
            const result = await response.json();
            
            const link = document.createElement('a');
            link.href = result.report_url;
            link.target = '_blank';
            link.click();

            showNotification('Report opened! Use Ctrl+P to save as PDF', 'success');
            
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Error generating report', 'error');
    } finally {
        exportButton.disabled = false;
        exportButton.innerHTML = originalContent;
    }
}

function showAdminPanel() {
    const modal = new bootstrap.Modal(document.getElementById('admin-panel'));
    modal.show();
    
    // Charger les statistiques et les logs au premier affichage
    loadLogsStats(); // Cette fonction chargera aussi les logs
    
    // Ajouter un listener pour charger les users quand on clique sur l'onglet
    document.querySelector('a[href="#users-tab"]').addEventListener('click', function() {
        loadUsers();
    });
}

async function loadActivityLogs() {
    try {
        const response = await fetch('/api/logs?limit=50');
        const result = await response.json();
        
        if (result.success) {
            displayLogs(result.logs);
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        document.getElementById('logs-container').innerHTML = '<div class="alert alert-danger">Error loading logs</div>';
    }
}

function displayLogs(logs) {
    // Chercher le conteneur des logs ou créer une div après les stats
    let logsContainer = document.getElementById('logs-table-container');
    if (!logsContainer) {
        logsContainer = document.createElement('div');
        logsContainer.id = 'logs-table-container';
        document.getElementById('logs-container').appendChild(logsContainer);
    }
    
    if (logs.length === 0) {
        logsContainer.innerHTML = '<div class="alert alert-info">No activity logs found</div>';
        return;
    }
    
    let html = `
        <h5>Recent Activity Logs</h5>
        <div class="table-responsive">
            <table class="table table-striped table-sm">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    logs.reverse().forEach(log => {
        html += `
            <tr>
                <td><small>${new Date(log.timestamp).toLocaleString()}</small></td>
                <td><span class="badge bg-primary">${log.username.split('@')[0]}</span></td>
                <td><strong>${log.action}</strong></td>
                <td><small>${log.details}</small></td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    logsContainer.innerHTML = html;
}

async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        const result = await response.json();
        
        if (result.success) {
            displayUsers(result.users);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('users-container').innerHTML = '<div class="alert alert-danger">Error loading users</div>';
    }
}

function displayUsers(users) {
    const container = document.getElementById('users-container');
    
    if (users.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No users found</div>';
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Full Name</th>
                        <th>Role</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    users.forEach(user => {
        const roleClass = user.role === 'admin' ? 'bg-primary' : 'bg-secondary';
        html += `
            <tr>
                <td><code>${user.username}</code></td>
                <td><strong>${user.full_name}</strong></td>
                <td><span class="badge ${roleClass}">${user.role}</span></td>
                <td><small>${new Date(user.created_at).toLocaleDateString()}</small></td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}