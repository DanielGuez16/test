# Explication complète du projet Steering ALM Metrics

## Vue d'ensemble du projet

Ce projet est une application web qui analyse des fichiers Excel contenant des données financières LCR (Liquidity Coverage Ratio). Il compare deux fichiers : un de "aujourd'hui" (J) et un d'"hier" (J-1) pour créer des analyses Balance Sheet et Consumption.

## Architecture du projet

```
projet/
├── run.py                 # Serveur FastAPI principal
├── templates/
│   └── index.html        # Interface utilisateur
├── static/
│   └── js/
│       └── main.js       # JavaScript frontend
└── data/                 # Stockage des fichiers uploadés
```

## 1. FICHIER run.py - LE SERVEUR BACKEND

### Imports et configuration

```python
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import uvicorn
import uuid
import logging
from pathlib import Path
from datetime import datetime
```

**Explication :**
- **FastAPI** : Framework web moderne pour créer des APIs REST
- **UploadFile, File, Form** : Pour gérer les uploads de fichiers
- **HTMLResponse** : Pour retourner du HTML
- **CORSMiddleware** : Permet les requêtes cross-origin (entre domaines)
- **StaticFiles** : Sert les fichiers CSS/JS
- **Jinja2Templates** : Moteur de templates pour générer du HTML dynamique
- **pandas** : Bibliothèque pour analyser les données Excel
- **uvicorn** : Serveur ASGI pour exécuter FastAPI
- **uuid** : Génère des identifiants uniques pour les fichiers
- **logging** : Système de logs pour débugger
- **pathlib** : Manipulation moderne des chemins de fichiers
- **datetime** : Gestion des dates et heures

### Configuration de l'application

```python
# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(title="Steering ALM Metrics", version="2.0.0")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Explication :**
- **logging** : Configure les messages de débogage qui apparaissent dans la console
- **FastAPI()** : Crée l'application web avec un titre et une version
- **CORSMiddleware** : Autorise toutes les requêtes externes (nécessaire pour les uploads)

### Création des dossiers

```python
# Création des dossiers requis
required_dirs = ["data", "templates", "static", "static/js", "static/css"]
for directory in required_dirs:
    Path(directory).mkdir(exist_ok=True)
```

**Explication :**
- Crée automatiquement les dossiers nécessaires au projet
- `exist_ok=True` évite les erreurs si le dossier existe déjà

### Configuration des fichiers statiques

```python
# Configuration des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
```

**Explication :**
- **mount("/static")** : Rend accessible les fichiers CSS/JS via l'URL /static/
- **Jinja2Templates** : Configure le moteur de templates pour générer les pages HTML

### Variable de session

```python
# Variables globales pour la session (en production: utiliser une base de données)
file_session = {"files": {}}
```

**Explication :**
- Stocke temporairement les informations des fichiers uploadés
- En production, ceci devrait être dans une vraie base de données

## ENDPOINTS (ROUTES) DE L'API

### 1. Route principale "/"

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Page d'accueil de l'application
    
    Utilise le template Jinja2 pour séparer la présentation
    de la logique métier.
    """
    try:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": "Steering ALM Metrics",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erreur chargement template: {e}")
        # Fallback en cas d'erreur de template
        return HTMLResponse(content="""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1>Steering ALM Metrics</h1>
                    <p style="color: red;">Erreur de chargement du template</p>
                    <p>Vérifiez que le fichier templates/index.html existe</p>
                </body>
            </html>
        """)
```

**Explication :**
- **@app.get("/")** : Décore la fonction pour répondre aux requêtes GET sur "/"
- **async def** : Fonction asynchrone (peut traiter plusieurs requêtes simultanément)
- **templates.TemplateResponse** : Renvoie le fichier HTML en passant des variables
- Le **try/except** gère les erreurs si le template n'existe pas
- **HTMLResponse** : Retourne du HTML brut en cas d'erreur

### 2. Route de vérification "/health"

```python
@app.get("/health")
async def health_check():
    """Endpoint de vérification de l'état de l'application"""
    return {
        "status": "healthy",
        "service": "steering-alm-metrics",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_files": len(file_session.get("files", {})),
        "templates_available": Path("templates/index.html").exists(),
        "static_available": Path("static/js/main.js").exists()
    }
```

**Explication :**
- Retourne un JSON avec l'état de santé de l'application
- Vérifie si les fichiers essentiels existent
- Compte le nombre de fichiers en session
- Utile pour le monitoring en production

### 3. Route d'upload "/api/upload"

```python
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), file_type: str = Form(...)):
    """
    Endpoint d'upload des fichiers Excel
    
    Args:
        file: Fichier Excel uploadé
        file_type: Type de fichier ('j' ou 'jMinus1')
    
    Returns:
        Réponse JSON avec les informations du fichier traité
    """
```

**Explication :**
- **@app.post** : Répond aux requêtes POST (avec données)
- **UploadFile = File(...)** : Paramètre pour recevoir un fichier
- **file_type: str = Form(...)** : Paramètre de formulaire obligatoire
- **async def** : Traitement asynchrone des uploads

#### Validation du fichier

```python
# Validation du fichier
if not file.filename:
    raise HTTPException(status_code=400, detail="Nom de fichier manquant")

if not file.filename.lower().endswith(('.xlsx', '.xls')):
    raise HTTPException(
        status_code=400, 
        detail="Format non supporté. Seuls les fichiers Excel (.xlsx, .xls) sont acceptés."
    )
```

**Explication :**
- Vérifie que le fichier a un nom
- Vérifie que l'extension est Excel (.xlsx ou .xls)
- **HTTPException** : Retourne une erreur HTTP avec un message

#### Sauvegarde du fichier

```python
# Lecture et sauvegarde du fichier
contents = await file.read()
unique_filename = f"{file_type}_{uuid.uuid4().hex[:8]}_{file.filename}"
file_path = Path("data") / unique_filename

with open(file_path, "wb") as f:
    f.write(contents)
```

**Explication :**
- **await file.read()** : Lit le contenu du fichier de manière asynchrone
- **uuid.uuid4().hex[:8]** : Génère un identifiant unique de 8 caractères
- **Path("data") / unique_filename** : Crée le chemin complet du fichier
- **"wb"** : Ouvre le fichier en mode écriture binaire

#### Validation Excel

```python
# Validation et analyse préliminaire du fichier Excel
try:
    df = pd.read_excel(file_path, engine='openpyxl')
    df.columns = df.columns.astype(str).str.strip()
    
    # Vérification des colonnes requises
    required_columns = ["Top Conso", "Réaffectation", "Groupe De Produit", "Nominal Value"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.warning(f"⚠️ Colonnes manquantes dans {file.filename}: {missing_columns}")
    
    logger.info(f"✅ Excel validé: {len(df)} lignes, {len(df.columns)} colonnes")
    
except Exception as e:
    logger.error(f"❌ Erreur lecture Excel: {e}")
    # Supprimer le fichier en cas d'erreur
    file_path.unlink(missing_ok=True)
    raise HTTPException(
        status_code=422, 
        detail=f"Fichier Excel invalide ou corrompu: {str(e)}"
    )
```

**Explication :**
- **pd.read_excel()** : Lit le fichier Excel avec pandas
- **engine='openpyxl'** : Moteur pour lire les fichiers .xlsx
- **df.columns.astype(str).str.strip()** : Nettoie les noms de colonnes
- Vérifie la présence des colonnes obligatoires
- **file_path.unlink()** : Supprime le fichier en cas d'erreur
- **status_code=422** : Code d'erreur pour "entité non traitable"

#### Stockage des métadonnées

```python
# Stockage des informations du fichier
file_session["files"][file_type] = {
    "filename": unique_filename,
    "original_name": file.filename,
    "rows": len(df),
    "columns": len(df.columns),
    "upload_time": datetime.now().isoformat(),
    "missing_columns": missing_columns
}
```

**Explication :**
- Sauvegarde les informations du fichier dans la session
- **datetime.now().isoformat()** : Timestamp au format ISO
- Stocke le nom original et le nom unique
- Compte les lignes et colonnes

### 4. Route d'analyse "/api/analyze"

```python
@app.post("/api/analyze")
async def analyze_files():
    """
    Endpoint d'analyse des fichiers LCR - Version complète avec Balance Sheet et Consumption
    """
```

#### Vérification des fichiers

```python
# Vérification de la présence des deux fichiers
if len(file_session.get("files", {})) < 2:
    raise HTTPException(
        status_code=400, 
        detail="Les deux fichiers (J et J-1) sont requis pour l'analyse"
    )

if "j" not in file_session["files"] or "jMinus1" not in file_session["files"]:
    raise HTTPException(
        status_code=400,
        detail="Fichiers manquants. Veuillez uploader le fichier J et le fichier J-1"
    )
```

**Explication :**
- Vérifie qu'on a bien 2 fichiers
- Vérifie qu'on a spécifiquement les types "j" et "jMinus1"
- Retourne une erreur 400 (Bad Request) sinon

#### Chargement des données

```python
# Chargement des fichiers
dataframes = {}
for file_type, file_info in file_session["files"].items():
    file_path = Path("data") / file_info["filename"]
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fichier {file_type} non trouvé sur le serveur"
        )
    
    df = pd.read_excel(file_path, engine='openpyxl')
    df.columns = df.columns.astype(str).str.strip()
    dataframes[file_type] = df
    
    logger.info(f"📊 {file_type}: {len(df)} lignes chargées")
```

**Explication :**
- Boucle sur chaque fichier de la session
- Vérifie que le fichier existe physiquement
- Charge le fichier Excel dans un DataFrame pandas
- Stocke tous les DataFrames dans un dictionnaire

## FONCTIONS D'ANALYSE

### Fonction create_balance_sheet_pivot_table()

```python
def create_balance_sheet_pivot_table(dataframes):
    """
    Crée le tableau croisé dynamique Balance Sheet
    
    Args:
        dataframes: Dict contenant les DataFrames 'j' et 'jMinus1'
    
    Returns:
        Dict contenant les résultats de l'analyse
    """
```

#### Filtrage des données

```python
# Filtrage des données
df_filtered = df[df["Top Conso"] == "O"].copy()
logger.info(f"📋 Après filtrage Top Conso='O': {len(df_filtered)} lignes")

if len(df_filtered) == 0:
    logger.warning(f"⚠️ Aucune donnée avec Top Conso='O' pour {file_type}")
    continue
```

**Explication :**
- **df["Top Conso"] == "O"** : Filtre les lignes où la colonne vaut "O"
- **.copy()** : Crée une copie pour éviter les avertissements pandas
- Vérifie qu'il reste des données après filtrage

#### Préparation des colonnes

```python
# Préparation des colonnes
df_filtered["Nominal Value"] = pd.to_numeric(
    df_filtered["Nominal Value"], errors='coerce'
).fillna(0)

df_filtered["Réaffectation"] = df_filtered["Réaffectation"].astype(str).str.upper().str.strip()
```

**Explication :**
- **pd.to_numeric(errors='coerce')** : Convertit en nombre, met NaN si impossible
- **.fillna(0)** : Remplace les valeurs manquantes par 0
- **.str.upper().str.strip()** : Met en majuscules et supprime les espaces

#### Création du tableau croisé

```python
# Création du tableau croisé dynamique
pivot_table = pd.pivot_table(
    df_filtered,
    index="Groupe De Produit",
    columns="Réaffectation",
    values="Nominal Value",
    aggfunc="sum",
    fill_value=0,
    margins=True,
    margins_name="TOTAL"
)
```

**Explication :**
- **index** : Lignes du tableau (Groupe De Produit)
- **columns** : Colonnes du tableau (Réaffectation)
- **values** : Valeurs à agréger (Nominal Value)
- **aggfunc="sum"** : Fonction d'agrégation (somme)
- **fill_value=0** : Remplace les cellules vides par 0
- **margins=True** : Ajoute les totaux
- **margins_name="TOTAL"** : Nom de la ligne/colonne de total

#### Conversion en milliards

```python
# Conversion en milliards d'euros
pivot_table = (pivot_table / 1_000_000_000).round(2)
```

**Explication :**
- Divise par 1 milliard pour convertir en milliards
- **.round(2)** : Arrondit à 2 décimales

### Fonction create_consumption_analysis()

Cette fonction suit la même logique mais analyse les données Consumption :

1. **Filtrage** : Top Conso = "O"
2. **Groupement** : Par "LCR_ECO_GROUPE_METIERS" et "Métier"
3. **Mesure** : "LCR_ECO_IMPACT_LCR"
4. **Conversion** : En milliards d'euros

### Fonctions de génération HTML

#### generate_pivot_table_html()

```python
def generate_pivot_table_html(pivot_tables):
    """
    Génère le HTML du tableau croisé dynamique combiné
    
    Args:
        pivot_tables: Dict des tables pivot par type de fichier
    
    Returns:
        String HTML du tableau formaté
    """
```

**Explication :**
- Prend les deux tableaux pivot (J et J-1)
- Génère un tableau HTML avec colonnes comparatives
- Calcule les variations (J - J-1)
- Applique des styles CSS pour les couleurs

#### Structure du tableau généré

```html
<table class="table table-bordered pivot-table">
    <thead>
        <tr>
            <th rowspan="2">Groupe De Produit</th>
            <th colspan="2">J-1 (Hier)</th>
            <th colspan="2">J (Aujourd'hui)</th>
            <th colspan="2">Variation (J - J-1)</th>
        </tr>
        <tr>
            <th>ACTIF</th>
            <th>PASSIF</th>
            <th>ACTIF</th>
            <th>PASSIF</th>
            <th>ACTIF</th>
            <th>PASSIF</th>
        </tr>
    </thead>
    <tbody>
        <!-- Données générées dynamiquement -->
    </tbody>
</table>
```

## 2. FICHIER templates/index.html - L'INTERFACE UTILISATEUR

### Structure HTML

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steering ALM Metrics - Analyse LCR</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
```

**Explication :**
- **DOCTYPE html** : Document HTML5
- **lang="fr"** : Langue française
- **meta viewport** : Responsive design pour mobile
- **Bootstrap** : Framework CSS pour un design moderne

### Styles CSS personnalisés

#### Variables CSS

```css
:root {
    --natixis-blue: #003366;
    --natixis-light-blue: #0066cc;
    --natixis-green: #00a651;
    --natixis-orange: #ff6600;
    --natixis-gray: #f5f5f5;
    --success-green: #28a745;
    --danger-red: #dc3545;
}
```

**Explication :**
- **:root** : Variables CSS globales
- Définit la palette de couleurs du projet
- Utilisables avec **var(--nom-variable)**

#### Styles du body

```css
body { 
    background: linear-gradient(135deg, var(--natixis-blue) 0%, var(--natixis-light-blue) 100%); 
    min-height: 100vh; 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
```

**Explication :**
- **linear-gradient** : Dégradé de couleur en arrière-plan
- **135deg** : Angle du dégradé
- **min-height: 100vh** : Hauteur minimum = hauteur de l'écran
- **font-family** : Police moderne

### Zones d'upload

```css
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
```

**Explication :**
- **border: 3px dashed** : Bordure pointillée
- **cursor: pointer** : Curseur main au survol
- **transition** : Animation fluide des changements
- **cubic-bezier** : Courbe d'animation personnalisée

### Structure de la page

```html
<!-- Navigation -->
<div class="navbar-custom">
    <div class="container d-flex justify-content-between align-items-center py-3">
        <h3 class="mb-0 text-primary fw-bold">
            📊 Steering ALM Metrics
        </h3>
        <span class="badge bg-primary">Analyse LCR</span>
    </div>
</div>

<!-- Contenu principal -->
<div class="container">
    <div class="main-container p-4">
        <!-- Titre -->
        <!-- Section Upload -->
        <!-- Bouton d'analyse -->
        <!-- Section Résultats -->
    </div>
</div>
```

**Explication :**
- **container** : Conteneur Bootstrap avec marges automatiques
- **d-flex** : Flexbox Bootstrap
- **justify-content-between** : Espacement entre éléments
- **py-3** : Padding vertical niveau 3

## 3. FICHIER static/js/main.js - LA LOGIQUE FRONTEND

### Variables globales

```javascript
// Variables globales
let filesReady = { j: false, j1: false };
```

**Explication :**
- Objet pour tracker quels fichiers sont prêts
- **j** : fichier du jour
- **j1** : fichier de J-1

### Initialisation

```javascript
// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Interface ALM initialisée');
    initializeFileUploads();
    initializeAnalyzeButton();
});
```

**Explication :**
- **DOMContentLoaded** : Événement déclenché quand la page est chargée
- Appelle les fonctions d'initialisation
- **console.log** : Message de débogage dans la console

### Fonction initializeFileUploads()

```javascript
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
```

**Explication :**
- **getElementById** : Sélectionne un élément par son ID
- **addEventListener('change')** : Écoute les changements de fichier
- **this.files[0]** : Premier fichier sélectionné
- Appelle **uploadFile()** avec le fichier et son type

### Fonction uploadFile()

```javascript
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
                        <strong>Upload en cours...</strong><br>
                        <small>${file.name} (${formatFileSize(file.size)})</small>
                    </div>
                </div>
            </div>
        `;
```

**Explication :**
- **async function** : Fonction asynchrone
- **statusDiv** : Élément HTML pour afficher le statut
- **innerHTML** : Modifie le contenu HTML
- **Template literals** (backticks) : Chaînes multi-lignes avec variables

#### Préparation de la requête

```javascript
// Préparation de la requête
const formData = new FormData();
formData.append('file', file);
formData.append('file_type', type);

// Envoi à l'API
const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
});
```

**Explication :**
- **FormData** : Objet pour les données de formulaire
- **append()** : Ajoute des champs au formulaire
- **fetch()** : Envoie une requête HTTP
- **await** : Attend la réponse de manière asynchrone

#### Traitement de la réponse

```javascript
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
                        📊 ${result.rows?.toLocaleString()} lignes • 
                        ${result.columns} colonnes • 
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
```

**Explication :**
- **response.ok** : Vérifie si la requête a réussi (status 200-299)
- **response.json()** : Parse la réponse JSON
- **result.rows?.toLocaleString()** : Formate le nombre avec séparateurs (optionnel)
- **filesReady[...]** : Met à jour l'état du fichier
- **checkAnalyzeButtonState()** : Vérifie si on peut analyser

### Fonction checkAnalyzeButtonState()

```javascript
function checkAnalyzeButtonState() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (filesReady.j && filesReady.j1) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '🎯 PRÊT - GÉNÉRER LE TCD';
        analyzeBtn.classList.add('pulse');
        
        // Notification visuelle
        showNotification('Les deux fichiers sont prêts ! Vous pouvez lancer l\'analyse.', 'success');
    } else {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '🚀 GÉNÉRER LE TCD BALANCE SHEET';
        analyzeBtn.classList.remove('pulse');
    }
}
```

**Explication :**
- **&&** : Opérateur ET logique
- **disabled** : Active/désactive le bouton
- **classList.add/remove** : Ajoute/supprime des classes CSS
- **showNotification()** : Affiche une notification

### Fonction analyze()

```javascript
async function analyze() {
    console.log('🔍 Lancement de l\'analyse TCD');
    
    // Affichage du statut d'analyse
    document.getElementById('results').innerHTML = `
        <div class="analysis-section fade-in-up">
            <div class="card border-0">
                <div class="card-body text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
                    <h4 class="text-primary">Génération des analyses en cours...</h4>
                    <p class="text-muted">
                        Balance Sheet + Consumption<br>
                        <small>Filtrage ACTIF/PASSIF • LCR par métier • Top Conso = "O"</small>
                    </p>
                    <div class="progress mt-3" style="height: 6px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             style="width: 100%"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
```

**Explication :**
- Affiche un écran de chargement avec spinner
- **progress-bar-striped progress-bar-animated** : Barre de progression animée
- Donne un feedback visuel à l'utilisateur

#### Appel à l'API d'analyse

```javascript
try {
    const response = await fetch('/api/analyze', { method: 'POST' });
    
    if (response.ok) {
        const result = await response.json();
        console.log('📊 Résultats de l\'analyse:', result);
        
        if (result.success) {
            displayCompleteResults(result.results);
            showNotification('Analyses Balance Sheet et Consumption terminées avec succès !', 'success');
        } else {
            throw new Error(result.message || 'Erreur dans l\'analyse');
        }
    } else {
        const errorText = await response.text();
        throw new Error(`Erreur serveur ${response.status}: ${errorText}`);
    }
} catch (error) {
    console.error('❌ Erreur analyse:', error);
    // Gestion d'erreur...
}
```

**Explication :**
- **try/catch** : Gestion des erreurs
- Appelle l'endpoint `/api/analyze`
- **displayCompleteResults()** : Affiche les résultats
- **response.text()** : Récupère la réponse en texte brut

### Fonction displayCompleteResults()

```javascript
function displayCompleteResults(analysisResults) {
    if (!analysisResults) {
        document.getElementById('results').innerHTML = '<div class="alert alert-danger">Aucun résultat d\'analyse disponible</div>';
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
    
    document.getElementById('results').innerHTML = html;
    
    // Scroll vers les résultats
    setTimeout(() => {
        const firstSection = document.querySelector('.analysis-section');
        if (firstSection) {
            firstSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }, 500);
}
```

**Explication :**
- Vérifie si on a des résultats
- Génère le HTML pour Balance Sheet et Consumption
- **+=** : Concatène les chaînes HTML
- **setTimeout()** : Délai avant de scroller
- **scrollIntoView()** : Fait défiler la page vers l'élément

### Fonction generateBalanceSheetSection()

```javascript
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
                <div class="card-header bg-primary text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1">📊 ${balanceSheetData.title || 'Balance Sheet Analysis'}</h3>
                            <small>Analyse ACTIF/PASSIF par Groupe de Produit</small>
                        </div>
                        <span class="badge bg-light text-primary">Balance Sheet</span>
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
```

**Explication :**
- **||** : Opérateur OU logique (valeur par défaut)
- **Template literals** : Utilise ${} pour insérer des variables
- **card-header bg-primary** : En-tête de carte Bootstrap avec couleur
- **p-0** : Padding zéro Bootstrap
- Structure modulaire pour chaque section

#### Génération des cartes de métriques

```javascript
// Variations Balance Sheet
if (balanceSheetData.variations) {
    html += `
        <div class="analysis-section fade-in-up">
            <h4 class="text-center mb-4">📈 Variations Balance Sheet (J vs J-1)</h4>
            <div class="row">
    `;
    
    const variations = balanceSheetData.variations;
    
    // Carte ACTIF
    if (variations.ACTIF) {
        const actif = variations.ACTIF;
        const isPositive = actif.variation >= 0;
        
        html += `
            <div class="col-md-6 mb-3">
                <div class="metric-card">
                    <div class="text-center">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h5 class="mb-0">💰 ACTIF</h5>
                            <span class="badge ${isPositive ? 'bg-success' : 'bg-danger'}">
                                ${isPositive ? '📈' : '📉'}
                            </span>
                        </div>
                        <div class="row text-center">
                            <div class="col-6">
                                <small class="opacity-75">J-1</small>
                                <h3>${actif.j_minus_1} Bn €</h3>
                            </div>
                            <div class="col-6">
                                <small class="opacity-75">J</small>
                                <h3>${actif.j} Bn €</h3>
                            </div>
                        </div>
                        <hr class="my-3 opacity-50">
                        <h2 class="${isPositive ? 'text-success' : 'text-danger'}">
                            ${isPositive ? '+' : ''}${actif.variation} Bn €
                        </h2>
                        <small class="opacity-75">Variation</small>
                    </div>
                </div>
            </div>
        `;
    }
```

**Explication :**
- **>=** : Opérateur "supérieur ou égal"
- **Ternary operator** : `condition ? vraie : fausse`
- **col-md-6** : Colonne Bootstrap (50% sur écrans moyens+)
- **opacity-75** : Transparence à 75%
- **text-success/text-danger** : Classes Bootstrap pour les couleurs

### Fonction generateConsumptionSection()

Cette fonction suit la même logique que Balance Sheet mais pour les données Consumption :

```javascript
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
                <div class="card-header bg-success text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h3 class="mb-1">🏢 ${consumptionData.title || 'LCR Consumption Analysis'}</h3>
                            <small>Analyse par Groupe Métiers et Métier</small>
                        </div>
                        <span class="badge bg-light text-success">Consumption</span>
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
```

**Explication :**
- **mt-5** : Marge top Bootstrap niveau 5
- **bg-success** : Couleur verte Bootstrap
- Structure identique à Balance Sheet mais avec thème vert

### Fonctions utilitaires

#### showNotification()

```javascript
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
```

**Explication :**
- **document.createElement()** : Crée un nouvel élément HTML
- **position-fixed** : Position fixe par rapport à la fenêtre
- **z-index: 9999** : Au-dessus de tous les autres éléments
- **transform: translateX()** : Translation horizontale
- **appendChild()** : Ajoute l'élément au DOM
- Animation en 3 étapes : création → affichage → suppression

#### formatFileSize()

```javascript
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
```

**Explication :**
- **Math.log()** : Logarithme naturel
- **Math.floor()** : Arrondi à l'entier inférieur
- **Math.pow(k, i)** : k puissance i
- **toFixed(2)** : 2 décimales
- **parseFloat()** : Convertit en nombre décimal

## FLOW COMPLET DE L'APPLICATION

### 1. Démarrage de l'application
```bash
python run.py
```
- Lance le serveur FastAPI sur http://localhost:8000
- Crée les dossiers nécessaires
- Configure les routes et middleware

### 2. Chargement de la page
1. L'utilisateur va sur http://localhost:8000
2. FastAPI sert `templates/index.html`
3. Le navigateur charge Bootstrap CSS et `static/js/main.js`
4. JavaScript initialise les listeners d'événements

### 3. Upload de fichiers
1. L'utilisateur clique sur une zone d'upload
2. Sélectionne un fichier Excel
3. JavaScript appelle `uploadFile()`
4. Envoi POST vers `/api/upload`
5. Python valide et sauvegarde le fichier
6. Retourne les métadonnées en JSON
7. JavaScript met à jour l'interface

### 4. Analyse des données
1. Quand les 2 fichiers sont prêts, le bouton s'active
2. L'utilisateur clique sur "ANALYSER"
3. JavaScript appelle `/api/analyze`
4. Python charge les 2 fichiers Excel
5. Crée les analyses Balance Sheet et Consumption
6. Retourne les résultats en JSON
7. JavaScript génère et affiche les tableaux HTML

### 5. Affichage des résultats
- Tableaux croisés dynamiques comparatifs
- Cartes de métriques avec variations
- Analyses textuelles automatiques
- Interface responsive et animations

## POINTS CLÉS POUR COMPRENDRE

### Architecture MVC
- **Model** : Pandas DataFrames (données)
- **View** : Templates HTML + JavaScript (présentation)
- **Controller** : FastAPI routes (logique métier)

### Technologies utilisées
- **Backend** : Python, FastAPI, Pandas
- **Frontend** : HTML, CSS, JavaScript, Bootstrap
- **Data** : Excel (.xlsx), JSON (échanges API)

### Patterns de développement
- **Async/Await** : Traitement asynchrone
- **REST API** : Communication frontend/backend
- **Template Engine** : Séparation présentation/logique
- **Responsive Design** : Adaptation mobile/desktop

### Gestion d'erreurs
- **Try/Catch** : Capture et gestion des exceptions
- **HTTP Status Codes** : Communication d'état
- **User Feedback** : Notifications et messages d'erreur
- **Logging** : Traçabilité pour le débogage

Cette architecture te permet d'ajouter facilement :
- Nouveaux types d'analyse
- Nouveaux formats de fichiers
- Nouvelles visualisations
- Système d'authentification
- Base de données persistante