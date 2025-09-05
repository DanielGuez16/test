#!/usr/bin/env python3
#run.py
"""
Steering ALM Metrics - Version avec Templates
============================================

Application FastAPI utilisant un système de templates Jinja2
pour séparer la logique métier de la présentation.
"""

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

# Création des dossiers requis
required_dirs = ["data", "templates", "static", "static/js", "static/css"]
for directory in required_dirs:
    Path(directory).mkdir(exist_ok=True)

# Configuration des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Variables globales pour la session (en production: utiliser une base de données)
file_session = {"files": {}}

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
    try:
        logger.info(f"📤 Upload reçu: {file.filename}, type: {file_type}")
        
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400, 
                detail="Format non supporté. Seuls les fichiers Excel (.xlsx, .xls) sont acceptés."
            )

        # Lecture et sauvegarde du fichier
        contents = await file.read()
        unique_filename = f"{file_type}_{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = Path("data") / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"💾 Fichier sauvegardé: {file_path}")
        
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
        
        # Stockage des informations du fichier
        file_session["files"][file_type] = {
            "filename": unique_filename,
            "original_name": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "upload_time": datetime.now().isoformat(),
            "missing_columns": missing_columns
        }
        
        return {
            "success": True,
            "message": f"Fichier {file_type} traité avec succès",
            "filename": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "file_size": len(contents),
            "missing_columns": missing_columns
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de l'upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/api/analyze")
async def analyze_files():
    """
    Endpoint d'analyse des fichiers LCR - Version complète avec Balance Sheet et Consumption
    """
    try:
        logger.info("🔍 Début de l'analyse Balance Sheet + Consumption")
        
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
        
        # Génération du tableau croisé dynamique Balance Sheet
        balance_sheet_results = create_balance_sheet_pivot_table(dataframes)
        
        # Génération de l'analyse Consumption
        consumption_results = create_consumption_analysis(dataframes)
        
        logger.info("✅ Analyses Balance Sheet et Consumption terminées avec succès")
        
        return {
            "success": True,
            "message": "Analyses Balance Sheet et Consumption terminées",
            "timestamp": datetime.now().isoformat(),
            "results": {
                "balance_sheet": balance_sheet_results,
                "consumption": consumption_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

def create_consumption_analysis(dataframes):
    """
    Crée l'analyse Consumption par métier
    
    Args:
        dataframes: Dict contenant les DataFrames 'j' et 'jMinus1'
    
    Returns:
        Dict contenant les résultats de l'analyse Consumption
    """
    try:
        logger.info("💼 Création de l'analyse Consumption")
        
        consumption_tables = {}
        totals_by_metier = {}
        
        # Traitement de chaque fichier
        for file_type, df in dataframes.items():
            logger.info(f"🔄 Traitement Consumption pour {file_type}")
            
            # Vérification des colonnes requises
            required_cols = ["Top Conso", "LCR_ECO_GROUPE_METIERS", "Métier", "LCR_ECO_IMPACT_LCR"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour Consumption {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données (Top Conso = "O")
            df_filtered = df[df["Top Conso"] == "O"].copy()
            logger.info(f"📋 Après filtrage Top Conso='O': {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée avec Top Conso='O' pour Consumption {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_ECO_IMPACT_LCR"] = pd.to_numeric(
                df_filtered["LCR_ECO_IMPACT_LCR"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["LCR_ECO_GROUPE_METIERS"] = df_filtered["LCR_ECO_GROUPE_METIERS"].astype(str).str.strip()
            df_filtered["Métier"] = df_filtered["Métier"].astype(str).str.strip()
            
            # Création du TCD avec groupement hiérarchique
            grouped = df_filtered.groupby([
                "LCR_ECO_GROUPE_METIERS", 
                "Métier"
            ])["LCR_ECO_IMPACT_LCR"].sum().reset_index()
            
            # Conversion en milliards
            grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)
            
            consumption_tables[file_type] = grouped
            
            # Calcul des totaux par LCR_ECO_GROUPE_METIERS
            totals_by_group = df_filtered.groupby("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR"].sum()
            totals_by_group_bn = (totals_by_group / 1_000_000_000).round(3)
            
            totals_by_metier[file_type] = {
                "total_global": (df_filtered["LCR_ECO_IMPACT_LCR"].sum() / 1_000_000_000).round(3),
                "by_groupe_metiers": totals_by_group_bn.to_dict(),
                "detailed_data": grouped
            }
            
            logger.info(f"✅ Consumption {file_type}: Total global = {totals_by_metier[file_type]['total_global']:.3f} Bn")
        
        # Génération du HTML du tableau
        consumption_html = generate_consumption_table_html(consumption_tables)
        
        # Calcul des variations
        variations = calculate_consumption_variations(totals_by_metier)
        
        # Génération de l'analyse textuelle
        analysis_text = generate_consumption_analysis_text(variations, totals_by_metier)
        
        return {
            "title": "LCR Consumption Analysis by Business Line",
            "consumption_table_html": consumption_html,
            "variations": variations,
            "analysis_text": analysis_text,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filter_applied": "Top Conso = 'O'",
                "grouping": ["LCR_ECO_GROUPE_METIERS", "Métier"],
                "measure": "LCR_ECO_IMPACT_LCR (Bn €)"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création analyse Consumption: {e}")
        return {
            "title": "Consumption Analysis - Erreur",
            "error": str(e),
            "consumption_table_html": "<p class='text-danger'>Erreur lors de la génération de l'analyse Consumption</p>"
        }

def generate_consumption_table_html(consumption_tables):
    """Génère le HTML du tableau d'analyse Consumption"""
    if len(consumption_tables) < 2:
        return "<div class='alert alert-warning'>Données insuffisantes pour l'analyse Consumption</div>"
    
    grouped_j = consumption_tables.get("j")
    grouped_j1 = consumption_tables.get("jMinus1")
    
    if grouped_j is None or grouped_j1 is None:
        return "<div class='alert alert-danger'>Erreur: données Consumption manquantes</div>"
    
    # Fusion des données pour avoir toutes les combinaisons
    all_combinations = set()
    all_combinations.update([(row["LCR_ECO_GROUPE_METIERS"], row["Métier"]) for _, row in grouped_j.iterrows()])
    all_combinations.update([(row["LCR_ECO_GROUPE_METIERS"], row["Métier"]) for _, row in grouped_j1.iterrows()])
    
    # Création des dictionnaires de lookup
    lookup_j = {(row["LCR_ECO_GROUPE_METIERS"], row["Métier"]): row["LCR_ECO_IMPACT_LCR_Bn"] 
                for _, row in grouped_j.iterrows()}
    lookup_j1 = {(row["LCR_ECO_GROUPE_METIERS"], row["Métier"]): row["LCR_ECO_IMPACT_LCR_Bn"] 
                 for _, row in grouped_j1.iterrows()}
    
    # Organisation par groupe métiers
    grouped_combinations = {}
    for groupe_metiers, metier in sorted(all_combinations):
        if groupe_metiers not in grouped_combinations:
            grouped_combinations[groupe_metiers] = []
        grouped_combinations[groupe_metiers].append(metier)
    
    html = """
    <table class="table table-bordered consumption-table">
        <thead>
            <tr>
                <th rowspan="2" class="align-middle">LCR Groupe Métiers</th>
                <th rowspan="2" class="align-middle">Métier</th>
                <th colspan="2" class="text-center header-j-minus-1">J-1 (Hier)</th>
                <th colspan="2" class="text-center header-j">J (Aujourd'hui)</th>
                <th rowspan="2" class="text-center header-variation align-middle">Variation<br>(Bn €)</th>
            </tr>
            <tr>
                <th class="text-center header-j-minus-1">Consumption (Bn €)</th>
                <th class="text-center header-j-minus-1">Part (%)</th>
                <th class="text-center header-j">Consumption (Bn €)</th>
                <th class="text-center header-j">Part (%)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Calcul des totaux globaux pour les pourcentages
    total_j1 = sum(lookup_j1.values())
    total_j = sum(lookup_j.values())
    
    # Génération des lignes par groupe métiers
    for groupe_metiers, metiers in grouped_combinations.items():
        first_metier = True
        groupe_total_j1 = sum(lookup_j1.get((groupe_metiers, m), 0) for m in metiers)
        groupe_total_j = sum(lookup_j.get((groupe_metiers, m), 0) for m in metiers)
        
        for metier in sorted(metiers):
            value_j1 = lookup_j1.get((groupe_metiers, metier), 0)
            value_j = lookup_j.get((groupe_metiers, metier), 0)
            variation = value_j - value_j1
            
            # Calcul des pourcentages
            pct_j1 = (value_j1 / total_j1 * 100) if total_j1 != 0 else 0
            pct_j = (value_j / total_j * 100) if total_j != 0 else 0
            
            html += '<tr>'
            
            # Affichage du groupe métiers seulement sur la première ligne
            if first_metier:
                rowspan = len(metiers)
                html += f'<td rowspan="{rowspan}" class="fw-bold align-middle bg-light">{groupe_metiers}</td>'
                first_metier = False
            
            html += f'<td class="ps-3">{metier}</td>'
            
            # Valeurs J-1
            html += f'<td class="text-end numeric-value">{value_j1:.3f}</td>'
            html += f'<td class="text-end numeric-value">{pct_j1:.1f}%</td>'
            
            # Valeurs J
            html += f'<td class="text-end numeric-value">{value_j:.3f}</td>'
            html += f'<td class="text-end numeric-value">{pct_j:.1f}%</td>'
            
            # Variation
            css_class = "variation-positive" if variation > 0 else "variation-negative" if variation < 0 else ""
            sign = "+" if variation > 0 else ""
            html += f'<td class="text-end numeric-value {css_class}">{sign}{variation:.3f}</td>'
            
            html += '</tr>'
        
        # Ligne de sous-total par groupe
        variation_groupe = groupe_total_j - groupe_total_j1
        pct_groupe_j1 = (groupe_total_j1 / total_j1 * 100) if total_j1 != 0 else 0
        pct_groupe_j = (groupe_total_j / total_j * 100) if total_j != 0 else 0
        
        css_class = "variation-positive" if variation_groupe > 0 else "variation-negative" if variation_groupe < 0 else ""
        sign = "+" if variation_groupe > 0 else ""
        
        html += f'''
        <tr class="table-secondary fw-bold">
            <td colspan="2" class="text-end">Sous-total {groupe_metiers}:</td>
            <td class="text-end">{groupe_total_j1:.3f}</td>
            <td class="text-end">{pct_groupe_j1:.1f}%</td>
            <td class="text-end">{groupe_total_j:.3f}</td>
            <td class="text-end">{pct_groupe_j:.1f}%</td>
            <td class="text-end {css_class}">{sign}{variation_groupe:.3f}</td>
        </tr>
        '''
    
    # Ligne de total général
    total_variation = total_j - total_j1
    css_class = "variation-positive" if total_variation > 0 else "variation-negative" if total_variation < 0 else ""
    sign = "+" if total_variation > 0 else ""
    
    html += f'''
        <tr class="total-row">
            <td colspan="2" class="text-end fw-bold">TOTAL GÉNÉRAL:</td>
            <td class="text-end fw-bold">{total_j1:.3f}</td>
            <td class="text-end fw-bold">100.0%</td>
            <td class="text-end fw-bold">{total_j:.3f}</td>
            <td class="text-end fw-bold">100.0%</td>
            <td class="text-end fw-bold {css_class}">{sign}{total_variation:.3f}</td>
        </tr>
    '''
    
    html += """
        </tbody>
    </table>
    """
    
    return html

def calculate_consumption_variations(totals_by_metier):
    """Calcule les variations de consumption entre J et J-1"""
    if "j" not in totals_by_metier or "jMinus1" not in totals_by_metier:
        return {}
    
    j_data = totals_by_metier["j"]
    j1_data = totals_by_metier["jMinus1"]
    
    # Variation globale
    global_variation = j_data["total_global"] - j1_data["total_global"]
    
    # Variations par groupe métiers
    group_variations = {}
    all_groups = set(j_data["by_groupe_metiers"].keys()) | set(j1_data["by_groupe_metiers"].keys())
    
    for group in all_groups:
        j_value = j_data["by_groupe_metiers"].get(group, 0)
        j1_value = j1_data["by_groupe_metiers"].get(group, 0)
        group_variations[group] = {
            "j_minus_1": j1_value,
            "j": j_value,
            "variation": round(j_value - j1_value, 3)
        }
    
    return {
        "global": {
            "j_minus_1": j1_data["total_global"],
            "j": j_data["total_global"],
            "variation": round(global_variation, 3)
        },
        "by_groupe_metiers": group_variations
    }

def generate_consumption_analysis_text(variations, totals_by_metier):
    """Génère le texte d'analyse de la consumption au format demandé"""
    if not variations or "global" not in variations:
        return "Analyse Consumption non disponible - données insuffisantes."
    
    global_data = variations["global"]
    date_str = datetime.now().strftime("March %d")
    
    # Analyse globale
    total_j = global_data["j"]
    variation = global_data["variation"]
    direction = "decrease" if variation < 0 else "increase"
    
    analysis = f"Overall, on {date_str}, businesses have consumption of {total_j:.2f} Bn, representing a {direction} of {abs(variation):.2f} Bn compared to yesterday."
    
    # Identification des principales variations par groupe
    if "by_groupe_metiers" in variations:
        significant_variations = []
        for group, data in variations["by_groupe_metiers"].items():
            group_var = data["variation"]
            if abs(group_var) >= 0.05:  # Variations >= 50M
                sign = "-" if group_var < 0 else "+"
                significant_variations.append(f"{group} ({sign}{abs(group_var):.2f} Bn)")
        
        if significant_variations:
            if variation < 0:
                analysis += f" This decrease is mainly supported by {', '.join(significant_variations[:3])}."
            else:
                analysis += f" This increase is mainly driven by {', '.join(significant_variations[:3])}."
    
    return analysis

def create_balance_sheet_pivot_table(dataframes):
    """
    Crée le tableau croisé dynamique Balance Sheet
    
    Args:
        dataframes: Dict contenant les DataFrames 'j' et 'jMinus1'
    
    Returns:
        Dict contenant les résultats de l'analyse
    """
    try:
        logger.info("💼 Création du TCD Balance Sheet")
        
        pivot_tables = {}
        totals_summary = {}
        
        # Traitement de chaque fichier
        for file_type, df in dataframes.items():
            logger.info(f"🔄 Traitement du fichier {file_type}")
            
            # Filtrage des données
            df_filtered = df[df["Top Conso"] == "O"].copy()
            logger.info(f"📋 Après filtrage Top Conso='O': {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée avec Top Conso='O' pour {file_type}")
                continue
            
            # Préparation des colonnes
            df_filtered["Nominal Value"] = pd.to_numeric(
                df_filtered["Nominal Value"], errors='coerce'
            ).fillna(0)
            
            df_filtered["Réaffectation"] = df_filtered["Réaffectation"].astype(str).str.upper().str.strip()
            
            # Filtrage ACTIF/PASSIF uniquement
            df_filtered = df_filtered[
                df_filtered["Réaffectation"].isin(["ACTIF", "PASSIF"])
            ].copy()
            
            logger.info(f"📊 Après filtrage ACTIF/PASSIF: {len(df_filtered)} lignes")
            logger.info(f"🏷️ Réaffectations trouvées: {sorted(df_filtered['Réaffectation'].unique())}")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée ACTIF/PASSIF pour {file_type}")
                continue
            
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
            
            # Conversion en milliards d'euros
            pivot_table = (pivot_table / 1_000_000_000).round(2)
            
            # Assurer la présence des colonnes ACTIF et PASSIF
            for col in ["ACTIF", "PASSIF"]:
                if col not in pivot_table.columns:
                    pivot_table[col] = 0.0
            
            # Réorganisation des colonnes
            pivot_table = pivot_table[["ACTIF", "PASSIF"]]
            
            pivot_tables[file_type] = pivot_table
            
            # Calcul des totaux
            if "TOTAL" in pivot_table.index:
                totals_summary[file_type] = {
                    "ACTIF": float(pivot_table.loc["TOTAL", "ACTIF"]),
                    "PASSIF": float(pivot_table.loc["TOTAL", "PASSIF"])
                }
            
            logger.info(f"✅ TCD {file_type} créé: {pivot_table.shape[0]} lignes x {pivot_table.shape[1]} colonnes")
        
        # Génération du HTML du tableau combiné
        pivot_html = generate_pivot_table_html(pivot_tables)
        
        # Calcul des variations
        variations = calculate_variations(totals_summary)
        
        # Génération du résumé exécutif
        summary = generate_executive_summary(variations)
        
        return {
            "title": "Balance Sheet - Tableau Croisé Dynamique (ACTIF/PASSIF)",
            "pivot_table_html": pivot_html,
            "variations": variations,
            "summary": summary,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "reaffectation": ["ACTIF", "PASSIF"]
                },
                "files_analyzed": list(pivot_tables.keys())
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création TCD: {e}")
        return {
            "title": "Balance Sheet - Erreur",
            "error": str(e),
            "pivot_table_html": "<p class='text-danger'>Erreur lors de la génération du tableau</p>"
        }

def generate_pivot_table_html(pivot_tables):
    """
    Génère le HTML du tableau croisé dynamique combiné
    
    Args:
        pivot_tables: Dict des tables pivot par type de fichier
    
    Returns:
        String HTML du tableau formaté
    """
    if len(pivot_tables) < 2:
        return "<div class='alert alert-warning'>Données insuffisantes pour générer le TCD complet</div>"
    
    pivot_j = pivot_tables.get("j")
    pivot_j1 = pivot_tables.get("jMinus1")
    
    if pivot_j is None or pivot_j1 is None:
        return "<div class='alert alert-danger'>Erreur: données manquantes pour la comparaison</div>"
    
    # Liste des groupes de produits (sans TOTAL pour l'instant)
    all_products = sorted([p for p in set(pivot_j.index) | set(pivot_j1.index) if p != "TOTAL"])
    all_products.append("TOTAL")  # Ajouter TOTAL à la fin
    
    html = """
    <table class="table table-bordered pivot-table">
        <thead>
            <tr>
                <th rowspan="2" class="align-middle">Groupe De Produit</th>
                <th colspan="2" class="text-center header-j-minus-1">J-1 (Hier)</th>
                <th colspan="2" class="text-center header-j">J (Aujourd'hui)</th>
                <th colspan="2" class="text-center header-variation">Variation (J - J-1)</th>
            </tr>
            <tr>
                <th class="text-center header-j-minus-1">ACTIF</th>
                <th class="text-center header-j-minus-1">PASSIF</th>
                <th class="text-center header-j">ACTIF</th>
                <th class="text-center header-j">PASSIF</th>
                <th class="text-center header-variation">ACTIF</th>
                <th class="text-center header-variation">PASSIF</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Génération des lignes
    for product in all_products:
        css_class = "total-row" if product == "TOTAL" else ""
        html += f'<tr class="{css_class}">'
        html += f'<td class="fw-bold">{product}</td>'
        
        # Valeurs J-1
        for category in ["ACTIF", "PASSIF"]:
            value_j1 = pivot_j1.loc[product, category] if product in pivot_j1.index else 0.0
            html += f'<td class="text-end numeric-value">{value_j1:.2f}</td>'
        
        # Valeurs J
        for category in ["ACTIF", "PASSIF"]:
            value_j = pivot_j.loc[product, category] if product in pivot_j.index else 0.0
            html += f'<td class="text-end numeric-value">{value_j:.2f}</td>'
        
        # Variations
        for category in ["ACTIF", "PASSIF"]:
            value_j1 = pivot_j1.loc[product, category] if product in pivot_j1.index else 0.0
            value_j = pivot_j.loc[product, category] if product in pivot_j.index else 0.0
            variation = value_j - value_j1
            
            css_class = "variation-positive" if variation > 0 else "variation-negative" if variation < 0 else ""
            sign = "+" if variation > 0 else ""
            html += f'<td class="text-end numeric-value {css_class}">{sign}{variation:.2f}</td>'
        
        html += '</tr>'
    
    html += """
        </tbody>
    </table>
    """
    
    return html

def calculate_variations(totals_summary):
    """
    Calcule les variations entre J et J-1
    
    Args:
        totals_summary: Dict des totaux par fichier
    
    Returns:
        Dict des variations calculées
    """
    if "j" not in totals_summary or "jMinus1" not in totals_summary:
        return {}
    
    variations = {}
    for category in ["ACTIF", "PASSIF"]:
        j_value = totals_summary["j"].get(category, 0)
        j1_value = totals_summary["jMinus1"].get(category, 0)
        
        variations[category] = {
            "j_minus_1": round(j1_value, 2),
            "j": round(j_value, 2),
            "variation": round(j_value - j1_value, 2)
        }
    
    return variations

def generate_executive_summary(variations):
    """
    Génère un résumé exécutif de l'analyse
    
    Args:
        variations: Dict des variations calculées
    
    Returns:
        String du résumé exécutif
    """
    if not variations:
        return "Analyse incomplète - données insuffisantes pour générer un résumé."
    
    date_str = datetime.now().strftime("%d/%m/%Y")
    summary_parts = []
    
    for category, data in variations.items():
        variation = data["variation"]
        if abs(variation) >= 0.1:  # Variations significatives >= 100M€
            direction = "hausse" if variation > 0 else "baisse"
            summary_parts.append(f"{category}: {direction} de {abs(variation):.2f} Md€")
    
    if summary_parts:
        return f"Balance Sheet au {date_str} - Principales variations: {', '.join(summary_parts)}."
    else:
        return f"Balance Sheet au {date_str} - Variations mineures observées (< 100M€)."

if __name__ == "__main__":
    print("🚀 Steering ALM Metrics - Version Templates")
    print("📊 Interface: http://localhost:8000")
    print("📁 Templates: templates/index.html")
    print("🎨 Styles: static/js/main.js")
    print("⏹️  Ctrl+C pour arrêter")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )