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
    initializeFileUploads();
    initializeDragAndDrop();
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


/**
 * Initialise les listeners pour les uploads de fichiers
 */
function initializeFileUploads() {
    document.getElementById('fileJ').addEventListener('change', function() {
        if (this.files[0]) {
            uploadFile(this.files[0], 'j');
        }
    });
    
    document.getElementById('fileJ1').addEventListener('change', function() {
        if (this.files[0]) {
            uploadFile(this.files[0], 'jMinus1');
        }
    });
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
        
        // Envoi à l'API
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
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
        console.error(`❌ Erreur upload ${type}:`, error);
        
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
        
        filesReady[type === 'j' ? 'j' : 'j1'] = false;
        checkAnalyzeButtonState();
    }
}

/**
 * Vérifie l'état du bouton d'analyse
 */
function checkAnalyzeButtonState() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (filesReady.j && filesReady.j1) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.add('pulse');
        
        // Notification visuelle
        showNotification('Both files are loaded! You can start the analysis.', 'success');
    } else {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.remove('pulse');
    }
}

/**
 * Lance l'analyse des fichiers
 */
async function analyze() {
    console.log('🔍 Lancement de l\'analyse TCD');
    
    // Affichage du statut d'analyse
    document.getElementById('results').innerHTML = `
        <div class="analysis-section fade-in-up">
            <div class="card border-0">
                <div class="card-body text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
                    <h4 class="text-primary">Generating analyses...</h4>
                    <p class="text-muted">
                        Balance Sheet + Consumption + Ressources <br>
                        <small>ACTIF/PASSIF • LCR par métier • Top Conso = "O"</small>
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
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000);

        const response = await fetch('/api/analyze', { 
            method: 'POST',
            signal: controller.signal 
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const result = await response.json();
            console.log('📊 Résultats de l\'analyse:', result);
            
            if (result.success) {
                // Attendre que l'affichage soit complètement terminé
                await displayCompleteResults(result.results);
                
                // AFFICHER L'INDICATEUR DE CHARGEMENT CONTEXTE
                document.getElementById('context-loading').style.display = 'block';
                
                // Vérifier que le contexte est prêt côté serveur
                if (result.context_ready) {
                    showNotification('Analyses successfully completed!', 'success');
                    
                    // Double vérification avec un petit délai pour l'effet visuel
                    setTimeout(async () => {
                        const contextStatus = await verifyContextReady();
                        
                        // MASQUER L'INDICATEUR DE CHARGEMENT
                        document.getElementById('context-loading').style.display = 'none';
                        
                        if (contextStatus) {
                            console.log('✅ Contexte vérifié, affichage du chatbot');
                            showNotification('AI Assistant ready!', 'success');
                            showChatbot();
                        } else {
                            console.warn('⚠️ Contexte pas encore prêt');
                            showNotification('AI Assistant loading...', 'info');
                            setTimeout(() => {
                                document.getElementById('context-loading').style.display = 'none';
                                showChatbot();
                            }, 1000);
                        }
                    }, 1000); // Délai pour montrer le chargement
                } else {
                    // Fallback
                    showNotification('Analysis completed, preparing chatbot...', 'info');
                    setTimeout(() => {
                        document.getElementById('context-loading').style.display = 'none';
                        showChatbot();
                    }, 3000);
                }
            } else {
                throw new Error(result.message || 'Erreur dans l\'analyse');
            }

        } else {
            const errorText = await response.text();
            throw new Error(`Erreur serveur ${response.status}: ${errorText}`);
        }
    } catch (error) {
        console.error('❌ Erreur analyse:', error);
        
        // MASQUER L'INDICATEUR EN CAS D'ERREUR
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
        
        showNotification('Erreur lors de l\'analyse', 'error');
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

        // AJOUTER LE BOUTON D'EXPORT ICI
        html += `
            <div class="text-center my-4">
                <button class="btn btn-analyze btn-lg" onclick="exportToPDF()">
                    <i class="fas fa-file-pdf me-2"></i>DOWNLOAD PDF REPORT
                </button>
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
        const response = await fetch('/api/chat-history');
        const result = await response.json();
        
        const docsContainer = document.getElementById('uploaded-docs');
        if (result.success && result.documents_count > 0) {
            docsContainer.innerHTML = `
                <h6 class="mb-2">Documents (${result.documents_count})</h6>
                <div class="doc-item">
                    <i class="fas fa-file-alt me-2"></i>
                    ${result.documents_count} document(s) in context
                </div>
            `;
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
        // Changer le bouton en mode loading
        exportButton.disabled = true;
        exportButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>GENERATING PDF...';
        
        showNotification('Generating PDF report...', 'info');
        
        const response = await fetch('/api/export-pdf', { method: 'POST' });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `LCR_Analysis_${new Date().toISOString().slice(0,10)}.pdf`;
            a.click();
            
            showNotification('PDF downloaded successfully!', 'success');
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Error exporting PDF', 'error');
    } finally {
        // Restaurer le bouton
        exportButton.disabled = false;
        exportButton.innerHTML = originalContent;
    }
}