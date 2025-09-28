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
    initializeFileUploads();
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
            html += generateCappageSection(analysisResults.cappage);
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }

        // Tableaux BUFFER & NCO empilés
        if (analysisResults.buffer_nco) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += generateBufferNcoSection(analysisResults.buffer_nco);
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }

        // Tableaux CONSUMPTION & RESOURCES empilés
        if (analysisResults.consumption_resources) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += generateConsumptionResourcesSection(analysisResults.consumption_resources);
            html += '</div>';
            html += '</div>';
            html += '</div>';
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
        
        setTimeout(() => {
            resolve();
        }, 500);
    });
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
                    <div class="badge bg-info">TCD with Variations</div>
                </div>
                <small class="text-muted">
                    <i class="fas fa-filter me-1"></i>LCR_Catégorie: "1- Buffer" • 
                    <i class="fas fa-table me-1"></i>Pivot: Section > Client × [D, Δ D-1, Δ M-1]
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
                    <th rowspan="2" class="align-middle tcd-header-row">LCR Template Section 1</th>
                    <th rowspan="2" class="align-middle tcd-header-row">Libellé Client</th>
                    <th class="text-center tcd-header-col">D (Today)</th>
                    <th class="text-center tcd-header-variation">Variation Daily</th>
                    <th class="text-center tcd-header-variation">Variation Monthly</th>
                </tr>
                <tr>
                    <th class="text-center tcd-value-header">Bn €</th>
                    <th class="text-center tcd-variation-header">D - D-1 (Bn €)</th>
                    <th class="text-center tcd-variation-header">D - M-1 (Bn €)</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Génération des lignes TCD avec hiérarchie
    pivotData.forEach((sectionGroup, sectionIndex) => {
        const clientDetails = sectionGroup.client_details || [];
        const totalRowsForSection = clientDetails.length + 1; // +1 pour la ligne de total
        
        // Lignes de détail par client
        clientDetails.forEach((detail, detailIndex) => {
            html += `<tr class="tcd-detail-row">`;
            
            // Cellule Section (fusionnée pour tous les détails + total)
            if (detailIndex === 0) {
                html += `<td rowspan="${totalRowsForSection}" class="tcd-section-cell align-middle">
                            <div class="tcd-section-label">
                                <i class="fas fa-plus-square text-primary me-2"></i>
                                <strong>${sectionGroup.section}</strong>
                            </div>
                         </td>`;
            }
            
            // Cellule Client avec indentation
            html += `<td class="tcd-client-detail">
                        <span class="tcd-indent">└─</span> ${detail.client}
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
        
        // Ligne de total pour la Section
        html += `<tr class="tcd-section-total-row">`;
        html += `<td class="tcd-section-total-label"><strong>Total ${sectionGroup.section}</strong></td>`;
        
        // Total Section
        html += `<td class="text-end tcd-section-total">${(sectionGroup.section_total_j || 0).toFixed(3)}</td>`;
        
        // Variation Daily Section
        const sectionVarDaily = sectionGroup.section_variation_daily || 0;
        const sectionDailyClass = sectionVarDaily >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
        const sectionDailyIcon = sectionVarDaily >= 0 ? '▲' : '▼';
        html += `<td class="text-end tcd-section-total ${sectionDailyClass}">
                    ${sectionVarDaily >= 0 ? '+' : ''}${sectionVarDaily.toFixed(3)}
                    <span class="variation-icon">${sectionDailyIcon}</span>
                 </td>`;
        
        // Variation Monthly Section
        const sectionVarMonthly = sectionGroup.section_variation_monthly || 0;
        const sectionMonthlyClass = sectionVarMonthly >= 0 ? 'tcd-positive-var' : 'tcd-negative-var';
        const sectionMonthlyIcon = sectionVarMonthly >= 0 ? '▲' : '▼';
        html += `<td class="text-end tcd-section-total ${sectionMonthlyClass}">
                    ${sectionVarMonthly >= 0 ? '+' : ''}${sectionVarMonthly.toFixed(3)}
                    <span class="variation-icon">${sectionMonthlyIcon}</span>
                 </td>`;
        
        html += '</tr>';
        
        // Ligne de séparation entre les sections (sauf pour la dernière)
        if (sectionIndex < pivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="5"></td></tr>`;
        }
    });
    
    // Ligne de grand total général
    html += `
        <tr class="tcd-grand-total-row">
            <td colspan="2" class="tcd-grand-total-label">
                <strong><i class="fas fa-calculator me-2"></i>GRAND TOTAL</strong>
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
                    <div class="badge bg-info">TCD Excel Style</div>
                </div>
                <small class="text-muted">
                    <i class="fas fa-filter me-1"></i>SI Remettant: SHORT_LCR, CAPREOS • 
                    <i class="fas fa-table me-1"></i>Pivot: SI Remettant > Commentaire × Date d'arrêté
                </small>
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
 * Génère le HTML du tableau CAPPAGE avec structure TCD Excel professionnelle
 */
function generateCappageTableHTML(cappageData) {
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
                    <th rowspan="2" class="align-middle tcd-header-row">SI Remettant</th>
                    <th rowspan="2" class="align-middle tcd-header-row">Commentaire</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    // En-têtes des dates
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
        const totalRowsForSI = commentaireDetails.length + 1; // +1 pour la ligne de total
        
        // Lignes de détail par commentaire
        commentaireDetails.forEach((detail, detailIndex) => {
            html += `<tr class="tcd-detail-row">`;
            
            // Cellule SI Remettant (fusionnée pour tous les détails + total)
            if (detailIndex === 0) {
                html += `<td rowspan="${totalRowsForSI}" class="tcd-si-cell align-middle">
                            <div class="tcd-group-label">
                                <i class="fas fa-plus-square text-primary me-2"></i>
                                <strong>${siGroup.si_remettant}</strong>
                            </div>
                         </td>`;
            }
            
            // Cellule Commentaire avec indentation
            html += `<td class="tcd-commentaire-detail">
                        <span class="tcd-indent">└─</span> ${detail.commentaire}
                     </td>`;
            
            // Valeurs par date
            dates.forEach(date => {
                const value = detail.date_values[date] || 0;
                const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
            });
            
            html += '</tr>';
        });
        
        // Ligne de total pour le SI Remettant
        html += `<tr class="tcd-si-total-row">`;
        html += `<td class="tcd-total-label"><strong>Total ${siGroup.si_remettant}</strong></td>`;
        
        // Totaux par date pour ce SI
        dates.forEach(date => {
            const value = siGroup.si_totals_by_date[date] || 0;
            html += `<td class="text-end tcd-si-total">${value.toFixed(3)}</td>`;
        });
        
        html += '</tr>';
        
        // Ligne de séparation entre les groupes SI (sauf pour le dernier)
        if (siIndex < pivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 2}"></td></tr>`;
        }
    });
    
    // Ligne de grand total général
    html += `
        <tr class="tcd-grand-total-row">
            <td colspan="2" class="tcd-grand-total-label">
                <strong><i class="fas fa-calculator me-2"></i>GRAND TOTAL</strong>
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
                    <div class="badge bg-info">TCD Excel Style</div>
                </div>
                <small class="text-muted">
                    <i class="fas fa-table me-1"></i>Deux tableaux croisés dynamiques : BUFFER (filtrée) + NCO (complète)
                </small>
            </div>
            <div class="card-body p-0">
                <!-- Tableau 1: BUFFER -->
                <div class="tcd-table-section">
                    <h5 class="text-primary mb-3 px-3 pt-3">
                        <i class="fas fa-shield-alt me-2"></i>1. BUFFER Analysis
                        <small class="text-muted ms-2">(LCR_Catégorie = "1- Buffer")</small>
                    </h5>
                    <div class="table-container mb-4">
                        ${generateBufferNcoBufferTableHTML(bufferNcoData.data)}
                    </div>
                </div>
                
                <!-- Tableau 2: NCO -->
                <div class="tcd-table-section">
                    <h5 class="text-primary mb-3 px-3">
                        <i class="fas fa-chart-bar me-2"></i>2. NCO Analysis
                        <small class="text-muted ms-2">(All Categories)</small>
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
function generateBufferNcoBufferTableHTML(bufferNcoData) {
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
                    <th rowspan="2" class="align-middle tcd-header-row">LCR Template Section 1</th>
                    <th rowspan="2" class="align-middle tcd-header-row">Libellé Client</th>
                    <th colspan="${dates.length}" class="text-center tcd-header-col">LCR Assiette Pondérée par Date (Bn €)</th>
                </tr>
                <tr>
    `;
    
    // En-têtes des dates
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
        const totalRowsForSection = clientDetails.length + 1; // +1 pour la ligne de total
        
        // Lignes de détail par client
        clientDetails.forEach((detail, detailIndex) => {
            html += `<tr class="tcd-detail-row">`;
            
            // Cellule Section (fusionnée pour tous les clients + total)
            if (detailIndex === 0) {
                html += `<td rowspan="${totalRowsForSection}" class="tcd-section-cell align-middle">
                            <div class="tcd-group-label">
                                <i class="fas fa-folder-open text-success me-2"></i>
                                <strong>${sectionGroup.section}</strong>
                            </div>
                         </td>`;
            }
            
            // Cellule Client avec indentation
            html += `<td class="tcd-client-detail">
                        <span class="tcd-indent">├─</span> ${detail.client}
                     </td>`;
            
            // Valeurs par date
            dates.forEach(date => {
                const value = detail.date_values[date] || 0;
                const cellClass = value === 0 ? 'tcd-zero-value' : 'tcd-data-cell';
                html += `<td class="text-end ${cellClass}">${value.toFixed(3)}</td>`;
            });
            
            html += '</tr>';
        });
        
        // Ligne de total pour la Section
        html += `<tr class="tcd-section-total-row">`;
        html += `<td class="tcd-total-label"><strong>Total ${sectionGroup.section}</strong></td>`;
        
        // Totaux par date pour cette section
        dates.forEach(date => {
            const value = sectionGroup.section_totals_by_date[date] || 0;
            html += `<td class="text-end tcd-section-total">${value.toFixed(3)}</td>`;
        });
        
        html += '</tr>';
        
        // Ligne de séparation entre les sections (sauf pour la dernière)
        if (sectionIndex < bufferPivotData.length - 1) {
            html += `<tr class="tcd-separator"><td colspan="${dates.length + 2}"></td></tr>`;
        }
    });
    
    // Ligne de grand total BUFFER
    html += `
        <tr class="tcd-grand-total-row">
            <td colspan="2" class="tcd-grand-total-label">
                <strong><i class="fas fa-calculator me-2"></i>GRAND TOTAL BUFFER</strong>
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
function generateBufferNcoNcoTableHTML(bufferNcoData) {
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
                <strong><i class="fas fa-calculator me-2"></i>GRAND TOTAL NCO</strong>
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
                <h5 class="text-primary mb-3 px-3 pt-3">1. CONSUMPTION (Filtered Groups)</h5>
                <div class="table-container mb-4">
                    ${generateConsumptionResourcesConsumptionTableHTML(consumptionResourcesData.data)}
                </div>
                
                <!-- Tableau RESOURCES -->
                <h5 class="text-primary mb-3 px-3">2. RESOURCES (Filtered Groups)</h5>
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
function generateConsumptionResourcesConsumptionTableHTML(consumptionResourcesData) {
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
                    <th rowspan="2" class="align-middle cons-total-header">Total (Bn €)</th>
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
                        <i class="fas fa-chart-line text-primary me-2"></i>
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
        html += `<td class="text-end cons-row-total">${rowTotal.toFixed(3)}</td>`;
        html += '</tr>';
    });
    
    // Ligne de totaux
    html += `
        <tr class="cons-grand-total-row">
            <td class="cons-grand-total-label">
                <strong><i class="fas fa-calculator me-2"></i>TOTAL CONSUMPTION</strong>
            </td>
    `;
    
    let finalGrandTotal = 0;
    dates.forEach(date => {
        const value = totalsByDate[date];
        finalGrandTotal += value;
        html += `<td class="text-end cons-grand-total-value">${value.toFixed(3)}</td>`;
    });
    
    html += `<td class="text-end cons-grand-total-final">${finalGrandTotal.toFixed(3)}</td>`;
    html += '</tr>';
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau RESOURCES avec style Excel professionnel
 */
function generateConsumptionResourcesResourcesTableHTML(consumptionResourcesData) {
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
                    <th rowspan="2" class="align-middle res-total-header">Total (Bn €)</th>
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
                        <i class="fas fa-coins text-success me-2"></i>
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
        html += `<td class="text-end res-row-total">${rowTotal.toFixed(3)}</td>`;
        html += '</tr>';
    });
    
    // Ligne de totaux
    html += `
        <tr class="res-grand-total-row">
            <td class="res-grand-total-label">
                <strong><i class="fas fa-calculator me-2"></i>TOTAL RESOURCES</strong>
            </td>
    `;
    
    let finalGrandTotal = 0;
    dates.forEach(date => {
        const value = totalsByDate[date];
        finalGrandTotal += value;
        html += `<td class="text-end res-grand-total-value">${value.toFixed(3)}</td>`;
    });
    
    html += `<td class="text-end res-grand-total-final">${finalGrandTotal.toFixed(3)}</td>`;
    html += '</tr>';
    
    html += '</tbody></table>';
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




