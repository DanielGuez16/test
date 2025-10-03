/**
 * static/js/main.js
 * 
 * Steering ALM Metrics - Interface JavaScript
 * ==========================================
 * 
 * Gestion des uploads, analyses et affichage des résultats TCD
 */

// ================================= VARIABLES GLOBALES  =================================


let filesReady = { j: false, j1: false, m1: false };
let chatMessages = [];


// ================================= INITIALISATION  =================================


document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Interface ALM initialisée');
    initializeDateSelection();
    initializeDragAndDrop();
});

// ================================= UTILITAIRES =================================


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


// ================================= DRAG AND DROP HANDLERS =================================


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

function handleFileDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const card = e.currentTarget.closest('.card');
        const title = card.querySelector('h5').textContent;
        
        let fileType;
        if (title.includes('D (')) {
            fileType = 'j';
        } else if (title.includes('D-1')) {
            fileType = 'jMinus1';
        } else if (title.includes('M-1')) {
            fileType = 'mMinus1';
        }
        
        if (fileType) {
            uploadFile(files[0], fileType);
        }
    }
}

function handleDocDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadDocument(files[0]);
    }
}


function initializeDragAndDrop() {
    const uploadAreas = document.querySelectorAll('.upload-area');
    
    uploadAreas.forEach(area => {
        area.addEventListener('dragover', handleDragOver);
        area.addEventListener('dragenter', handleDragEnter);
        area.addEventListener('dragleave', handleDragLeave);
        area.addEventListener('drop', handleFileDrop);
    });
}

function initializeDocumentDragAndDrop() {
    const docUploadArea = document.getElementById('doc-upload-area');
    
    if (docUploadArea) {
        docUploadArea.addEventListener('dragover', handleDragOver);
        docUploadArea.addEventListener('dragenter', handleDragEnter);
        docUploadArea.addEventListener('dragleave', handleDragLeave);
        docUploadArea.addEventListener('drop', handleDocDrop);
    }
}


// ================================= GESTION FICHIERS =================================

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
    
    document.getElementById('fileM1').addEventListener('change', function() {
        if (this.files[0]) {
            uploadFile(this.files[0], 'mMinus1');
        }
    });
}

/**
 * Upload d'un fichier vers l'API
 * @param {File} file - Fichier à uploader
 * @param {string} type - Type de fichier ('j', 'jMinus1', 'mMinus1')
 */
async function uploadFile(file, type) {
    const statusMapping = {
        'j': 'statusJ',
        'jMinus1': 'statusJ1',
        'mMinus1': 'statusM1'
    };
    
    const readyMapping = {
        'j': 'j',
        'jMinus1': 'j1',
        'mMinus1': 'm1'
    };
    
    const statusDiv = document.getElementById(statusMapping[type]);
    
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
            filesReady[readyMapping[type]] = true;
            
            // Vérifier si on peut activer l'analyse
            checkAnalyzeButtonState();
            
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Erreur inconnue' }));
            throw new Error(errorData.message || `Erreur HTTP ${response.status}`);
        }
        
    } catch (error) {
        clearTimeout(timeoutId);
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
        
        filesReady[readyMapping[type]] = false;
        checkAnalyzeButtonState();
    }
}

function initializeDateSelection() {
    const loadButton = document.getElementById('loadFilesBtn');
    if (loadButton) {
        loadButton.addEventListener('click', loadFilesByDate);
        console.log('✅ Load Files button listener attached'); // Debug
    } else {
        console.error('❌ loadFilesBtn element not found!'); // Debug
    }
    
    // Définir la date par défaut
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate());
    const dateInput = document.getElementById('analysisDate');
    if (dateInput) {
        dateInput.value = yesterday.toISOString().split('T')[0];
        console.log('✅ Default date set:', dateInput.value); // Debug
    } else {
        console.error('❌ analysisDate input not found!'); // Debug
    }
}

async function loadFilesByDate() {
    console.log('🔄 loadFilesByDate() called');
    
    const dateInput = document.getElementById('analysisDate');
    const statusJ = document.getElementById('statusJ');
    const statusJ1 = document.getElementById('statusJ1');
    const statusM1 = document.getElementById('statusM1');
    
    // VÉRIFICATION CRITIQUE
    if (!statusJ || !statusJ1 || !statusM1) {
        console.error('❌ Éléments de statut manquants:', { statusJ, statusJ1, statusM1 });
        showNotification('Interface error: status elements missing', 'error');
        return;
    }
    
    const selectedDate = dateInput.value;
    
    if (!selectedDate) {
        showNotification('Please select a date', 'error');
        return;
    }
    
    try {
        // Affichage du loading
        statusJ.innerHTML = statusJ1.innerHTML = statusM1.innerHTML = `
            <div class="alert alert-info">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-3"></div>
                    <div>Loading from SharePoint...</div>
                </div>
            </div>
        `;
        
        const response = await fetch('/api/load-files-by-date', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: selectedDate })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Mise à jour statut J
            statusJ.innerHTML = `
                <div class="alert alert-success">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="d-flex align-items-center mb-1">
                                <i class="fas fa-check-circle text-success me-2"></i>
                                <strong>${result.files.j.filename}</strong>
                            </div>
                            <small class="text-muted">
                                ${result.files.j.rows.toLocaleString()} rows • 
                                ${result.files.j.columns} columns
                            </small>
                        </div>
                        <span class="badge bg-success">OK</span>
                    </div>
                </div>
            `;
            
            // Mise à jour statut J-1
            statusJ1.innerHTML = `
                <div class="alert alert-success">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="d-flex align-items-center mb-1">
                                <i class="fas fa-check-circle text-success me-2"></i>
                                <strong>${result.files.jMinus1.filename}</strong>
                            </div>
                            <small class="text-muted">
                                ${result.files.jMinus1.rows.toLocaleString()} rows • 
                                ${result.files.jMinus1.columns} columns
                            </small>
                        </div>
                        <span class="badge bg-success">OK</span>
                    </div>
                </div>
            `;
            
            // Mise à jour statut M-1
            statusM1.innerHTML = `
                <div class="alert alert-success">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="d-flex align-items-center mb-1">
                                <i class="fas fa-check-circle text-success me-2"></i>
                                <strong>${result.files.mMinus1.filename}</strong>
                            </div>
                            <small class="text-muted">
                                ${result.files.mMinus1.rows.toLocaleString()} rows • 
                                ${result.files.mMinus1.columns} columns
                            </small>
                        </div>
                        <span class="badge bg-success">OK</span>
                    </div>
                </div>
            `;
            
            // Marquer les TROIS fichiers comme prêts
            filesReady.j = true;
            filesReady.j1 = true;
            filesReady.m1 = true;
            checkAnalyzeButtonState();
            
            showNotification(`Three files loaded for ${selectedDate}`, 'success');
            
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Loading failed');
        }
        
    } catch (error) {
        console.error('Error loading files:', error);
        
        statusJ.innerHTML = statusJ1.innerHTML = statusM1.innerHTML = `
            <div class="alert alert-danger">
                <div class="d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <div>
                        <strong>Loading Error</strong><br>
                        <small>${error.message}</small>
                    </div>
                </div>
            </div>
        `;
        
        filesReady.j = false;
        filesReady.j1 = false;
        filesReady.m1 = false;
        checkAnalyzeButtonState();
        
        showNotification('Error loading files', 'error');
    }
}

/**
 * Vérifie l'état du bouton d'analyse
 */
function checkAnalyzeButtonState() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (filesReady.j && filesReady.j1 && filesReady.m1) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.add('pulse');
        
        if (!document.getElementById('cleanup-btn')) {
            const cleanupBtn = document.createElement('button');
            cleanupBtn.id = 'cleanup-btn';
            cleanupBtn.className = 'btn btn-outline-warning btn-sm ms-3';
            cleanupBtn.innerHTML = '<i class="fas fa-trash"></i> Clean Memory';
            cleanupBtn.onclick = cleanupMemory;
            analyzeBtn.parentNode.appendChild(cleanupBtn);
        }
        
        showNotification('All three files are loaded! You can start the analysis.', 'success');
    } else {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.remove('pulse');
        
        const cleanupBtn = document.getElementById('cleanup-btn');
        if (cleanupBtn) {
            cleanupBtn.remove();
        }
    }
}

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


// ================================= GESTION ANALYSE =================================

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

        if (analysisResults.simple_totals) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += generateSimpleTotalsSection(analysisResults.simple_totals);
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }

        // Section SI Remettant Bar juste après les totaux
        if (analysisResults.si_remettant) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += generateSiRemettantBar(analysisResults.si_remettant);
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }
        
        // Section avec BUFFER/Summary à gauche et Consumption & Resources à droite
        html += '<div class="analysis-section fade-in-up">';
        html += '<div class="row">';
        
        // Colonne gauche : BUFFER + Summary
        if (analysisResults.buffer) {
            html += '<div class="col-lg-6">';
            html += generateBufferSection(analysisResults.buffer);
            
            // Tableau de synthèse juste en dessous du BUFFER (sans titre)
            if (analysisResults.summary) {
                html += '<div class="mt-3">';
                html += generateSummarySection(analysisResults.summary);
                html += '</div>';
            }
            
            html += '</div>';
        }
        
        // Colonne droite : Consumption & Resources avec analyse IA
        html += '<div class="col-lg-6">';
        html += generateConsumptionResourcesBlockSection(analysisResults);
        html += '</div>';
        
        html += '</div>';
        html += '</div>';

        // Tableau CAPPAGE en pleine largeur
        if (analysisResults.cappage) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += '<div id="cappage-container">Chargement de l\'historique...</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }

        // Tableaux BUFFER & NCO empilés
        if (analysisResults.buffer_nco) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += '<div class="card border-0">';
            html += '<div class="card-header no-background">';
            html += '<h3 style="color: #76279b;">BUFFER & NCO - TCD Analysis</h3>';
            html += '</div>';
            html += '<div class="card-body p-0">';
            html += '<div id="buffer-nco-buffer-container">Chargement...</div>';
            html += '<div id="buffer-nco-nco-container">Chargement...</div>';
            html += '</div></div></div></div></div>';
        }

        // Tableaux CONSUMPTION & RESOURCES empilés
        if (analysisResults.consumption_resources) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += '<div class="card border-0">';
            html += '<div class="card-header no-background">';
            html += '<h3 style="color: #76279b;">CONSUMPTION & RESOURCES</h3>';
            html += '</div>';
            html += '<div class="card-body p-0">';
            html += '<div id="consumption-container">Chargement...</div>';
            html += '<div id="resources-container">Chargement...</div>';
            html += '</div></div></div></div></div>';
        }

        // Bouton export PDF
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

        // Attendre que le DOM soit à jour avant de charger l'historique
        setTimeout(() => {
            resolve();
        }, 100);

        // Charger l'historique après un délai plus long
        setTimeout(() => {
            loadHistoricalTables();
        }, 800);
    });
}

async function loadHistoricalTables() {
    try {
        // 1. CAPPAGE
        const cappageResp = await fetch('/api/analyze-historical/cappage?days_back=10');
        const cappageRes = await cappageResp.json();
        if (cappageRes.success) {
            document.getElementById('cappage-container').innerHTML = `
                <div class="card border-0">
                    <div class="card-header no-background">
                        <h3 style="color: #76279b;">CAPPAGE - Historique (${cappageRes.total_days} jours)</h3>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-container">
                            ${generateCappageTableHTML({historical: cappageRes})}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 2. BUFFER (Buffer & NCO)
        const bufferResp = await fetch('/api/analyze-historical/buffer_nco_buffer?days_back=10');
        const bufferRes = await bufferResp.json();
        if (bufferRes.success) {
            document.getElementById('buffer-nco-buffer-container').innerHTML = `
                <h5 class="text-primary mb-3 px-3 pt-3">1. BUFFER - Historique (${bufferRes.total_days} jours)</h5>
                <div class="table-container mb-4">
                    ${generateBufferNcoBufferTableHTML({historical: bufferRes})}
                </div>
            `;
        }
        
        // 3. NCO (Buffer & NCO)
        const ncoResp = await fetch('/api/analyze-historical/buffer_nco_nco?days_back=10');
        const ncoRes = await ncoResp.json();
        if (ncoRes.success) {
            document.getElementById('buffer-nco-nco-container').innerHTML = `
                <h5 class="text-primary mb-3 px-3">2. NCO - Historique (${ncoRes.total_days} jours)</h5>
                <div class="table-container">
                    ${generateBufferNcoNcoTableHTML({historical: ncoRes})}
                </div>
            `;
        }
        
        // 4. CONSUMPTION
        const consResp = await fetch('/api/analyze-historical/consumption_resources_consumption?days_back=10');
        const consRes = await consResp.json();
        if (consRes.success) {
            document.getElementById('consumption-container').innerHTML = `
                <h5 class="text-primary mb-3 px-3 pt-3">1. CONSUMPTION - Historique (${consRes.total_days} jours)</h5>
                <div class="table-container mb-4">
                    ${generateConsumptionResourcesConsumptionTableHTML({historical: consRes})}
                </div>
            `;
        }
        
        // 5. RESOURCES
        const resResp = await fetch('/api/analyze-historical/consumption_resources_resources?days_back=10');
        const resRes = await resResp.json();
        if (resRes.success) {
            document.getElementById('resources-container').innerHTML = `
                <h5 class="text-primary mb-3 px-3">2. RESOURCES - Historique (${resRes.total_days} jours)</h5>
                <div class="table-container">
                    ${generateConsumptionResourcesResourcesTableHTML({historical: resRes})}
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Erreur chargement historique:', error);
    }
}

// ================================= GÉNÉRATION TOTAUX LCR DU DÉBUT =================================


/**
 * Génère le tableau simple des totaux LCR
 */
function generateSimpleTotalsSection(totalsData) {
    if (totalsData.error) {
        return `<div class="alert alert-danger">Erreur totaux: ${totalsData.error}</div>`;
    }
    
    const data = totalsData.data;
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;">${totalsData.title}</h3>
                <small class="text-muted">
                    <i class="fas fa-info-circle me-1"></i>
                    ${totalsData.metadata.note}
                </small>
            </div>
            <div class="card-body p-0">
                <div class="table-container">
                    <table class="table table-bordered simple-totals-table mb-0">
                        <thead>
                            <tr>
                                <th class="text-center totals-header">File D (Today)</th>
                                <th class="text-center totals-header">File D-1 (Yesterday)</th>
                                <th class="text-center totals-header">File M-1 (Last Month)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="totals-row">
                                <td class="text-end totals-value">${(data.j || 0).toFixed(3)} Bn €</td>
                                <td class="text-end totals-value">${(data.jMinus1 || 0).toFixed(3)} Bn €</td>
                                <td class="text-end totals-value">${(data.mMinus1 || 0).toFixed(3)} Bn €</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère le visuel de la barre horizontale SI Remettant
 */
function generateSiRemettantBar(siData) {
    if (siData.error) {
        return `<div class="alert alert-danger">Erreur SI Remettant: ${siData.error}</div>`;
    }
    
    const data = siData.data.j || [];  // Données du fichier J (aujourd'hui)
    const colors = ['#6B218D', '#666666', '#805BED', '#51A0A2', '#987001', '#D46EA7'];
    
    // Calculer le total pour les pourcentages
    const total = data.reduce((sum, item) => sum + item.value, 0);
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <div class="d-flex justify-content-between align-items-center">
                    <h3 style="color: #76279b;">${siData.title}</h3>
                    <div class="si-filter-controls">
                        <small class="text-muted me-2">Filtres:</small>
    `;
    
    // Checkboxes pour filtrer
    siData.metadata.allowed_values.forEach((val, idx) => {
        html += `
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="si-${idx}" value="${val}" checked onchange="updateSiBar()">
                <label class="form-check-label" for="si-${idx}">
                    <span class="si-color-indicator" style="background-color: ${colors[idx % colors.length]}"></span>
                    ${val}
                </label>
            </div>
        `;
    });
    
    html += `
                    </div>
                </div>
            </div>
            <div class="card-body p-4">
                <div id="si-remettant-container" class="si-bar-container">
    `;
    
    // Générer la barre horizontale
    html += '<div class="si-horizontal-bar">';
    
    data.forEach((item, idx) => {
        const percentage = ((item.value / total) * 100).toFixed(2);
        const color = colors[idx % colors.length];
        
        html += `
            <div class="si-bar-segment" 
                 data-si="${item.si_remettant}"
                 style="width: ${percentage}%; background-color: ${color};"
                 title="${item.si_remettant}: ${item.value.toFixed(3)} Bn € (${percentage}%)">
                <span class="si-bar-label">${percentage}%</span>
            </div>
        `;
    });
    
    html += '</div>';  // Fin si-horizontal-bar
    
    // Légende
    html += '<div class="si-legend mt-4">';
    data.forEach((item, idx) => {
        const color = colors[idx % colors.length];
        html += `
            <div class="si-legend-item">
                <span class="si-legend-color" style="background-color: ${color}"></span>
                <span class="si-legend-label">${item.si_remettant}</span>
                <span class="si-legend-value">${item.value.toFixed(3)} Bn €</span>
            </div>
        `;
    });
    html += '</div>';
    
    html += `
                </div>
            </div>
        </div>
    `;
    
    // Stocker les données globalement pour les filtres
    html += `<script>window.siRemettantData = ${JSON.stringify(data)}; window.siColors = ${JSON.stringify(colors)};</script>`;
    
    return html;
}

/**
 * Met à jour la barre SI Remettant selon les filtres
 */
function updateSiBar() {
    const checkboxes = document.querySelectorAll('[id^="si-"]');
    const activeValues = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
    
    // Filtrer les données
    const filteredData = window.siRemettantData.filter(item => 
        activeValues.includes(item.si_remettant)
    );
    
    const total = filteredData.reduce((sum, item) => sum + item.value, 0);
    
    // Regénérer la barre
    let barHtml = '';
    filteredData.forEach((item, idx) => {
        const percentage = ((item.value / total) * 100).toFixed(2);
        const originalIdx = window.siRemettantData.indexOf(item);
        const color = window.siColors[originalIdx % window.siColors.length];
        
        barHtml += `
            <div class="si-bar-segment" 
                 data-si="${item.si_remettant}"
                 style="width: ${percentage}%; background-color: ${color};"
                 title="${item.si_remettant}: ${item.value.toFixed(3)} Bn € (${percentage}%)">
                <span class="si-bar-label">${percentage}%</span>
            </div>
        `;
    });
    
    document.querySelector('.si-horizontal-bar').innerHTML = barHtml;
}


// ================================= GÉNÉRATION BUFFER & CONSUMPTION & RESOURCES & CAPPAGE SECTION & BUFFER&NCO =================================


/**
 * Génère la section BUFFER avec style TCD Excel professionnel
 */
function generateBufferSection(bufferData) {
    if (bufferData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur BUFFER TCD</h5>
                <p>${bufferData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <div class="d-flex justify-content-between align-items-center">
                    <h3 style="color: #76279b;" class="mb-1">${bufferData.title}</h3>
                </div>
                <small class="text-muted">
                    <i class="fas fa-filter me-1"></i>LCR_Catégorie: "1- Buffer"
                </small>
            </div>
            <div class="card-body p-0">
                <div class="table-container">
                    ${generateBufferTableHTML(bufferData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère la section CONSUMPTION
 */
function generateConsumptionSection(consumptionData) {
    if (consumptionData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur CONSUMPTION</h5>
                <p>${consumptionData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${consumptionData.title}</h3>
            </div>
            <div class="card-body p-0">
                <div class="table-container">
                    ${generateConsumptionTableHTML(consumptionData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère la section du tableau de synthèse (sans titre)
 */
function generateSummarySection(summaryData) {
    if (summaryData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur Summary</h5>
                <p>${summaryData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-body p-0">
                <div class="table-container">
                    ${generateSummaryTableHTML(summaryData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}


/**
 * Génère le HTML du tableau BUFFER avec structure TCD Excel et variations
 */
function generateBufferTableHTML(bufferData) {
    if (!bufferData || !bufferData.pivot_data) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau BUFFER TCD</div>';
    }
    
    const pivotData = bufferData.pivot_data || [];
    
    if (pivotData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée BUFFER TCD disponible</div>';
    }
    
    // Calculer les grands totaux
    let grandTotal_J = 0;
    let grandTotal_DailyVar = 0;
    let grandTotal_MonthlyVar = 0;
    
    pivotData.forEach(sectionGroup => {
        grandTotal_J += sectionGroup.section_total_j || 0;
        grandTotal_DailyVar += sectionGroup.section_variation_daily || 0;
        grandTotal_MonthlyVar += sectionGroup.section_variation_monthly || 0;
    });
    
    let html = `
        <table class="table table-bordered buffer-tcd-table">
            <thead class="table-dark">
                <tr>
                    <th class="align-middle tcd-header-row" style="width: 40%">Section / Client</th>
                    <th class="text-center tcd-header-col">D (Bn €)</th>
                    <th class="text-center tcd-header-variation">Var. Daily (Bn €)</th>
                    <th class="text-center tcd-header-variation">Var. Monthly (Bn €)</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Génération des lignes TCD avec vraie hiérarchie Excel-like
    pivotData.forEach((sectionGroup, sectionIndex) => {
        const clientDetails = sectionGroup.client_details || [];
        
        // LIGNE DE SECTION - avec données directement (pas de ligne vide)
        html += `<tr class="tcd-section-row">`;
        html += `<td class="tcd-section-cell">
                    <div class="tcd-hierarchy-level-0">
                        <strong>${sectionGroup.section}</strong>
                    </div>
                 </td>`;
        
        // Données DIRECTES pour la section (comme Excel)
        html += `<td class="text-end tcd-data-cell"><strong>${(sectionGroup.section_total_j || 0).toFixed(3)}</strong></td>`;
        
        // Variation Daily Section
        const sectionVarDaily = sectionGroup.section_variation_daily || 0;
        const sectionDailyClass = sectionVarDaily >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
        const sectionDailyIcon = sectionVarDaily >= 0 ? '▲' : '▼';
        html += `<td class="text-end ${sectionDailyClass}">
                    ${sectionVarDaily >= 0 ? '+' : ''}${sectionVarDaily.toFixed(3)}
                    <span class="variation-icon">${sectionDailyIcon}</span>
                 </td>`;
        
        // Variation Monthly Section
        const sectionVarMonthly = sectionGroup.section_variation_monthly || 0;
        const sectionMonthlyClass = sectionVarMonthly >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
        const sectionMonthlyIcon = sectionVarMonthly >= 0 ? '▲' : '▼';
        html += `<td class="text-end ${sectionMonthlyClass}">
                    ${sectionVarMonthly >= 0 ? '+' : ''}${sectionVarMonthly.toFixed(3)}
                    <span class="variation-icon">${sectionMonthlyIcon}</span>
                 </td>`;
        
        html += `</tr>`;
        
        // LIGNES DE DÉTAIL : Clients indentés
        // N'afficher les détails QUE pour la section "1.1- Cash"
        if (sectionGroup.section === "1.1- Cash") {
            clientDetails.forEach((detail, detailIndex) => {
                html += `<tr class="tcd-detail-row">`;
                
                // Client indenté dans la même colonne
                html += `<td class="tcd-client-detail">
                            <div class="tcd-hierarchy-level-1">
                                ${detail.client}
                            </div>
                        </td>`;
                
                // Valeur D (Today)
                const valueJ = detail.value_j || 0;
                html += `<td class="text-end tcd-data-cell">${valueJ.toFixed(3)}</td>`;
                
                // Variation Daily
                const varDaily = detail.variation_daily || 0;
                const dailyClass = varDaily >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
                const dailyIcon = varDaily >= 0 ? '▲' : '▼';
                html += `<td class="text-end ${dailyClass}">
                            ${varDaily >= 0 ? '+' : ''}${varDaily.toFixed(3)}
                            <span class="variation-icon">${dailyIcon}</span>
                        </td>`;
                
                // Variation Monthly
                const varMonthly = detail.variation_monthly || 0;
                const monthlyClass = varMonthly >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
                const monthlyIcon = varMonthly >= 0 ? '▲' : '▼';
                html += `<td class="text-end ${monthlyClass}">
                            ${varMonthly >= 0 ? '+' : ''}${varMonthly.toFixed(3)}
                            <span class="variation-icon">${monthlyIcon}</span>
                        </td>`;
                
                html += '</tr>';
            });
        }
        // Pour toutes les autres sections, on ne montre PAS les détails clients
        // On passe directement à la ligne de séparation
        
        // Ligne de séparation entre les sections (sauf pour la dernière)
        if (sectionIndex < pivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="4"></td></tr>`;
        }
    });
    
    // Ligne de grand total général
    html += `
        <tr class="tcd-grand-total-row">
            <td class="tcd-grand-total-label">
                <strong>TOTAL</strong>
            </td>
            <td class="text-end tcd-grand-total-value">${grandTotal_J.toFixed(3)}</td>
    `;
    
    // Grand Total Variation Daily
    const grandDailyClass = grandTotal_DailyVar >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
    const grandDailyIcon = grandTotal_DailyVar >= 0 ? '▲' : '▼';
    html += `<td class="text-end tcd-grand-total-value ${grandDailyClass}">
                ${grandTotal_DailyVar >= 0 ? '+' : ''}${grandTotal_DailyVar.toFixed(3)}
                <span class="variation-icon">${grandDailyIcon}</span>
             </td>`;
    
    // Grand Total Variation Monthly
    const grandMonthlyClass = grandTotal_MonthlyVar >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
    const grandMonthlyIcon = grandTotal_MonthlyVar >= 0 ? '▲' : '▼';
    html += `<td class="text-end tcd-grand-total-value ${grandMonthlyClass}">
                ${grandTotal_MonthlyVar >= 0 ? '+' : ''}${grandTotal_MonthlyVar.toFixed(3)}
                <span class="variation-icon">${grandMonthlyIcon}</span>
             </td>`;
    
    html += '</tr>';
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau CONSUMPTION avec variations quotidiennes et mensuelles
 */
function generateConsumptionTableHTML(consumptionData) {
    if (!consumptionData.j || !consumptionData.jMinus1 || !consumptionData.mMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau CONSUMPTION (3 fichiers requis)</div>';
    }
    
    const dataJ = consumptionData.j;
    const dataJ1 = consumptionData.jMinus1;
    const dataM1 = consumptionData.mMinus1;
    
    // Créer mappings pour les variations
    const variationsMap = new Map();
    const monthlyVariationsMap = new Map();
    
    // Calculer les variations J vs J-1 et J vs M-1
    dataJ.forEach(itemJ => {
        // Variation quotidienne (J vs J-1)
        const itemJ1 = dataJ1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueJ1 = itemJ1 ? itemJ1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const dailyVariation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueJ1;
        
        // Variation mensuelle (J vs M-1)
        const itemM1 = dataM1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueM1 = itemM1 ? itemM1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const monthlyVariation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueM1;
        
        variationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            j1: valueJ1,
            variation: dailyVariation
        });
        
        monthlyVariationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            m1: valueM1,
            variation: monthlyVariation
        });
    });
    
    let html = `
        <table class="table table-bordered new-table consumption-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">LCR ECO Groupe Métiers</th>
                    <th colspan="3" class="text-center header-j">Analysis Results (Bn €)</th>
                </tr>
                <tr>
                    <th class="text-center header-j">D (Today)</th>
                    <th class="text-center header-variation">Daily Variation vs D-1</th>
                    <th class="text-center header-variation">Monthly Variation vs M-1</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Générer les lignes
    dataJ.forEach(item => {
        const dailyVar = variationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        const monthlyVar = monthlyVariationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        
        const absDailyVariation = Math.abs(dailyVar.variation);
        const isDailyPositive = dailyVar.variation >= 0;
        
        const absMonthlyVariation = Math.abs(monthlyVar.variation);
        const isMonthlyPositive = monthlyVar.variation >= 0;
        
        html += '<tr>';
        html += `<td class="fw-bold">${item.LCR_ECO_GROUPE_METIERS}</td>`;
        html += `<td class="text-end numeric-value">${item.LCR_ECO_IMPACT_LCR_Bn.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">
                    ${absDailyVariation.toFixed(3)}
                    <span class="variation-indicator ${isDailyPositive ? 'positive' : 'negative'}">
                        ${isDailyPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += `<td class="text-end numeric-value">
                    ${absMonthlyVariation.toFixed(3)}
                    <span class="variation-indicator ${isMonthlyPositive ? 'positive' : 'negative'}">
                        ${isMonthlyPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau de synthèse
 */
function generateSummaryTableHTML(summaryData) {
    if (!summaryData.j || !summaryData.jMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau de synthèse</div>';
    }
    
    const dataJ = summaryData.j;
    const dataJ1 = summaryData.jMinus1;
    
    let html = `
        <table class="table table-bordered new-table summary-table">
            <thead>
                <tr>
                    <th class="align-middle">Date d'arrêté</th>
                    <th class="text-center header-j">LCR Assiette Pondérée<br><small>(Bn €)</small></th>
                    <th class="text-center header-j">LCR ECO Impact<br><small>(Bn €)</small></th>
                    <th class="text-center header-variation">Différence<br><small>(Assiette - Impact)</small></th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Ligne pour fichier J-1 (hier)
    if (dataJ1.length > 0) {
        const itemJ1 = dataJ1[0]; // Prendre la première date du fichier J-1
        html += '<tr>';
        html += `<td class="fw-bold">D (${itemJ1.date})</td>`;
        html += `<td class="text-end numeric-value">${itemJ1.sum_assiette.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">${itemJ1.sum_impact.toFixed(3)}</td>`;
        
        const diffClass = itemJ1.sum_difference >= 0 ? 'text-success' : 'text-danger';
        html += `<td class="text-end numeric-value ${diffClass}">${itemJ1.sum_difference.toFixed(3)}</td>`;
        html += '</tr>';
    }
    
    // Ligne pour fichier J (aujourd'hui)
    if (dataJ.length > 0) {
        const itemJ = dataJ[0]; // Prendre la première date du fichier J
        html += '<tr>';
        html += `<td class="fw-bold">D-1 (${itemJ.date})</td>`;
        html += `<td class="text-end numeric-value">${itemJ.sum_assiette.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">${itemJ.sum_impact.toFixed(3)}</td>`;
        
        const diffClass = itemJ.sum_difference >= 0 ? 'text-success' : 'text-danger';
        html += `<td class="text-end numeric-value ${diffClass}">${itemJ.sum_difference.toFixed(3)}</td>`;
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère la section RESOURCES
 */
function generateResourcesSection(resourcesData) {
    if (resourcesData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur RESOURCES</h5>
                <p>${resourcesData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${resourcesData.title}</h3>
            </div>
            <div class="card-body p-0">
                <div class="table-container">
                    ${generateResourcesTableHTML(resourcesData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère le HTML du tableau RESOURCES avec variations quotidiennes et mensuelles
 */
function generateResourcesTableHTML(resourcesData) {
    if (!resourcesData.j || !resourcesData.jMinus1 || !resourcesData.mMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau RESOURCES (3 fichiers requis)</div>';
    }
    
    const dataJ = resourcesData.j;
    const dataJ1 = resourcesData.jMinus1;
    const dataM1 = resourcesData.mMinus1;
    
    // Créer mappings pour les variations
    const variationsMap = new Map();
    const monthlyVariationsMap = new Map();
    
    // Calculer les variations J vs J-1 et J vs M-1
    dataJ.forEach(itemJ => {
        // Variation quotidienne (J vs J-1)
        const itemJ1 = dataJ1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueJ1 = itemJ1 ? itemJ1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const dailyVariation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueJ1;
        
        // Variation mensuelle (J vs M-1)
        const itemM1 = dataM1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueM1 = itemM1 ? itemM1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const monthlyVariation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueM1;
        
        variationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            j1: valueJ1,
            variation: dailyVariation
        });
        
        monthlyVariationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            m1: valueM1,
            variation: monthlyVariation
        });
    });
    
    let html = `
        <table class="table table-bordered new-table resources-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">LCR ECO Groupe Métiers</th>
                    <th colspan="3" class="text-center header-j">Analysis Results (Bn €)</th>
                </tr>
                <tr>
                    <th class="text-center header-j">D (Today)</th>
                    <th class="text-center header-variation">Daily Variation vs D-1</th>
                    <th class="text-center header-variation">Monthly Variation vs M-1</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Générer les lignes
    dataJ.forEach(item => {
        const dailyVar = variationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        const monthlyVar = monthlyVariationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        
        const absDailyVariation = Math.abs(dailyVar.variation);
        const isDailyPositive = dailyVar.variation >= 0;
        
        const absMonthlyVariation = Math.abs(monthlyVar.variation);
        const isMonthlyPositive = monthlyVar.variation >= 0;
        
        html += '<tr>';
        html += `<td class="fw-bold">${item.LCR_ECO_GROUPE_METIERS}</td>`;
        html += `<td class="text-end numeric-value">${item.LCR_ECO_IMPACT_LCR_Bn.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">
                    ${absDailyVariation.toFixed(3)}
                    <span class="variation-indicator ${isDailyPositive ? 'positive' : 'negative'}">
                        ${isDailyPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += `<td class="text-end numeric-value">
                    ${absMonthlyVariation.toFixed(3)}
                    <span class="variation-indicator ${isMonthlyPositive ? 'positive' : 'negative'}">
                        ${isMonthlyPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le bloc Consumption & Resources avec analyse IA
 */
function generateConsumptionResourcesBlockSection(analysisResults) {
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">Consumption & Resources</h3>
            </div>
            <div class="card-body p-0">
    `;
    
    // Tableau CONSUMPTION
    if (analysisResults.consumption) {
        html += '<h5 class="text-secondary mb-3 px-3 pt-3">Consumption</h5>';
        html += '<div class="table-container mb-4">';
        html += generateConsumptionTableHTML(analysisResults.consumption.data);
        html += '</div>';
    }
    
    // Tableau RESOURCES
    if (analysisResults.resources) {
        html += '<h5 class="text-secondary mb-3 px-3">Resources</h5>';
        html += '<div class="table-container mb-4">';
        html += generateResourcesTableHTML(analysisResults.resources.data);
        html += '</div>';
    }
    
    // Zone d'analyse IA
    html += `
        <div class="px-3 pb-3">
            <h5 class="text-secondary mb-3">AI Analysis</h5>
            <div id="consumption-resources-analysis" class="analysis-loading">
                <div class="d-flex align-items-center justify-content-center py-4">
                    <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                    <span class="text-muted">Generating analysis...</span>
                </div>
            </div>
        </div>
    `;
    
    html += '</div></div>';
    
    // Déclencher l'analyse IA après un court délai
    setTimeout(() => {
        generateConsumptionResourcesAnalysis(analysisResults);
    }, 1000);
    
    return html;
}

/**
 * Génère l'analyse IA pour Consumption & Resources
 */
async function generateConsumptionResourcesAnalysis(analysisResults) {
    try {
        const analysisContainer = document.getElementById('consumption-resources-analysis');
        
        if (!analysisContainer) {
            console.error('Container d\'analyse introuvable');
            return;
        }
        
        // Préparer le contexte avec les données des deux tableaux
        const contextData = prepareConsumptionResourcesContext(analysisResults);
        
        // Appel à l'IA
        const response = await fetch('/api/analyze-consumption-resources', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                context_data: contextData
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                analysisContainer.innerHTML = `
                    <div class="ai-analysis-content">
                        <div class="analysis-text">
                            ${parseMarkdownToHtml(result.analysis)}
                        </div>
                    </div>
                `;
            } else {
                throw new Error(result.message || 'Erreur analyse');
            }
        } else {
            throw new Error('Erreur serveur');
        }
        
    } catch (error) {
        console.error('Erreur génération analyse IA:', error);
        
        const analysisContainer = document.getElementById('consumption-resources-analysis');
        if (analysisContainer) {
            analysisContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Analysis temporarily unavailable
                </div>
            `;
        }
    }
}

/**
 * Prépare le contexte pour l'analyse Consumption & Resources
 */
function prepareConsumptionResourcesContext(analysisResults) {
    const context = {
        consumption_data: null,
        resources_data: null,
        timestamp: new Date().toISOString()
    };
    
    if (analysisResults.consumption && analysisResults.consumption.data) {
        context.consumption_data = analysisResults.consumption.data;
    }
    
    if (analysisResults.resources && analysisResults.resources.data) {
        context.resources_data = analysisResults.resources.data;
    }
    
    return context;
}

/**
 * Génère la section CAPPAGE avec style TCD Excel professionnel
 */
function generateCappageSection(cappageData) {
    if (cappageData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur CAPPAGE TCD</h5>
                <p>${cappageData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <div class="d-flex justify-content-between align-items-center">
                    <h3 style="color: #76279b;" class="mb-1">${cappageData.title}</h3>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-container">
                    ${generateCappageTableHTML(cappageData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Version fallback pour affichage single-day (ancien format)
 */
function generateCappageSingleDayHTML(cappageData) {
    if (!cappageData.j) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau CAPPAGE TCD</div>';
    }
    
    const dataJ = cappageData.j;
    const pivotData = dataJ.pivot_data || [];
    const dates = dataJ.dates || [];
    
    if (pivotData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée CAPPAGE TCD disponible</div>';
    }
    
    // Calculer les totaux globaux par date
    const grandTotalsByDate = {};
    
    dates.forEach(date => {
        grandTotalsByDate[date] = 0;
    });
    
    pivotData.forEach(siGroup => {
        Object.keys(siGroup.si_totals_by_date).forEach(date => {
            if (grandTotalsByDate[date] !== undefined) {
                grandTotalsByDate[date] += siGroup.si_totals_by_date[date];
            }
        });
    });
    
    let html = `
        <table class="table table-bordered cappage-tcd-table">
            <thead class="table-dark">
                <tr>
                    <th class="align-middle tcd-header-row" style="width: 30%">SI Remettant / Commentaire</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;

    // En-têtes des dates
    html += `<th></th>`; // Colonne vide pour aligner avec "SI Remettant / Commentaire"
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header">${date}</th>`;
    });

    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Génération des lignes TCD avec hiérarchie
    pivotData.forEach((siGroup, siIndex) => {
        const commentaireDetails = siGroup.commentaire_details || [];
        
        // LIGNE DE SI REMETTANT - avec totaux directement
        html += `<tr class="tcd-section-row">`;
        html += `<td class="tcd-si-cell">
                    <div class="tcd-hierarchy-level-0">
                        <strong>${siGroup.si_remettant}</strong>
                    </div>
                </td>`;
        
        // Totaux SI Remettant pour chaque date
        dates.forEach(date => {
            const value = siGroup.si_totals_by_date[date] || 0;
            html += `<td class="text-end tcd-data-cell"><strong>${value.toFixed(3)}</strong></td>`;
        });
        
        html += `</tr>`;
        
        // LIGNES DE DÉTAIL : Commentaires indentés
        // N'afficher les détails QUE pour SI Remettant "CAPREOS"
        if (siGroup.si_remettant === "CAPREOS") {
            commentaireDetails.forEach((detail, detailIndex) => {
                html += `<tr class="tcd-detail-row">`;
                
                // Commentaire indenté
                html += `<td class="tcd-commentaire-detail">
                            <div class="tcd-hierarchy-level-1">
                                ${detail.commentaire}
                            </div>
                        </td>`;
                
                // Valeurs par date pour ce commentaire
                dates.forEach(date => {
                    const value = detail.date_values[date] || 0;
                    const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                    html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
                });
                
                html += '</tr>';
            });
        }
        // Pour SHORT_LCR et autres, on ne montre PAS les détails
        
        // Ligne de séparation entre les SI (sauf pour le dernier)
        if (siIndex < pivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 1}"></td></tr>`;
        }
    });

    // Ligne de grand total
    html += `
        <tr class="tcd-grand-total-row">
            <td class="tcd-grand-total-label">
                <strong>TOTAL</strong>
            </td>
    `;

    dates.forEach(date => {
        const value = grandTotalsByDate[date] || 0;
        html += `<td class="text-end tcd-grand-total-value">${value.toFixed(3)}</td>`;
    });

    html += '</tr>';
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau CAPPAGE avec historique multi-colonnes
 */
function generateCappageTableHTML(cappageData) {
    // Si pas de données historiques, afficher en mode classique
    if (!cappageData.historical || !cappageData.historical.dates) {
        return generateCappageSingleDayHTML(cappageData);
    }
    
    const dates = cappageData.historical.dates; // ["2025-09-10", "2025-09-09", ...]
    const dataByDate = cappageData.historical.data_by_date;
    
    // Construire la structure des lignes avec toutes les dates
    const allSiRemettants = new Set();
    const rowsData = {};
    
    // Collecter tous les SI Remettants et Commentaires
    dates.forEach(date => {
        const dayData = dataByDate[date];
        if (dayData && dayData.data && dayData.data.j && dayData.data.j.pivot_data) {
            dayData.data.j.pivot_data.forEach(siGroup => {
                allSiRemettants.add(siGroup.si_remettant);
                
                if (!rowsData[siGroup.si_remettant]) {
                    rowsData[siGroup.si_remettant] = {
                        commentaires: {},
                        totals: {}
                    };
                }
                
                // Stocker le total SI pour cette date
                rowsData[siGroup.si_remettant].totals[date] = siGroup.grand_total || 0;
                
                // Stocker les commentaires
                siGroup.commentaire_details.forEach(detail => {
                    if (!rowsData[siGroup.si_remettant].commentaires[detail.commentaire]) {
                        rowsData[siGroup.si_remettant].commentaires[detail.commentaire] = {};
                    }
                    rowsData[siGroup.si_remettant].commentaires[detail.commentaire][date] = detail.total || 0;
                });
            });
        }
    });
    
    // Générer le HTML
    let html = `
        <table class="table table-bordered cappage-tcd-table">
            <thead class="table-dark">
                <tr>
                    <th class="align-middle tcd-header-row" style="width: 30%">SI Remettant / Commentaire</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
                    <th></th>
    `;
    
    // En-têtes des dates
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header">${date}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    // Générer les lignes
    Array.from(allSiRemettants).forEach((siRemettant, siIndex) => {
        const siData = rowsData[siRemettant];
        
        // Ligne SI Remettant
        html += `<tr class="tcd-section-row">`;
        html += `<td class="tcd-si-cell"><div class="tcd-hierarchy-level-0"><strong>${siRemettant}</strong></div></td>`;
        
        dates.forEach(date => {
            const value = siData.totals[date] || 0;
            html += `<td class="text-end tcd-data-cell"><strong>${value.toFixed(3)}</strong></td>`;
        });
        
        html += `</tr>`;
        
        // Lignes de détail (commentaires)
        // N'afficher les détails QUE pour SI Remettant "CAPREOS"
        if (siRemettant === "CAPREOS") {
            Object.entries(siData.commentaires).forEach(([commentaire, values]) => {
                html += `<tr class="tcd-detail-row">`;
                html += `<td class="tcd-commentaire-detail"><div class="tcd-hierarchy-level-1">${commentaire}</div></td>`;
                
                dates.forEach(date => {
                    const value = values[date] || 0;
                    const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                    html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
                });
                
                html += `</tr>`;
            });
        }
        // Pour SHORT_LCR et autres, on ne montre PAS les détails
        
        // Séparateur
        if (siIndex < allSiRemettants.size - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 1}"></td></tr>`;
        }
    });
    
    // Ligne de grand total
    html += `<tr class="tcd-grand-total-row"><td class="tcd-grand-total-label"><strong>TOTAL</strong></td>`;
    
    dates.forEach(date => {
        let grandTotal = 0;
        Object.values(rowsData).forEach(siData => {
            grandTotal += siData.totals[date] || 0;
        });
        html += `<td class="text-end tcd-grand-total-value">${grandTotal.toFixed(3)}</td>`;
    });
    
    html += `</tr></tbody></table>`;
    return html;
}

/**
 * Génère la section BUFFER & NCO avec style TCD Excel professionnel
 */
function generateBufferNcoSection(bufferNcoData) {
    if (bufferNcoData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur BUFFER & NCO TCD</h5>
                <p>${bufferNcoData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <div class="d-flex justify-content-between align-items-center">
                    <h3 style="color: #76279b;" class="mb-1">${bufferNcoData.title}</h3>
                </div>
            </div>
            <div class="card-body p-0">
                <!-- Tableau 1: BUFFER -->
                <div class="tcd-table-section">
                    <h5 class="text-primary mb-3 px-3 pt-3">
                        1. BUFFER Analysis
                        <small class="text-muted ms-2">(LCR_Catégorie = "1- Buffer")</small>
                    </h5>
                    <div class="table-container mb-4">
                        ${generateBufferNcoBufferTableHTML(bufferNcoData.data)}
                    </div>
                </div>
                
                <!-- Tableau 2: NCO -->
                <div class="tcd-table-section">
                    <h5 class="text-primary mb-3 px-3">
                        2. NCO Analysis
                    </h5>
                    <div class="table-container">
                        ${generateBufferNcoNcoTableHTML(bufferNcoData.data)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère le HTML du tableau BUFFER avec structure TCD Excel hiérarchique
 */
function generateBufferNcoBufferTableHTML(bufferData) {
    // Si pas de données historiques
    if (!bufferData.historical || !bufferData.historical.dates) {
        return generateBufferNcoBufferSingleDayHTML(bufferData);
    }
    
    const dates = bufferData.historical.dates;
    const dataByDate = bufferData.historical.data_by_date;
    
    // Structure : section -> client -> {date: value}
    const allSections = new Set();
    const rowsData = {};
    
    dates.forEach(date => {
        const dayData = dataByDate[date];
        if (Array.isArray(dayData)) {
            dayData.forEach(sectionGroup => {
                allSections.add(sectionGroup.section);
                
                if (!rowsData[sectionGroup.section]) {
                    rowsData[sectionGroup.section] = {
                        clients: {},
                        totals: {}
                    };
                }
                
                rowsData[sectionGroup.section].totals[date] = 
                    Object.values(sectionGroup.section_totals_by_date || {}).reduce((a, b) => a + b, 0);
                
                (sectionGroup.client_details || []).forEach(detail => {
                    if (!rowsData[sectionGroup.section].clients[detail.client]) {
                        rowsData[sectionGroup.section].clients[detail.client] = {};
                    }
                    const clientTotal = Object.values(detail.date_values || {}).reduce((a, b) => a + b, 0);
                    rowsData[sectionGroup.section].clients[detail.client][date] = clientTotal;
                });
            });
        }
    });
    
    let html = `
        <table class="table table-bordered buffer-nco-tcd-table">
            <thead class="table-dark">
                <tr>
                    <th class="align-middle tcd-header-row" style="width: 35%">Section / Client</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr><th></th>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header">${date}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    Array.from(allSections).forEach((section, idx) => {
        const sectionData = rowsData[section];
        
        html += `<tr class="tcd-section-row">`;
        html += `<td class="tcd-section-cell"><div class="tcd-hierarchy-level-0"><strong>${section}</strong></div></td>`;
        
        dates.forEach(date => {
            const value = sectionData.totals[date] || 0;
            html += `<td class="text-end tcd-data-cell"><strong>${value.toFixed(3)}</strong></td>`;
        });
        html += `</tr>`;
        
        // LIGNES DE DÉTAIL : Clients indentés
        // N'afficher les détails QUE pour la section "1.1- Cash"
        if (section === "1.1- Cash") {
            Object.entries(sectionData.clients).forEach(([client, values]) => {
                html += `<tr class="tcd-detail-row">`;
                html += `<td class="tcd-client-detail"><div class="tcd-hierarchy-level-1">${client}</div></td>`;
                
                dates.forEach(date => {
                    const value = values[date] || 0;
                    const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                    html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
                });
                html += `</tr>`;
            });
        }
        // Pour toutes les autres sections, on ne montre PAS les détails clients
        
        if (idx < allSections.size - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 1}"></td></tr>`;
        }
    });
    
    html += `<tr class="tcd-grand-total-row"><td class="tcd-grand-total-label"><strong>TOTAL BUFFER</strong></td>`;
    dates.forEach(date => {
        let grandTotal = 0;
        Object.values(rowsData).forEach(s => grandTotal += s.totals[date] || 0);
        html += `<td class="text-end tcd-grand-total-value">${grandTotal.toFixed(3)}</td>`;
    });
    html += `</tr></tbody></table>`;
    return html;
}

/**
 * Génère le HTML du tableau BUFFER avec structure TCD Excel hiérarchique (ancien pour fallback)
 */
function generateBufferNcoBufferSingleDayHTML(bufferNcoData) {
    if (!bufferNcoData.j) {
        return '<div class="alert alert-warning">Données BUFFER insuffisantes</div>';
    }
    
    const dataJ = bufferNcoData.j;
    const bufferPivotData = dataJ.buffer_pivot_data || [];
    const dates = dataJ.dates || [];
    
    if (bufferPivotData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée BUFFER TCD disponible</div>';
    }
    
    // Calculer les totaux globaux par date pour BUFFER
    const grandTotalsByDate = {};
    dates.forEach(date => {
        grandTotalsByDate[date] = 0;
    });
    
    bufferPivotData.forEach(sectionGroup => {
        Object.keys(sectionGroup.section_totals_by_date).forEach(date => {
            if (grandTotalsByDate[date] !== undefined) {
                grandTotalsByDate[date] += sectionGroup.section_totals_by_date[date];
            }
        });
    });
    
    let html = `
        <table class="table table-bordered buffer-nco-tcd-table">
            <thead class="table-dark">
                <tr>
                    <th class="align-middle tcd-header-row" style="width: 35%">Section / Client</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;

    // En-têtes des dates
    html += `<th></th>`; // Colonne vide pour aligner avec "Section / Client"
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header">${date}</th>`;
    });

    html += `
                </tr>
            </thead>
            <tbody>
    `;
        
    // Génération des lignes TCD avec hiérarchie Section > Client
    bufferPivotData.forEach((sectionGroup, sectionIndex) => {
        const clientDetails = sectionGroup.client_details || [];
        
        // LIGNE DE SECTION - avec totaux directement
        html += `<tr class="tcd-section-row">`;
        html += `<td class="tcd-section-cell">
                    <div class="tcd-hierarchy-level-0">
                        <strong>${sectionGroup.section}</strong>
                    </div>
                </td>`;
        
        // Totaux Section pour chaque date
        dates.forEach(date => {
            const value = sectionGroup.section_totals_by_date[date] || 0;
            html += `<td class="text-end tcd-data-cell"><strong>${value.toFixed(3)}</strong></td>`;
        });
        
        html += `</tr>`;
        
        // LIGNES DE DÉTAIL : Clients indentés
        // N'afficher les détails QUE pour la section "1.1- Cash"
        if (sectionGroup.section === "1.1- Cash") {
            clientDetails.forEach((detail, detailIndex) => {
                html += `<tr class="tcd-detail-row">`;
                
                // Client indenté
                html += `<td class="tcd-client-detail">
                            <div class="tcd-hierarchy-level-1">
                                ${detail.client}
                            </div>
                        </td>`;
                
                // Valeurs par date
                dates.forEach(date => {
                    const value = detail.date_values[date] || 0;
                    const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                    html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
                });
                
                html += '</tr>';
            });
        }
        // Pour toutes les autres sections, on ne montre PAS les détails clients
        
        // Ligne de séparation
        if (sectionIndex < bufferPivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 1}"></td></tr>`;
        }
    });

    // Grand total BUFFER
    html += `
        <tr class="tcd-grand-total-row">
            <td class="tcd-grand-total-label">
                <strong>TOTAL BUFFER</strong>
            </td>
    `;
    
    dates.forEach(date => {
        const value = grandTotalsByDate[date] || 0;
        html += `<td class="text-end tcd-grand-total-value">${value.toFixed(3)}</td>`;
    });
    
    html += '</tr>';
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau NCO avec structure TCD simple
 */
function generateBufferNcoNcoSingleDayHTML(bufferNcoData) {
    if (!bufferNcoData.j) {
        return '<div class="alert alert-warning">Données NCO insuffisantes</div>';
    }
    
    const dataJ = bufferNcoData.j;
    const ncoPivotData = dataJ.nco_pivot_data || [];
    const dates = dataJ.dates || [];
    
    if (ncoPivotData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée NCO TCD disponible</div>';
    }
    
    // Calculer les totaux globaux par date pour NCO
    const grandTotalsByDate = {};
    dates.forEach(date => {
        grandTotalsByDate[date] = 0;
    });
    
    ncoPivotData.forEach(categorieGroup => {
        Object.keys(categorieGroup.date_values).forEach(date => {
            if (grandTotalsByDate[date] !== undefined) {
                grandTotalsByDate[date] += categorieGroup.date_values[date];
            }
        });
    });
    
    let html = `
        <table class="table table-bordered buffer-nco-tcd-table nco-table">
            <thead class="table-success">
                <tr>
                    <th rowspan="2" class="align-middle tcd-header-row-nco">LCR Catégorie</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col-nco">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    // En-têtes des dates
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header-nco">${date}</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Génération des lignes NCO (simple, pas de hiérarchie)
    ncoPivotData.forEach((categorieGroup, index) => {
        html += `<tr class="tcd-nco-row">`;
        html += `<td class="tcd-categorie-cell">
                    <strong>${categorieGroup.categorie}</strong>
                 </td>`;
        
        // Valeurs par date
        dates.forEach(date => {
            const value = categorieGroup.date_values[date] || 0;
            const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell-nco';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        
        html += '</tr>';
    });
    
    // Ligne de grand total NCO
    html += `
        <tr class="tcd-grand-total-row-nco">
            <td class="tcd-grand-total-label-nco">
                <strong>TOTAL NCO</strong>
            </td>
    `;
    
    dates.forEach(date => {
        const value = grandTotalsByDate[date] || 0;
        html += `<td class="text-end tcd-grand-total-value-nco">${value.toFixed(3)}</td>`;
    });
    
    html += '</tr>';
    html += '</tbody></table>';
    return html;
}

function generateBufferNcoNcoTableHTML(ncoData) {
    if (!ncoData.historical || !ncoData.historical.dates) {
        return generateBufferNcoNcoSingleDayHTML(ncoData);
    }
    
    const dates = ncoData.historical.dates;
    const dataByDate = ncoData.historical.data_by_date;
    
    const allCategories = new Set();
    const rowsData = {};
    
    dates.forEach(date => {
        const dayData = dataByDate[date];
        if (Array.isArray(dayData)) {
            dayData.forEach(catGroup => {
                allCategories.add(catGroup.categorie);
                
                if (!rowsData[catGroup.categorie]) {
                    rowsData[catGroup.categorie] = {};
                }
                
                const catTotal = Object.values(catGroup.date_values || {}).reduce((a, b) => a + b, 0);
                rowsData[catGroup.categorie][date] = catTotal;
            });
        }
    });
    
    let html = `
        <table class="table table-bordered buffer-nco-tcd-table nco-table">
            <thead class="table-success">
                <tr>
                    <th rowspan="2" class="align-middle tcd-header-row-nco">LCR Catégorie</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col-nco">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center tcd-date-header-nco">${date}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    Array.from(allCategories).forEach(categorie => {
        html += `<tr class="tcd-nco-row">`;
        html += `<td class="tcd-categorie-cell"><strong>${categorie}</strong></td>`;
        
        dates.forEach(date => {
            const value = rowsData[categorie][date] || 0;
            const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell-nco';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        html += `</tr>`;
    });
    
    html += `<tr class="tcd-grand-total-row-nco"><td class="tcd-grand-total-label-nco"><strong>TOTAL NCO</strong></td>`;
    dates.forEach(date => {
        let grandTotal = 0;
        Object.values(rowsData).forEach(values => grandTotal += values[date] || 0);
        html += `<td class="text-end tcd-grand-total-value-nco">${grandTotal.toFixed(3)}</td>`;
    });
    html += `</tr></tbody></table>`;
    return html;
}

/**
 * Génère la section CONSUMPTION & RESOURCES (deux tableaux empilés)
 */
function generateConsumptionResourcesSection(consumptionResourcesData) {
    if (consumptionResourcesData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur CONSUMPTION & RESOURCES</h5>
                <p>${consumptionResourcesData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${consumptionResourcesData.title}</h3>
            </div>
            <div class="card-body p-0">
                <!-- Tableau CONSUMPTION -->
                <h5 class="text-primary mb-3 px-3 pt-3">1. CONSUMPTION</h5>
                <div class="table-container mb-4">
                    ${generateConsumptionResourcesConsumptionTableHTML(consumptionResourcesData.data)}
                </div>
                
                <!-- Tableau RESOURCES -->
                <h5 class="text-primary mb-3 px-3">2. RESOURCES</h5>
                <div class="table-container">
                    ${generateConsumptionResourcesResourcesTableHTML(consumptionResourcesData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère le HTML du tableau CONSUMPTION avec style Excel professionnel
 */
function generateConsumptionSingleDayHTML(consumptionResourcesData) {
    if (!consumptionResourcesData.j) {
        return '<div class="alert alert-warning">Données CONSUMPTION insuffisantes</div>';
    }
    
    const dataJ = consumptionResourcesData.j;
    const consumptionData = dataJ.consumption_data || [];
    const dates = dataJ.dates || [];
    
    if (consumptionData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée CONSUMPTION disponible</div>';
    }
    
    // Calculer les totaux par date
    const totalsByDate = {};
    let grandTotal = 0;
    
    dates.forEach(date => {
        totalsByDate[date] = 0;
    });
    
    consumptionData.forEach(item => {
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            totalsByDate[date] += value;
            grandTotal += value;
        });
    });
    
    let html = `
        <table class="table table-bordered consumption-excel-table">
            <thead class="table-dark">
                <tr>
                    <th rowspan="2" class="align-middle cons-header-row">LCR ECO Groupe Métiers</th>
                    <th colspan="${dates.length}" class="text-center cons-header-col">LCR ECO Impact by Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center cons-date-header">${date}</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Lignes de données avec totaux par ligne
    consumptionData.forEach((item, index) => {
        let rowTotal = 0;
        html += `<tr class="cons-data-row">`;
        html += `<td class="cons-groupe-cell">
                    <div class="cons-group-label">
                        <strong>${item.lcr_eco_groupe_metiers}</strong>
                    </div>
                 </td>`;
        
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            rowTotal += value;
            const cellClass = value === 0 ? 'cons-zero-value' : 'cons-data-cell';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        
        // Total par ligne
        html += '</tr>';
    });
    
    // Ligne de totaux
    html += `
        <tr class="cons-grand-total-row">
            <td class="cons-grand-total-label">
                <strong>TOTAL CONSUMPTION</strong>
            </td>
    `;
    
    let finalGrandTotal = 0;
    dates.forEach(date => {
        const value = totalsByDate[date];
        finalGrandTotal += value;
        html += `<td class="text-end cons-grand-total-value">${value.toFixed(3)}</td>`;
    });
    
    html += '</tr>';
    
    html += '</tbody></table>';
    return html;
}

function generateConsumptionResourcesConsumptionTableHTML(consumptionData) {
    if (!consumptionData.historical || !consumptionData.historical.dates) {
        return generateConsumptionSingleDayHTML(consumptionData);
    }
    
    const dates = consumptionData.historical.dates;
    const dataByDate = consumptionData.historical.data_by_date;
    
    const allGroupes = new Set();
    const rowsData = {};
    
    dates.forEach(date => {
        const dayData = dataByDate[date];
        if (Array.isArray(dayData)) {
            dayData.forEach(item => {
                allGroupes.add(item.lcr_eco_groupe_metiers);
                
                if (!rowsData[item.lcr_eco_groupe_metiers]) {
                    rowsData[item.lcr_eco_groupe_metiers] = {};
                }
                
                const total = Object.values(item.dates || {}).reduce((a, b) => a + b, 0);
                rowsData[item.lcr_eco_groupe_metiers][date] = total;
            });
        }
    });
    
    let html = `
        <table class="table table-bordered consumption-excel-table">
            <thead class="table-dark">
                <tr>
                    <th rowspan="2" class="align-middle cons-header-row">LCR ECO Groupe Métiers</th>
                    <th colspan="${dates.length}" class="text-center cons-header-col">LCR ECO Impact by Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center cons-date-header">${date}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    Array.from(allGroupes).forEach(groupe => {
        html += `<tr class="cons-data-row">`;
        html += `<td class="cons-groupe-cell"><div class="cons-group-label"><strong>${groupe}</strong></div></td>`;
        
        dates.forEach(date => {
            const value = rowsData[groupe][date] || 0;
            const cellClass = value === 0 ? 'cons-zero-value' : 'cons-data-cell';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        html += `</tr>`;
    });
    
    html += `<tr class="cons-grand-total-row"><td class="cons-grand-total-label"><strong>TOTAL CONSUMPTION</strong></td>`;
    dates.forEach(date => {
        let grandTotal = 0;
        Object.values(rowsData).forEach(values => grandTotal += values[date] || 0);
        html += `<td class="text-end cons-grand-total-value">${grandTotal.toFixed(3)}</td>`;
    });
    html += `</tr></tbody></table>`;
    return html;
}

/**
 * Génère le HTML du tableau RESOURCES avec style Excel professionnel
 */
function generateResourcesSingleDayHTML(consumptionResourcesData) {
    if (!consumptionResourcesData.j) {
        return '<div class="alert alert-warning">Données RESOURCES insuffisantes</div>';
    }
    
    const dataJ = consumptionResourcesData.j;
    const resourcesData = dataJ.resources_data || [];
    const dates = dataJ.dates || [];
    
    if (resourcesData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée RESOURCES disponible</div>';
    }
    
    // Calculer les totaux par date
    const totalsByDate = {};
    let grandTotal = 0;
    
    dates.forEach(date => {
        totalsByDate[date] = 0;
    });
    
    resourcesData.forEach(item => {
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            totalsByDate[date] += value;
            grandTotal += value;
        });
    });
    
    let html = `
        <table class="table table-bordered resources-excel-table">
            <thead class="table-success">
                <tr>
                    <th rowspan="2" class="align-middle res-header-row">LCR ECO Groupe Métiers</th>
                    <th colspan="${dates.length}" class="text-center res-header-col">LCR ECO Impact by Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center res-date-header">${date}</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Lignes de données avec totaux par ligne
    resourcesData.forEach((item, index) => {
        let rowTotal = 0;
        html += `<tr class="res-data-row">`;
        html += `<td class="res-groupe-cell">
                    <div class="res-group-label">
                        <strong>${item.lcr_eco_groupe_metiers}</strong>
                    </div>
                 </td>`;
        
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            rowTotal += value;
            const cellClass = value === 0 ? 'res-zero-value' : 'res-data-cell';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        
        // Total par ligne
        html += '</tr>';
    });
    
    // Ligne de totaux
    html += `
        <tr class="res-grand-total-row">
            <td class="res-grand-total-label">
                <strong>TOTAL RESOURCES</strong>
            </td>
    `;
    
    let finalGrandTotal = 0;
    dates.forEach(date => {
        const value = totalsByDate[date];
        finalGrandTotal += value;
        html += `<td class="text-end res-grand-total-value">${value.toFixed(3)}</td>`;
    });
    
    html += '</tr>';
    
    html += '</tbody></table>';
    return html;
}

function generateConsumptionResourcesResourcesTableHTML(resourcesData) {
    if (!resourcesData.historical || !resourcesData.historical.dates) {
        return generateResourcesSingleDayHTML(resourcesData);
    }
    
    const dates = resourcesData.historical.dates;
    const dataByDate = resourcesData.historical.data_by_date;
    
    const allGroupes = new Set();
    const rowsData = {};
    
    dates.forEach(date => {
        const dayData = dataByDate[date];
        if (Array.isArray(dayData)) {
            dayData.forEach(item => {
                allGroupes.add(item.lcr_eco_groupe_metiers);
                
                if (!rowsData[item.lcr_eco_groupe_metiers]) {
                    rowsData[item.lcr_eco_groupe_metiers] = {};
                }
                
                const total = Object.values(item.dates || {}).reduce((a, b) => a + b, 0);
                rowsData[item.lcr_eco_groupe_metiers][date] = total;
            });
        }
    });
    
    let html = `
        <table class="table table-bordered resources-excel-table">
            <thead class="table-success">
                <tr>
                    <th rowspan="2" class="align-middle res-header-row">LCR ECO Groupe Métiers</th>
                    <th colspan="${dates.length}" class="text-center res-header-col">LCR ECO Impact by Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center res-date-header">${date}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    Array.from(allGroupes).forEach(groupe => {
        html += `<tr class="res-data-row">`;
        html += `<td class="res-groupe-cell"><div class="res-group-label"><strong>${groupe}</strong></div></td>`;
        
        dates.forEach(date => {
            const value = rowsData[groupe][date] || 0;
            const cellClass = value === 0 ? 'res-zero-value' : 'res-data-cell';
            html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
        });
        html += `</tr>`;
    });
    
    html += `<tr class="res-grand-total-row"><td class="res-grand-total-label"><strong>TOTAL RESOURCES</strong></td>`;
    dates.forEach(date => {
        let grandTotal = 0;
        Object.values(rowsData).forEach(values => grandTotal += values[date] || 0);
        html += `<td class="text-end res-grand-total-value">${grandTotal.toFixed(3)}</td>`;
    });
    html += `</tr></tbody></table>`;
    return html;
}

// ================================= CHATBOT =================================


/**
 * Affiche la section chatbot après les analyses
 */
function showChatbot() {
    document.getElementById('chatbot-section').style.display = 'block';

    // Initialiser le drag & drop pour les documents
    initializeDocumentDragAndDrop();
    
    // Message initial du bot
    if (chatMessages.length === 0) {
        addChatMessage('assistant', 'Hello! I am your LCR (Liquidity Coverage Ratio) banking analyst. I have just processed your comprehensive LCR analysis including BUFFER, CONSUMPTION, RESOURCES, CAPPAGE, and NCO tables across multiple time periods (D, D-1, M-1). \n\nI can help you:\n- Analyze variations and trends in your liquidity data\n- Identify regulatory compliance issues\n- Explain business group performance\n- Provide strategic recommendations\n- Deep-dive into specific metrics or time periods\n\nWhat aspects of your LCR analysis would you like to explore?');
    }
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
        
        const response = await fetch('/api/uploaded-document', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            
            // Réinitialiser l'input
            const fileInput = document.getElementById('doc-upload');
            if (fileInput) {
                fileInput.value = '';
            }
            
            updateUploadedDocsList();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Document upload error:', error);
        showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
        
        // Réinitialiser l'input même en cas d'erreur
        const fileInput = document.getElementById('doc-upload');
        if (fileInput) {
            fileInput.value = '';
        }
    }
}

/**
 * Affiche l'aperçu d'un document
 */
async function previewDocument(filename) {
    try {
        const response = await fetch(`/api/document-preview/${encodeURIComponent(filename)}`);
        const result = await response.json();
        
        if (result.success) {
            // Créer un modal pour l'aperçu
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-file-alt me-2"></i>${filename}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="document-preview">
                                ${result.content_type === 'text' ? 
                                    `<pre class="p-3 bg-light rounded">${escapeHtml(result.preview)}</pre>` :
                                    `<div class="alert alert-info">
                                        <i class="fas fa-info-circle me-2"></i>
                                        Preview not available for this file type
                                    </div>`
                                }
                            </div>
                            <div class="mt-3">
                                <small class="text-muted">
                                    <strong>Size:</strong> ${formatFileSize(result.size)} • 
                                    <strong>Uploaded:</strong> ${new Date(result.upload_time).toLocaleString()}
                                    ${result.is_truncated ? ' • <span class="text-warning">Preview truncated</span>' : ''}
                                </small>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-danger" onclick="deleteDocument('${filename}')">
                                <i class="fas fa-trash me-2"></i>Delete
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
        } else {
            showNotification('Error loading preview', 'error');
        }
    } catch (error) {
        console.error('Preview error:', error);
        showNotification('Error displaying preview', 'error');
    }
}

/**
 * Supprime un document
 */
async function deleteDocument(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    
    try {
        const response = await fetch(`/api/delete-document/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Document deleted', 'success');
            
            // Fermer le modal si ouvert
            const modalElement = document.querySelector('.modal.show');
            if (modalElement) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) modal.hide();
            }
            
            // Réinitialiser l'input file pour permettre un nouvel upload
            const fileInput = document.getElementById('doc-upload');
            if (fileInput) {
                fileInput.value = '';
            }
            
            // Mettre à jour la liste
            updateUploadedDocsList();
        } else {
            throw new Error('Delete failed');
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        showNotification('Error deleting document', 'error');
    }
}

/**
 * Échappe le HTML pour affichage sécurisé
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
                    <div class="doc-item d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <i class="fas fa-file-alt me-2"></i>
                            <strong>${doc.filename}</strong>
                            <br><small class="text-muted">${formatFileSize(doc.size)} - ${new Date(doc.upload_time).toLocaleTimeString()}</small>
                        </div>
                        <div class="btn-group btn-group-sm ms-2">
                            <button class="btn btn-outline-primary" onclick="previewDocument('${doc.filename}')" title="Preview">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-danger" onclick="deleteDocument('${doc.filename}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
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


// ================================= ADMINISTRATION =================================


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

// ================================= EXPORT =================================


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


// ================================= AUTHENTIFICATION =================================


async function logout() {
    if (confirm('Are you sure you want to logout?')) {
        const response = await fetch('/api/logout', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            window.location.href = result.redirect;
        }
    }
}




