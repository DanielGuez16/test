/**
 * static/js/main.js
 * 
 * Steering ALM Metrics - Interface JavaScript
 * ==========================================
 * 
 * Gestion des uploads, analyses et affichage des résultats TCD
 */

// ================================= VARIABLES GLOBALES  =================================


let filesReady = { j: false, j1: false };
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
        const isFileJ = e.currentTarget.closest('.card').querySelector('h5').textContent.includes('D (');
        const fileType = isFileJ ? 'j' : 'jMinus1';
        uploadFile(files[0], fileType);
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
        
        // NOUVEAU: Ajouter bouton de nettoyage si pas déjà présent
        if (!document.getElementById('cleanup-btn')) {
            const cleanupBtn = document.createElement('button');
            cleanupBtn.id = 'cleanup-btn';
            cleanupBtn.className = 'btn btn-outline-warning btn-sm ms-3';
            cleanupBtn.innerHTML = '<i class="fas fa-trash"></i> Clean Memory';
            cleanupBtn.onclick = cleanupMemory;
            analyzeBtn.parentNode.appendChild(cleanupBtn);
        }
        
        showNotification('Both files are loaded! You can start the analysis.', 'success');
    } else {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = 'BEGIN DAILY LCR ANALYSIS';
        analyzeBtn.classList.remove('pulse');
        
        // Supprimer le bouton de nettoyage si présent
        const cleanupBtn = document.getElementById('cleanup-btn');
        if (cleanupBtn) {
            cleanupBtn.remove();
        }
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
        
        // Section avec les deux tableaux côte à côte (BUFFER et CONSUMPTION)
        html += '<div class="analysis-section fade-in-up">';
        html += '<div class="row">';
        
        // Tableau BUFFER (côté gauche)
        if (analysisResults.buffer) {
            html += '<div class="col-lg-6">';
            html += generateBufferSection(analysisResults.buffer);
            html += '</div>';
        }
        
        // Tableau CONSUMPTION (côté droit)
        if (analysisResults.consumption) {
            html += '<div class="col-lg-6">';
            html += generateConsumptionSection(analysisResults.consumption);
            html += '</div>';
        }
        
        html += '</div>';
        html += '</div>';
        
        // Tableau RESOURCES en pleine largeur
        if (analysisResults.resources) {
            html += '<div class="analysis-section fade-in-up">';
            html += '<div class="row">';
            html += '<div class="col-12">';
            html += generateResourcesSection(analysisResults.resources);
            html += '</div>';
            html += '</div>';
            html += '</div>';
        }

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
 * Génère la section BUFFER
 */
function generateBufferSection(bufferData) {
    if (bufferData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur BUFFER</h5>
                <p>${bufferData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${bufferData.title}</h3>
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
 * Génère le HTML du tableau BUFFER
 */
function generateBufferTableHTML(bufferData) {
    if (!bufferData.j || !bufferData.jMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau BUFFER</div>';
    }
    
    const dataJ = bufferData.j;
    const dataJ1 = bufferData.jMinus1;
    
    // Créer un mapping pour les variations
    const variationsMap = new Map();
    
    // Calculer les variations
    dataJ.forEach(itemJ => {
        const key = `${itemJ.section}_${itemJ.client}`;
        const itemJ1 = dataJ1.find(item => item.section === itemJ.section && item.client === itemJ.client);
        const valueJ1 = itemJ1 ? itemJ1.total : 0;
        const variation = itemJ.total - valueJ1;
        
        variationsMap.set(key, {
            j: itemJ.total,
            j1: valueJ1,
            variation: variation
        });
    });
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th class="align-middle">Hierarchy</th>
                    <th class="text-center header-j">D (Today)<br><small>LCR Assiette Pondérée (Bn €)</small></th>
                    <th class="text-center header-variation">Variation<br><small>Abs. Value</small></th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Organiser les données par section
    const sectionGroups = {};
    dataJ.forEach(item => {
        if (!sectionGroups[item.section]) {
            sectionGroups[item.section] = [];
        }
        sectionGroups[item.section].push(item);
    });
    
    // Générer les lignes avec hiérarchie
    Object.keys(sectionGroups).forEach(section => {
        const items = sectionGroups[section];
        
        if (section === "1.1- Cash") {
            // Pour 1.1- Cash, d'abord la ligne de section
            html += `<tr class="section-header">`;
            html += `<td class="fw-bold text-primary">${section}</td>`;
            html += `<td colspan="2" class="text-muted text-center"><em>Détail ci-dessous</em></td>`;
            html += '</tr>';
            
            // Puis les détails avec indentation
            items.forEach(item => {
                const key = `${item.section}_${item.client}`;
                const varData = variationsMap.get(key);
                const absVariation = Math.abs(varData.variation);
                const isPositive = varData.variation >= 0;
                
                html += `<tr class="detail-row">`;
                html += `<td class="ps-4">├─ ${item.client}</td>`;
                html += `<td class="text-end numeric-value">${item.total.toFixed(3)}</td>`;
                html += `<td class="text-end numeric-value">
                            ${absVariation.toFixed(3)}
                            <span class="variation-indicator ${isPositive ? 'positive' : 'negative'}">
                                ${isPositive ? '▲' : '▼'}
                            </span>
                         </td>`;
                html += '</tr>';
            });
        } else {
            // Pour les autres sections, juste la ligne totale
            const item = items[0]; // Il n'y a qu'un élément "TOTAL" pour ces sections
            const key = `${item.section}_${item.client}`;
            const varData = variationsMap.get(key);
            const absVariation = Math.abs(varData.variation);
            const isPositive = varData.variation >= 0;
            
            html += `<tr class="total-row">`;
            html += `<td class="fw-bold">${section}</td>`;
            html += `<td class="text-end numeric-value">${item.total.toFixed(3)}</td>`;
            html += `<td class="text-end numeric-value">
                        ${absVariation.toFixed(3)}
                        <span class="variation-indicator ${isPositive ? 'positive' : 'negative'}">
                            ${isPositive ? '▲' : '▼'}
                        </span>
                     </td>`;
            html += '</tr>';
        }
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau CONSUMPTION
 */
function generateConsumptionTableHTML(consumptionData) {
    if (!consumptionData.j || !consumptionData.jMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau CONSUMPTION</div>';
    }
    
    const dataJ = consumptionData.j;
    const dataJ1 = consumptionData.jMinus1;
    
    // Créer un mapping pour les variations
    const variationsMap = new Map();
    
    // Calculer les variations
    dataJ.forEach(itemJ => {
        const itemJ1 = dataJ1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueJ1 = itemJ1 ? itemJ1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const variation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueJ1;
        
        variationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            j1: valueJ1,
            variation: variation
        });
    });
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">LCR ECO Groupe Métiers</th>
                    <th class="text-center header-j">D (Today)</th>
                    <th class="text-center header-variation">Variation</th>
                </tr>
                <tr>
                    <th class="text-center header-j">LCR ECO Impact (Bn €)</th>
                    <th class="text-center header-variation">Abs. Value</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Générer les lignes
    dataJ.forEach(item => {
        const varData = variationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        const absVariation = Math.abs(varData.variation);
        const isPositive = varData.variation >= 0;
        
        html += '<tr>';
        html += `<td class="fw-bold">${item.LCR_ECO_GROUPE_METIERS}</td>`;
        html += `<td class="text-end numeric-value">${item.LCR_ECO_IMPACT_LCR_Bn.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">
                    ${absVariation.toFixed(3)}
                    <span class="variation-indicator ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += '</tr>';
    });
    
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
 * Génère le HTML du tableau RESOURCES
 */
function generateResourcesTableHTML(resourcesData) {
    if (!resourcesData.j || !resourcesData.jMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau RESOURCES</div>';
    }
    
    const dataJ = resourcesData.j;
    const dataJ1 = resourcesData.jMinus1;
    
    // Créer un mapping pour les variations
    const variationsMap = new Map();
    
    // Calculer les variations
    dataJ.forEach(itemJ => {
        const itemJ1 = dataJ1.find(item => item.LCR_ECO_GROUPE_METIERS === itemJ.LCR_ECO_GROUPE_METIERS);
        const valueJ1 = itemJ1 ? itemJ1.LCR_ECO_IMPACT_LCR_Bn : 0;
        const variation = itemJ.LCR_ECO_IMPACT_LCR_Bn - valueJ1;
        
        variationsMap.set(itemJ.LCR_ECO_GROUPE_METIERS, {
            j: itemJ.LCR_ECO_IMPACT_LCR_Bn,
            j1: valueJ1,
            variation: variation
        });
    });
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">LCR ECO Groupe Métiers</th>
                    <th class="text-center header-j">D (Today)</th>
                    <th class="text-center header-variation">Variation</th>
                </tr>
                <tr>
                    <th class="text-center header-j">LCR ECO Impact (Bn €)</th>
                    <th class="text-center header-variation">Abs. Value</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Générer les lignes
    dataJ.forEach(item => {
        const varData = variationsMap.get(item.LCR_ECO_GROUPE_METIERS);
        const absVariation = Math.abs(varData.variation);
        const isPositive = varData.variation >= 0;
        
        html += '<tr>';
        html += `<td class="fw-bold">${item.LCR_ECO_GROUPE_METIERS}</td>`;
        html += `<td class="text-end numeric-value">${item.LCR_ECO_IMPACT_LCR_Bn.toFixed(3)}</td>`;
        html += `<td class="text-end numeric-value">
                    ${absVariation.toFixed(3)}
                    <span class="variation-indicator ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '▲' : '▼'}
                    </span>
                 </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère la section CAPPAGE
 */
function generateCappageSection(cappageData) {
    if (cappageData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur CAPPAGE</h5>
                <p>${cappageData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${cappageData.title}</h3>
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
 * Génère le HTML du tableau CAPPAGE avec structure pivot
 */
function generateCappageTableHTML(cappageData) {
    if (!cappageData.j || !cappageData.jMinus1) {
        return '<div class="alert alert-warning">Données insuffisantes pour le tableau CAPPAGE</div>';
    }
    
    const dataJ = cappageData.j;
    
    if (!dataJ.data || dataJ.data.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée CAPPAGE disponible</div>';
    }
    
    const dates = dataJ.dates || [];
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">SI Remettant</th>
                    <th rowspan="2" class="align-middle">Commentaire</th>
    `;
    
    // En-têtes des dates
    dates.forEach(date => {
        html += `<th class="text-center header-j">${date}</th>`;
    });
    
    html += `
                </tr>
                <tr>
    `;
    
    // Sous-en-têtes pour les dates
    dates.forEach(() => {
        html += `<th class="text-center header-j">LCR Assiette Pondérée (Bn €)</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Générer les lignes
    dataJ.data.forEach(item => {
        const rowClass = item.is_detail ? '' : 'total-row';
        
        html += `<tr class="${rowClass}">`;
        html += `<td class="fw-bold">${item.si_remettant}</td>`;
        html += `<td>${item.commentaire}</td>`;
        
        // Valeurs pour chaque date
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            html += `<td class="text-end numeric-value">${value.toFixed(3)}</td>`;
        });
        
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère la section BUFFER & NCO (deux tableaux empilés)
 */
function generateBufferNcoSection(bufferNcoData) {
    if (bufferNcoData.error) {
        return `
            <div class="alert alert-danger">
                <h5>Erreur BUFFER & NCO</h5>
                <p>${bufferNcoData.error}</p>
            </div>
        `;
    }
    
    let html = `
        <div class="card border-0">
            <div class="card-header no-background">
                <h3 style="color: #76279b;" class="mb-1">${bufferNcoData.title}</h3>
            </div>
            <div class="card-body p-0">
                <!-- Tableau BUFFER -->
                <h5 class="text-primary mb-3 px-3 pt-3">1. BUFFER (LCR_Catégorie = "1- Buffer")</h5>
                <div class="table-container mb-4">
                    ${generateBufferNcoBufferTableHTML(bufferNcoData.data)}
                </div>
                
                <!-- Tableau NCO -->
                <h5 class="text-primary mb-3 px-3">2. NCO (All Categories)</h5>
                <div class="table-container">
                    ${generateBufferNcoNcoTableHTML(bufferNcoData.data)}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Génère le HTML du tableau BUFFER (premier tableau)
 */
function generateBufferNcoBufferTableHTML(bufferNcoData) {
    if (!bufferNcoData.j) {
        return '<div class="alert alert-warning">Données BUFFER insuffisantes</div>';
    }
    
    const dataJ = bufferNcoData.j;
    const bufferData = dataJ.buffer_data || [];
    const dates = dataJ.dates || [];
    
    if (bufferData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée BUFFER disponible</div>';
    }
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">Hierarchy</th>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center header-j">${date}</th>`;
    });
    
    html += `
                </tr>
                <tr>
    `;
    
    dates.forEach(() => {
        html += `<th class="text-center header-j">LCR Assiette Pondérée (Bn €)</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    // Organiser par section
    const sectionGroups = {};
    bufferData.forEach(item => {
        if (!sectionGroups[item.lcr_template_section]) {
            sectionGroups[item.lcr_template_section] = [];
        }
        sectionGroups[item.lcr_template_section].push(item);
    });
    
    // Générer avec hiérarchie
    Object.keys(sectionGroups).forEach(section => {
        const items = sectionGroups[section];
        
        // Ligne d'en-tête de section
        html += `<tr class="section-header">`;
        html += `<td class="fw-bold text-primary">${section}</td>`;
        dates.forEach(() => {
            html += `<td class="text-muted text-center"><em>─</em></td>`;
        });
        html += '</tr>';
        
        // Lignes de détail avec indentation
        items.forEach(item => {
            html += `<tr class="detail-row">`;
            html += `<td class="ps-4">├─ ${item.libelle_client}</td>`;
            
            dates.forEach(date => {
                const value = item.dates[date] || 0;
                html += `<td class="text-end numeric-value">${value.toFixed(3)}</td>`;
            });
            
            html += '</tr>';
        });
    });
    
    html += '</tbody></table>';
    return html;
}

/**
 * Génère le HTML du tableau NCO (deuxième tableau)
 */
function generateBufferNcoNcoTableHTML(bufferNcoData) {
    if (!bufferNcoData.j) {
        return '<div class="alert alert-warning">Données NCO insuffisantes</div>';
    }
    
    const dataJ = bufferNcoData.j;
    const ncoData = dataJ.nco_data || [];
    const dates = dataJ.dates || [];
    
    if (ncoData.length === 0) {
        return '<div class="alert alert-warning">Aucune donnée NCO disponible</div>';
    }
    
    let html = `
        <table class="table table-bordered new-table">
            <thead>
                <tr>
                    <th rowspan="2" class="align-middle">LCR Catégorie</th>
    `;
    
    dates.forEach(date => {
        html += `<th class="text-center header-j">${date}</th>`;
    });
    
    html += `
                </tr>
                <tr>
    `;
    
    dates.forEach(() => {
        html += `<th class="text-center header-j">LCR Assiette Pondérée (Bn €)</th>`;
    });
    
    html += `
                </tr>
            </thead>
            <tbody>
    `;
    
    ncoData.forEach(item => {
        html += '<tr>';
        html += `<td class="fw-bold">${item.lcr_categorie}</td>`;
        
        dates.forEach(date => {
            const value = item.dates[date] || 0;
            html += `<td class="text-end numeric-value">${value.toFixed(3)}</td>`;
        });
        
        html += '</tr>';
    });
    
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
        addChatMessage('assistant', 'Hello! I can help you analyze the LCR data that was just processed. You can ask me questions about the Balance Sheet variations, Consumption trends, or upload additional documents for context.');
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




