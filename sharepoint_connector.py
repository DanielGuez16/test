<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steering ALM Metrics - LCR Analysis</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Styles personnalisés -->
    <style>
        :root {
            --natixis-blue: #76279b;
            --natixis-light-blue: #ab54d4;
            --natixis-very-light-blue: #D3A5E9;
            --natixis-green: #00a651;
            --natixis-orange: #ff6600;
            --natixis-gray: #f5f5f5;
            --success-green: #28a745;
            --danger-red: #dc3545;
        }

        .bg-primary {
            background-color: var(--natixis-blue) !important;
        }

        .bg-secondary {
            background-color: var(--natixis-light-blue) !important;
        }

        .bg-third {
            background-color: var(--natixis-very-light-blue) !important;
        }

        .text-primary {
            color: var(--natixis-blue) !important;
        }

        .text-black {
            color: black !important; 
        }
        
        body { 
            background: #f2f0f0; 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .main-container { 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 15px 40px rgba(0,0,0,0.3); 
            margin: 30px auto; 
            backdrop-filter: blur(10px);
        }
        
        .navbar-custom {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            margin: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .upload-area { 
            border: 3px dashed var(--natixis-light-blue); 
            padding: 2.5rem; 
            text-align: center; 
            margin: 20px 0; 
            cursor: pointer; 
            border-radius: 15px; 
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            background: linear-gradient(145deg, #ffffff, #f8f9ff);
        }
        
        .upload-area:hover { 
            background: linear-gradient(145deg, #f0f8ff, #e3f2fd);
            border-color: var(--natixis-green);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,102,204,0.15);
        }
        
        .upload-area i {
            font-size: 3rem;
            color: var(--natixis-light-blue);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        
        .upload-area:hover i {
            color: var(--natixis-green);
            transform: scale(1.1);
        }
        
        /* Styles du tableau croisé dynamique */
        .pivot-table, .consumption-table { 
            font-size: 13px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }
        
        .pivot-table th, .consumption-table th { 
            background: #bf7cde;
            color: white; 
            font-weight: 600; 
            text-align: center; 
            padding: 12px 8px; 
            border: none;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .pivot-table td, .consumption-table td { 
            padding: 8px; 
            border: 1px solid #e0e6ed; 
            vertical-align: middle;
        }
        
        .pivot-table tbody tr:hover, .consumption-table tbody tr:hover {
            background-color: rgba(0, 102, 204, 0.05);
            transition: background-color 0.2s ease;
        }
        
        /* Styles des lignes spéciales */
        .total-row { 
            background: linear-gradient(135deg, #f3dffc, #f3dffc);
            font-weight: bold; 
            border-top: 2px solid var(--natixis-light-blue);
        }
        
        .total-row td {
            font-weight: 700;
            border-top: 2px solid var(--natixis-light-blue);
        }
        
        /* Styles des variations */
        .variation-positive { 
            color: var(--success-green); 
            font-weight: bold;
            position: relative;
        }
        
        .variation-positive::before {
            content: "▲";
            margin-right: 3px;
            font-size: 0.8em;
        }
        
        .variation-negative { 
            color: var(--danger-red); 
            font-weight: bold;
            position: relative;
        }
        
        .variation-negative::before {
            content: "▼";
            margin-right: 3px;
            font-size: 0.8em;
        }
        
        /* En-têtes de colonnes spécialisés */
        .header-j-minus-1 {
            background: linear-gradient(135deg, #ab54d4, #ab54d4) !important;
        }
        
        .header-j {
            background: linear-gradient(135deg,  #bf7cde, #bf7cde) !important;
        }
        
        .header-variation {
            background: linear-gradient(135deg, #ab54d4, #ab54d4) !important;
        }
        
        /* Cartes de métriques */
        .metric-card { 
            background: #f3dffc; 
            color: black; 
            border-radius: 15px; 
            padding: 2rem; 
            margin: 15px 0; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-card h2 {
            font-size: 2.5rem;
            font-weight: 300;
            margin: 10px 0;
        }
        
        /* Boutons */
        .btn-analyze {
            background: linear-gradient(45deg, var(--natixis-light-blue), var(--natixis-light-blue)); 
            border: none; 
            color: white; 
            padding: 15px 40px; 
            font-size: 18px; 
            font-weight: 600;
            border-radius: 50px; 
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,102,204,0.3);
        }
        
        .btn-analyze:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,102,204,0.4);
            color: white;
        }
        
        .btn-analyze:disabled {
            background: #6c757d;
            transform: none;
            box-shadow: none;
        }
        
        /* Alertes et statuts */
        .alert {
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .balance-sheet-separator {
            border: none;
            height: 10px;
            background: var(--natixis-blue);
            margin: 2rem auto;
            width: 100%;
            border-radius: 2px;
        }

        .analysis-section { 
            margin: 40px 0; 
        }
        
        /* Animations */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in-up {
            animation: fadeInUp 0.6s ease forwards;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .pivot-table {
                font-size: 11px;
            }
            
            .pivot-table th,
            .pivot-table td {
                padding: 6px 4px;
            }
            
            .metric-card {
                padding: 1.5rem;
            }
        }
        
        /* Table responsive avec scroll horizontal */
        .table-container {
            max-width: 100%;
            overflow-x: auto;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        /* Styles pour les valeurs numériques */
        .numeric-value {
            font-family: 'Courier New', monospace;
            text-align: right;
        }
        
        /* Légende */
        .table-legend {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            border-left: 4px solid var(--natixis-light-blue);
        }

        .chart-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            position: relative;
            height: 350px;
        }

        .chart-container h5 {
            color: var(--natixis-blue);
            font-weight: 600;
            margin-bottom: 15px;
        }

        .chart-container canvas {
            max-height: 280px !important;
        }

        .summary-box {
            background: #f3dffc;
            color: black;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .summary-box h5 {
            color: white;
            font-weight: 600;
        }

        .navbar-logo {
            height: 40px;
            margin-right: 15px;
            transition: transform 0.3s ease;
        }

        .navbar-logo:hover {
            transform: scale(1.05);
        }

        /* Styles Chatbot */
        .chatbot-section {
            background: white;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            margin-top: 50px;
        }

        .chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e6ed;
            border-radius: 10px;
            padding: 15px;
            background: #f8f9fa;
        }

        .chat-message {
            margin-bottom: 15px;
            padding: 12px;
            border-radius: 10px;
            max-width: 80%;
            animation: fadeInUp 0.3s ease;
        }

        .chat-message.user {
            background: linear-gradient(135deg, var(--natixis-blue), var(--natixis-light-blue));
            color: white;
            margin-left: auto;
            text-align: right;
        }

        .chat-message.assistant {
            background: white;
            border: 1px solid #e0e6ed;
            margin-right: auto;
        }

        .chat-input {
            border: 2px solid var(--natixis-light-blue);
            border-radius: 25px;
            padding: 12px 20px;
            font-size: 14px;
        }

        .chat-input:focus {
            border-color: var(--natixis-blue);
            box-shadow: 0 0 0 0.2rem rgba(154, 96, 177, 0.25);
        }

        .btn-chat {
            background: var(--natixis-blue);
            border: none;
            border-radius: 50%;
            width: 45px;
            height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn-chat:hover {
            background: var(--natixis-light-blue);
        }

        .document-upload {
            border: 2px dashed var(--natixis-light-blue);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            min-height: 80px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .document-upload i {
            font-size: 2rem;
            color: var(--natixis-light-blue);
            margin-bottom: 0.5rem;
        }

        .document-upload p {
            margin: 0;
            color: #6c757d;
        }

        .document-upload.drag-over {
            border-color: var(--natixis-green) !important;
            background: rgba(0, 166, 81, 0.1) !important;
            transform: scale(1.02);
        }

        .document-upload {
            transition: all 0.3s ease;
        }

        .document-upload:hover {
            border-color: var(--natixis-green);
            background: rgba(0, 166, 81, 0.05);
        }

        .uploaded-docs {
            max-height: 100px;
            overflow-y: auto;
        }

        .doc-item {
            background: #e3f2fd;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 5px;
            font-size: 12px;
        }

        /* Ajouter dans la section <style> */
        .ai-response {
            line-height: 1.5;
        }

        .ai-response h4 {
            color: var(--natixis-blue);
            font-size: 1.1em;
            border-bottom: 2px solid var(--natixis-light-blue);
            padding-bottom: 5px;
        }

        .ai-response h5 {
            color: var(--natixis-light-blue);
            font-size: 1em;
        }

        .ai-response ul, .ai-response ol {
            padding-left: 20px;
        }

        .ai-response li {
            margin-bottom: 5px;
        }

        .ai-response code {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .ai-response p {
            margin-bottom: 10px;
        }

        .upload-area.drag-over {
            border-color: var(--natixis-green) !important;
            background: rgba(0, 166, 81, 0.1) !important;
            transform: scale(1.02);
        }

        .date-selector-container {
            background: linear-gradient(145deg, #f8f9ff, #f8f9ff);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            overflow: visible;
        }

        .date-label {
            font-weight: 600;
            color: #76279b;
            font-size: 1.1rem;
            margin-bottom: 10px;
            display: block;
        }

        .date-input-wrapper {
            position: relative;
        }

        .date-input {
            border: 2px solid #e0e6ed;
            border-radius: 15px;
            padding: 15px 50px 15px 20px;
            font-size: 1.1rem;
            font-weight: 500;
            color: #333;
            background: #fff;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .date-input:focus {
            border-color: #76279b;
            box-shadow: 0 0 0 0.2rem rgba(118, 39, 155, 0.25);
            outline: none;
        }

        .date-icon {
            position: absolute;
            right: 15px;
            color: #76279b;
            font-size: 1.2rem;
            pointer-events: none;
        }

        .date-explanation {
            background: rgba(171, 84, 212, 0.1);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-top: 1rem;
        }
        /* Load Files Button */
        .btn-load-files {
            width: 60%;
            height: 100%;
            min-height: 80px;            
            background: linear-gradient(135deg, var(--natixis-blue), var(--bleu-canard));
            border: none;
            border-radius: 90px;         
            color: white;
            font-weight: 700;
            font-size: 1rem;       
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            box-shadow: 0 6px 20px rgba(118, 39, 155, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .btn-load-files::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }

        .btn-load-files:hover::before {
            left: 100%;
        }

        .btn-load-files:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px var(--natixis-blue);
        }

        .btn-load-files:active {
            transform: translateY(-1px);
        }


        /* Forcer les styles du bouton LOAD FILES */
        .btn-load-files {
            background: linear-gradient(160deg, #76279b, #51A0A2) !important;
            color: white !important;
        }

        .btn-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-icon {
            font-size: 1.3rem;
            margin-right: 10px;
        }

        .btn-text {
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .date-input {
                padding: 12px 40px 12px 15px;
                font-size: 1rem;
            }
            
            .btn-load-files {
                height: 50px;
                font-size: 0.9rem;
                margin-top: 20px;
            }
            
            .btn-icon {
                font-size: 1.1rem;
                margin-right: 8px;
            }
        }

        /* Animation pour le card */
        .upload-section .card {
            transition: all 0.3s ease;
        }

        .upload-section .card:hover {
            transform: translateY(-5px);
        }

        .card-header.no-background {
            background: transparent !important;
            border: none !important;
            padding: 1.5rem 1.25rem 1rem 1.25rem;
        }

        .card-header.no-background h3,
        .card-header.no-background h4 {
            color: var(--natixis-blue) !important;
            font-weight: 600;
            margin: 0;
            position: relative;
            padding-left: 20px;
        }

        .card-header.no-background h3::before {
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 4px;
            height: 24px;
            background: linear-gradient(to bottom, var(--natixis-blue), var(--natixis-light-blue));
            border-radius: 2px;
        }

        .card-header.no-background .badge {
            background: #6c757d !important;
            color: white;
        }


        .upload-section .card-header.bg-gradient {
            background: linear-gradient(160deg, var(--natixis-blue), var(--bleu-canard)) !important;
            border: none !important;
            padding: 1.5rem !important;
        }

        .upload-section .card-header.bg-gradient * {
            color: white !important;
        }

        .upload-section .card-header.bg-gradient h3 {
            font-weight: 600 !important;
            margin-bottom: 0.25rem !important;
        }

        .upload-section .card-header.bg-gradient p {
            opacity: 0.9 !important;
            margin-bottom: 0 !important;
            font-size: 0.9rem !important;
        }

        .upload-section .card-header.bg-gradient i.fa-calendar-alt {
            font-size: 2rem !important;
        }

        .upload-cards .card-body {
            padding: 1.5rem;
        }

        .upload-section .card-body {
            border-radius: 0 0 20px 20px !important;  /* Arrondi seulement en bas */
        }



    </style>
</head>
<body>

    <!-- Navigation -->
    <div class="navbar-custom">
        <div class="container d-flex justify-content-between align-items-center py-3">
            <div class="d-flex align-items-center">
                <img src="/static/images/bpce_logo.png" alt="BPCE Logo" class="navbar-logo">
            </div>
            <div class="d-flex align-items-center">
                <span class="badge bg-third me-3">{{ user.full_name }}</span>
                {% if user.role == 'admin' %}
                    <button class="btn btn-outline-primary btn-sm me-2" onclick="showAdminPanel()">
                        <i class="fas fa-cogs"></i> Admin
                    </button>
                {% endif %}
                <button class="btn btn-outline-danger btn-sm me-2" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
                <span class="badge bg-primary">Steering ALM Metrics</span>
            
            </div>
        </div>
    </div>
    
    <!-- Contenu principal -->
    <div class="container">
        <div class="main-container p-4">
            <div class="text-center mb-5 fade-in-up">
                <h1 class="display-5 text-primary fw-bold mb-3">
                    Daily LCR Analysis Tool
                </h1>
            </div>
            </div>
            
            <!-- SECTION UPLOAD -->
            <div class="upload-section mb-5">
                <div class="card border-0 shadow-lg">
                    <div class="card-header bg-gradient text-white" style="background: linear-gradient(135deg, #76279b, #51A0A2);">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-calendar-alt fa-2x me-3"></i>
                            <div>
                                <h3 class="mb-1">LCR Analysis Date Selection</h3>
                                <p class="mb-0 opacity-75">Files will be loaded automatically from SharePoint</p>
                            </div>
                        </div>
                    </div>
                    <div class="card-body p-4">
                        <div class="row align-items-center">
                            <div class="col-md-10">
                                <div class="date-selector-container">
                                    <label class="date-label">
                                        Select Analysis Date
                                        <span id=""dateInfoIcon">
                                           <i class="fas fa-info-circle ms-1"></i>
                                    </label>
                                    <div class="date-input-wrapper">
                                        <input type="date" class="form-control date-input" id="analysisDate">
                                    </div>
                                    <div class="date-explanation mt-2">
                                        <small class="text-muted">
                                            <i class="fas fa-info-circle me-1"></i>
                                            Example: Select <strong>15/09/2025</strong> to load data of the previous day (J-1) 14/09/2025 and the current day (J) 15/09/2025
                                        </small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <button id="loadFilesBtn" class="btn btn-load-files">
                                    <div class="btn-content">
                                        <i class="fas fa-cloud-download-alt btn-icon"></i>
                                        <span class="btn-text">LOAD FILES</span>
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Conserver les sections de statut -->
            <div class="row upload-cards">
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">D (Today)</h5>
                            <div id="statusJ"></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">D-1 (Yesterday)</h5>
                            <div id="statusJ1"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Espace avant le bouton d'analyse -->
            <div style="margin-top: 10px;"></div>

            <!-- Bouton d'analyse -->
            <div class="text-center mb-4 fade-in-up" style="animation-delay: 0.4s;">
                <button id="analyzeBtn" class="btn btn-analyze btn-lg" onclick="analyze()" disabled>
                    <i class="fa-solid fa-chart-line me-2"></i>BEGIN DAILY LCR ANALYSIS
                </button>
            </div>
            
            <!-- Section Résultats -->
            <div id="results" class="fade-in-up" style="animation-delay: 0.6s;"></div>

            <div id="context-loading" class="text-center my-4" style="display: none;">
                <div class="card border-0" style="background: rgba(255,255,255,0.9);">
                    <div class="card-body py-4">
                        <div class="d-flex align-items-center justify-content-center">
                            <div class="spinner-border text-primary me-3" style="width: 2rem; height: 2rem;"></div>
                            <div>
                                <h5 class="mb-1 text-primary">Preparing AI context...</h5>
                                <small class="text-muted">Loading analysis data into AI assistant</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section Chatbot -->
            <div id="chatbot-section" class="chatbot-section p-4 mt-5" style="display: none;">
                <div class="card border-0">
                    <div class="card-header bg-secondary text-white">
                        <div class="d-flex justify-content-between align-items-center">
                            <h4 class="mb-0">AI Analysis Assistant</h4>
                            <div>
                                <button class="btn btn-outline-light btn-sm me-2" onclick="clearChat()">
                                    <i class="fas fa-trash"></i> Clear
                                </button>
                                <button class="btn btn-outline-light btn-sm" onclick="toggleChatbot()">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-lg-8">
                                <!-- Zone de chat -->
                                <div id="chat-container" class="chat-container mb-3"></div>
                                
                                <!-- Input de chat -->
                                <div class="d-flex gap-2">
                                    <input type="text" id="chat-input" class="form-control chat-input" 
                                        placeholder="Posez une question sur les analyses..." 
                                        onkeypress="handleChatKeyPress(event)">
                                    <button class="btn btn-chat text-white" onclick="sendMessage()">
                                        <i class="fas fa-paper-plane"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="col-lg-4">
                                <!-- Upload de documents -->
                                <h6 class="mb-3">Add Context Documents</h6>
                                <div class="document-upload mb-3" id="doc-upload-area" onclick="document.getElementById('doc-upload').click()">
                                    <i class="fas fa-file-upload"></i>
                                    <p class="mb-0">Upload PDF, TXT, DOC...</p>
                                </div>
                                <input type="file" id="doc-upload" accept=".pdf,.txt,.doc,.docx" 
                                    style="display:none" onchange="uploadDocument(this.files[0])">
                                
                                <!-- Liste des documents -->
                                <div id="uploaded-docs" class="uploaded-docs"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.5/dist/purify.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/js/all.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="/static/js/main.js"></script>

    <!-- Panel Admin (masqué par défaut) -->
    {% if user.role == 'admin' %}
    <div id="admin-panel" class="modal fade" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Administration Panel</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <ul class="nav nav-tabs mb-3">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" href="#logs-tab">Activity Logs</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#users-tab">Users</a>
                        </li>
                    </ul>
                    <div class="tab-content">
                        <div class="tab-pane active" id="logs-tab">
                            <div id="logs-container">
                                <div class="text-center">
                                    <div class="spinner-border"></div>
                                    <p>Loading logs...</p>
                                </div>
                            </div>
                        </div>
                        <div class="tab-pane" id="users-tab">
                            <div id="users-container">
                                <div class="text-center">
                                    <div class="spinner-border"></div>
                                    <p>Loading users...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endif %}

</body>
</html>
