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
import math
import statistics
import chardet

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
required_dirs = ["data", "templates", "static", "static/js", "static/css", "static/images"]
for directory in required_dirs:
    Path(directory).mkdir(exist_ok=True)

# Formats supportés
SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', '.tsv', '.txt']

# Configuration des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Variables globales pour la session (en production: utiliser une base de données)
file_session = {"files": {}}

REQUIRED_COLUMNS = {
    "balance_sheet": [
        "Top Conso",
        "Réaffectation", 
        "Groupe De Produit",
        "Nominal Value"
    ],
    "consumption": [
        "Top Conso",
        "LCR_ECO_GROUPE_METIERS",
        "LCR_ECO_IMPACT_LCR",
        "Métier",
        "Sous-Métier"
    ]
}

ALL_REQUIRED_COLUMNS = list(set(
    REQUIRED_COLUMNS["balance_sheet"] + 
    REQUIRED_COLUMNS["consumption"]
))

def convert_any_file_to_excel(file_path):
    """
    Lit n'importe quel fichier et le convertit en Excel - Version optimisée
    Retourne le chemin du fichier Excel créé
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    try:
        # Si c'est déjà Excel, on garde tel quel
        if extension in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            return file_path
        
        # Si c'est CSV/TSV/TXT, on le convertit
        elif extension in ['.csv', '.tsv', '.txt']:
            logger.info(f"Conversion {extension} vers Excel en cours...")
            
            # Détecter l'encodage
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            logger.info(f"Encodage détecté: {encoding}")
            
            # Détecter le délimiteur
            if extension == '.tsv':
                delimiter = '\t'
            else:
                with open(file_path, 'r', encoding=encoding) as f:
                    first_line = f.readline()
                    if ';' in first_line:
                        delimiter = ';'
                    elif '\t' in first_line:
                        delimiter = '\t'
                    else:
                        delimiter = ','
            
            logger.info(f"Délimiteur détecté: '{delimiter}'")
            
            # Lire le fichier CSV avec optimisations pour éviter les warnings
            df = pd.read_csv(
                file_path, 
                delimiter=delimiter, 
                encoding=encoding,
                low_memory=False,      # Évite les warnings DtypeWarning
                dtype=str,             # Force tout en string pour éviter détection automatique
                na_filter=False        # Évite la conversion des valeurs vides en NaN
            )
            
            # Nettoyer les noms de colonnes
            df.columns = df.columns.astype(str).str.strip()
            
            logger.info(f"CSV lu: {len(df)} lignes, {len(df.columns)} colonnes")
            
            # Convertir les colonnes numériques connues après lecture
            numeric_columns = ['Nominal Value', 'LCR_ECO_IMPACT_LCR']
            for col in numeric_columns:
                if col in df.columns:
                    # Nettoyer et convertir en numérique
                    df[col] = pd.to_numeric(df[col].str.replace(',', '.'), errors='coerce')
            
            # Convertir en Excel
            excel_path = file_path.with_suffix('.xlsx')
            logger.info(f"Écriture Excel vers: {excel_path}")
            
            df.to_excel(excel_path, index=False, engine='openpyxl')
            
            # Supprimer l'original
            file_path.unlink()
            
            logger.info(f"Conversion terminée: {extension} → .xlsx")
            return excel_path
        
        else:
            raise ValueError(f"Format non supporté: {extension}")
            
    except Exception as e:
        logger.error(f"Erreur conversion {extension}: {e}")
        raise ValueError(f"Erreur conversion vers Excel: {str(e)}")
    
#######################################################################################################################################

#                           API

#######################################################################################################################################


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
    Upload avec conversion automatique vers Excel
    """
    try:
        logger.info(f"Upload reçu: {file.filename}, type: {file_type}")
        
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        file_extension = Path(file.filename).suffix.lower()
        SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', '.tsv', '.txt']
        
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Format non supporté: {file_extension}. Formats acceptés: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # Sauvegarder le fichier
        contents = await file.read()
        unique_filename = f"{file_type}_{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = Path("data") / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # CONVERSION AUTOMATIQUE VERS EXCEL
        try:
            excel_path = convert_any_file_to_excel(file_path)
            logger.info(f"Fichier converti vers Excel: {excel_path}")
            
            # Lire le fichier Excel pour validation
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.astype(str).str.strip()
            
        except Exception as e:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=f"Erreur conversion: {str(e)}")
        
        # Vérifier les colonnes
        missing_columns = [col for col in ALL_REQUIRED_COLUMNS if col not in df.columns]
        
        # Stocker les infos (avec le nom du fichier Excel)
        file_session["files"][file_type] = {
            "filename": excel_path.name,  # Nom du fichier Excel converti
            "original_name": file.filename,
            "original_format": file_extension,
            "rows": len(df),
            "columns": len(df.columns),
            "upload_time": datetime.now().isoformat(),
            "missing_columns": missing_columns
        }
        
        return {
            "success": True,
            "message": f"Fichier {file_type} lu et converti en Excel ({file_extension} → .xlsx)",
            "filename": file.filename,
            "original_format": file_extension,
            "converted_to": "Excel",
            "rows": len(df),
            "columns": len(df.columns),
            "missing_columns": missing_columns,
            "file_size": len(contents)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    
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
        consumption_results = create_consumption_analysis_grouped_only(dataframes)
        
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

#######################################################################################################################################

#                           BALANCE SHEET

#######################################################################################################################################

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
            "title": "Balance Sheet",
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
                <th colspan="2" class="text-center header-j-minus-1">D-1 (Yesterday)</th>
                <th colspan="2" class="text-center header-j">D (Today)</th>
                <th colspan="2" class="text-center header-variation">Variation (D - D-1)</th>
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
        return f"On {date_str} Natixis' balance sheet presents some variations: {', '.join(summary_parts)}."
    else:
        return f"Balance Sheet au {date_str} - Variations mineures observées (< 100M€)."

#######################################################################################################################################

#                           CONSUMPTION

#######################################################################################################################################

def create_consumption_analysis_grouped_only(dataframes):
    """
    Crée l'analyse Consumption UNIQUEMENT par Groupe Métiers (sans détail des métiers)
    """
    try:
        logger.info("💼 Création de l'analyse Consumption - Groupes Métiers uniquement")
        
        consumption_grouped = {}
        totals_by_group = {}
        metier_details = {}  # Initialiser au début
        
        # Traitement de chaque fichier
        for file_type, df in dataframes.items():
            logger.info(f"🔄 Traitement Consumption groupé pour {file_type}")
            
            # Vérification des colonnes requises
            required_cols = ["Top Conso", "LCR_ECO_GROUPE_METIERS", "LCR_ECO_IMPACT_LCR"]
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
            
            # Groupement UNIQUEMENT par LCR_ECO_GROUPE_METIERS
            grouped = df_filtered.groupby("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR"].sum().reset_index()
            
            # Conversion en milliards
            grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)
            
            consumption_grouped[file_type] = grouped
            
            # Calcul des totaux
            total_global = (df_filtered["LCR_ECO_IMPACT_LCR"].sum() / 1_000_000_000).round(3)
            
            totals_by_group[file_type] = {
                "total_global": total_global,
                "by_groupe_metiers": grouped.set_index("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR_Bn"].to_dict(),
                "grouped_data": grouped
            }
            
            logger.info(f"✅ Consumption groupé {file_type}: {len(grouped)} groupes, Total global = {total_global:.3f} Bn")
        
        # Génération du HTML du tableau groupé
        consumption_html = generate_consumption_grouped_table_html(consumption_grouped)
        
        # Calcul des variations
        variations = calculate_consumption_grouped_variations(totals_by_group)

        # Génération de l'analyse textuelle
        analysis_text, significant_groups = generate_consumption_grouped_analysis_text(variations, totals_by_group, dataframes)

        # Génération de l'analyse détaillée par métier (NOUVELLE VERSION)
        metier_detailed_analysis = generate_metier_detailed_analysis(significant_groups, dataframes)

        # Préparer les données détaillées par métier pour les groupes significatifs
        metier_details = {}
        for file_type, df in dataframes.items():
            df_filtered = df[df["Top Conso"] == "O"].copy()
            if "Métier" in df_filtered.columns:
                print(significant_groups)
                if len(significant_groups) != 0:
                    # Filtrer pour les groupes significatifs seulement
                    df_significant = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(significant_groups)]
                    
                    # Grouper par groupe métier et métier
                    grouped = df_significant.groupby(["LCR_ECO_GROUPE_METIERS", "Métier"])["LCR_ECO_IMPACT_LCR"].sum().reset_index()
                    grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)
                    
                    # CONVERTIR EN DICTIONNAIRE SÉRIALISABLE
                    metier_details[file_type] = grouped.to_dict(orient='records')
        
        print (f"TESTSTSTSTSTSTST : {metier_detailed_analysis}")
        return {
            "title": "LCR Consumption Analysis by Business Group (Summary)",
            "consumption_table_html": consumption_html,
            "variations": variations,
            "analysis_text": analysis_text,
            "metier_detailed_analysis": metier_detailed_analysis, 
            "significant_groups": significant_groups,
            "metier_details": metier_details,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filter_applied": "Top Conso = 'O'",
                "grouping": ["LCR_ECO_GROUPE_METIERS"],  # Seulement groupe, pas métier
                "measure": "LCR_ECO_IMPACT_LCR (Bn €)",
                "view_type": "grouped_summary"
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur création analyse Consumption groupée: {e}")
        return {
            "title": "Consumption Analysis Grouped - Erreur",
            "error": str(e),
            "consumption_table_html": "<p class='text-danger'>Erreur lors de la génération de l'analyse Consumption groupée</p>"
        }
    
def generate_consumption_grouped_table_html(consumption_grouped):
    """
    Génère le HTML du tableau Consumption GROUPÉ (sans détail métiers)
    """
    if len(consumption_grouped) < 2:
        return "<div class='alert alert-warning'>Données insuffisantes pour l'analyse Consumption groupée</div>"
    
    grouped_j = consumption_grouped.get("j")
    grouped_j1 = consumption_grouped.get("jMinus1")
    
    if grouped_j is None or grouped_j1 is None:
        return "<div class='alert alert-danger'>Erreur: données Consumption groupées manquantes</div>"
    
    # Fusion de tous les groupes métiers
    all_groups = set()
    all_groups.update(grouped_j["LCR_ECO_GROUPE_METIERS"].tolist())
    all_groups.update(grouped_j1["LCR_ECO_GROUPE_METIERS"].tolist())
    
    # Création des dictionnaires de lookup
    lookup_j = grouped_j.set_index("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR_Bn"].to_dict()
    lookup_j1 = grouped_j1.set_index("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR_Bn"].to_dict()
    
    html = """
    <table class="table table-bordered consumption-table">
        <thead>
            <tr>
                <th rowspan="2" class="align-middle">LCR Groupe Métiers</th>
                <th colspan="2" class="text-center header-j-minus-1">D-1 (Yesterday)</th>
                <th colspan="2" class="text-center header-j">D (Today)</th>
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
    
    # Génération des lignes - UNE LIGNE PAR GROUPE MÉTIER
    for groupe_metiers in sorted(all_groups):
        value_j1 = lookup_j1.get(groupe_metiers, 0)
        value_j = lookup_j.get(groupe_metiers, 0)
        variation = value_j - value_j1
        
        # Calcul des pourcentages
        pct_j1 = (value_j1 / total_j1 * 100) if total_j1 != 0 else 0
        pct_j = (value_j / total_j * 100) if total_j != 0 else 0
        
        html += '<tr>'
        html += f'<td class="fw-bold">{groupe_metiers}</td>'
        
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
    
    # Ligne de total général
    total_variation = total_j - total_j1
    css_class = "variation-positive" if total_variation > 0 else "variation-negative" if total_variation < 0 else ""
    sign = "+" if total_variation > 0 else ""
    
    html += f'''
        <tr class="total-row">
            <td class="text-end fw-bold">TOTAL GÉNÉRAL:</td>
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

def calculate_consumption_grouped_variations(totals_by_group):
    """Calcule les variations de consumption groupée entre J et J-1"""
    if "j" not in totals_by_group or "jMinus1" not in totals_by_group:
        return {}
    
    j_data = totals_by_group["j"]
    j1_data = totals_by_group["jMinus1"]
    
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

def generate_consumption_grouped_analysis_text(variations, totals_by_group, dataframes=None):
    """Génère le texte d'analyse de la consumption groupée avec mapping Métier -> Sous-Métier"""
    if not variations or "global" not in variations:
        return "Analyse Consumption groupée non disponible - données insuffisantes.", []
    
    # Créer le mapping Métier -> Sous-Métier depuis les données Excel IL SERT À RIEN ICI ON UTILISE PAS MÉTIER MAIS À RÉUTILISER POUR LES MÉTIER AU NIVEAU DE GRANULARITÉ SUIVANT.
    metier_to_sous_metier = {}
    if dataframes is not None and isinstance(dataframes, dict): #ATTENTION NE PAS METTRE if dataframes.
        # Utiliser le fichier J pour créer le mapping (ou J-1 si J n'existe pas)
        df_for_mapping = dataframes.get("j")
        if df_for_mapping is None:
            df_for_mapping = dataframes.get("jMinus1")
        
        if df_for_mapping is not None:
            # Vérifier que les colonnes existent
            if "Métier" in df_for_mapping.columns and "Sous-Métier" in df_for_mapping.columns:
                try:
                    # Créer le mapping en supprimant les doublons
                    mapping_df = df_for_mapping[["Métier", "Sous-Métier"]].dropna().drop_duplicates()
                    metier_to_sous_metier = mapping_df.set_index("Métier")["Sous-Métier"].to_dict()
                    logger.info(f"Mapping Métier -> Sous-Métier créé: {len(metier_to_sous_metier)} entrées")
                except Exception as e:
                    logger.warning(f"Erreur création mapping Métier->Sous-Métier: {e}")
            else:
                logger.warning("Colonnes 'Métier' ou 'Sous-Métier' non trouvées dans les données")
    
    global_data = variations["global"]
    date_str = datetime.now().strftime("March %d")
    
    # Analyse globale
    total_j = global_data["j"]
    variation = global_data["variation"]
    direction = "decrease" if variation < 0 else "increase"
    
    analysis = f"Summary view: on {date_str}, business groups have total consumption of {total_j:.2f} Bn, representing a {direction} of {abs(variation):.2f} Bn compared to yesterday."
    
    # Identification des principales variations par groupe (auto, sans paramètre)
    significant_groups = []
    if "by_groupe_metiers" in variations and variations["by_groupe_metiers"]:
        def _tukey_upper_threshold(values):
            import statistics
            if len(values) < 4:
                return max(values) if values else 0.0
            q1 = statistics.quantiles(values, n=4)[0]
            q3 = statistics.quantiles(values, n=4)[2]
            iqr = q3 - q1
            return q3 + 1.5 * iqr

        def _knee_index(cum_shares):
            n = len(cum_shares)
            if n == 0:
                return None
            diffs = []
            for i, cs in enumerate(cum_shares, start=1):
                baseline = i / n
                diffs.append(cs - baseline)
            k = max(range(n), key=lambda i: diffs[i])
            return k if diffs[k] > 1e-9 else None

        by_grp = variations["by_groupe_metiers"]
        items = []
        for group, data in by_grp.items():
            gv = float(data.get("variation", 0.0))
            items.append((group, gv, abs(gv)))

        net_var = float(global_data.get("variation", 0.0))
        net_mag = abs(net_var)

        selected = []
        # CAS 1 : mouvement net significatif -> sélection des "drivers" alignés (knee + outliers IQR)
        if net_mag >= 1e-9:
            sign = 1 if net_var >= 0 else -1
            aligned = [(g, v, av) for (g, v, av) in items if (v > 0 and sign > 0) or (v < 0 and sign < 0)]
            aligned.sort(key=lambda x: x[2], reverse=True)

            cum = 0.0
            cum_shares = []
            for _, _, av in aligned:
                cum += av
                cum_shares.append(min(cum / net_mag, 1.0))

            knee = _knee_index(cum_shares)
            if knee is not None:
                selected = aligned[:knee+1]

            aligned_abs = [av for (_, _, av) in aligned]
            upper = _tukey_upper_threshold(aligned_abs)
            for tup in aligned:
                if tup not in selected and tup[2] >= upper:
                    selected.append(tup)

            if not selected and aligned:
                selected = [aligned[0]]  # au moins le plus gros driver

        # CAS 2 : net ~ 0 -> sortir les vrais movers (IQR) des deux côtés
        else:
            abs_vars = [av for (_, _, av) in items]
            upper = _tukey_upper_threshold(abs_vars)
            movers = [(g, v, av) for (g, v, av) in items if av >= upper]
            movers.sort(key=lambda x: x[2], reverse=True)
            if not movers and items:
                movers = [max(items, key=lambda x: x[2])]
            selected = movers

        # Mise en forme avec mapping Métier -> Sous-Métier
        significant_variations = []
        for g, v, av in selected:
            sign_sym = "-" if v < 0 else "+"
            
            # Utiliser le mapping pour obtenir le nom complet
            display_name = metier_to_sous_metier.get(g, g)  # Si pas de mapping trouvé, utiliser g
            
            significant_variations.append(f"{display_name} ({sign_sym}{abs(v):.2f} Bn)")
            significant_groups.append(g)  # Garder l'abréviation pour les traitements ultérieurs

        if significant_variations:
            if variation < 0:
                analysis += f" Main contributors to this decrease: {', '.join(significant_variations)}."
            else:
                analysis += f" Main drivers of this increase: {', '.join(significant_variations)}."
    
    return analysis, significant_groups

def generate_metier_detailed_analysis(significant_groups, dataframes=None):
    """
    Génère une analyse textuelle détaillée des métiers avec les plus grosses variations
    en recréant les données métier depuis les DataFrames
    """
    if not significant_groups or not dataframes:
        return ""
    
    logger.info(f"Génération analyse détaillée pour groupes: {significant_groups}")
    
    # Créer le mapping Métier -> Sous-Métier
    metier_to_sous_metier = {}
    if dataframes is not None and isinstance(dataframes, dict):
        df_for_mapping = dataframes.get("j")
        if df_for_mapping is None:
            df_for_mapping = dataframes.get("jMinus1")
        
        if df_for_mapping is not None:
            has_metier = "Métier" in df_for_mapping.columns
            has_sous_metier = "Sous-Métier" in df_for_mapping.columns
            
            if has_metier and has_sous_metier:
                try:
                    mapping_df = df_for_mapping[["Métier", "Sous-Métier"]].dropna().drop_duplicates()
                    metier_to_sous_metier = mapping_df.set_index("Métier")["Sous-Métier"].to_dict()
                    logger.info(f"Mapping Métier -> Sous-Métier créé pour analyse détaillée: {len(metier_to_sous_metier)} entrées")
                except Exception as e:
                    logger.warning(f"Erreur création mapping pour analyse détaillée: {e}")
    
    # Recréer les données métier depuis les DataFrames
    metier_data = {}
    
    try:
        for file_type, df in dataframes.items():
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            # Vérifier si la colonne Métier existe
            if "Métier" not in df_filtered.columns:
                logger.warning(f"Colonne 'Métier' non trouvée dans {file_type}, analyse détaillée impossible")
                continue
            
            if len(significant_groups) > 0:
                # Filtrer pour les groupes significatifs seulement
                df_significant = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(significant_groups)]
                
                if df_significant.empty:  # Utiliser .empty au lieu de len() == 0
                    logger.warning(f"Aucune donnée pour les groupes significatifs dans {file_type}")
                    continue
                
                # Grouper par groupe métier et métier
                grouped = df_significant.groupby(["LCR_ECO_GROUPE_METIERS", "Métier"])["LCR_ECO_IMPACT_LCR"].sum().reset_index()
                grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)
                
                metier_data[file_type] = grouped
                logger.info(f"Données métier créées pour {file_type}: {len(grouped)} lignes")
    
    except Exception as e:
        logger.error(f"Erreur lors de la création des données métier: {e}")
        return ""

    # Vérifier que nous avons les données J et J-1
    if "j" not in metier_data or "jMinus1" not in metier_data:
        logger.warning("Données J ou J-1 manquantes pour l'analyse détaillée")
        return ""
    
    data_j = metier_data["j"]
    data_j1 = metier_data["jMinus1"]
    
    # Vérifier que les DataFrames ne sont pas vides
    if data_j.empty or data_j1.empty:
        logger.warning("DataFrames J ou J-1 vides pour l'analyse détaillée")
        return ""
    
    # Créer des dictionnaires de lookup par (groupe, métier)
    lookup_j = {}
    lookup_j1 = {}
    
    try:
        for _, row in data_j.iterrows():
            key = (row["LCR_ECO_GROUPE_METIERS"], row["Métier"])
            lookup_j[key] = row["LCR_ECO_IMPACT_LCR_Bn"]
        
        for _, row in data_j1.iterrows():
            key = (row["LCR_ECO_GROUPE_METIERS"], row["Métier"])
            lookup_j1[key] = row["LCR_ECO_IMPACT_LCR_Bn"]
    
    except Exception as e:
        logger.error(f"Erreur lors de la création des dictionnaires lookup: {e}")
        return ""
    
# Calculer les variations par métier
    all_keys = set(lookup_j.keys()) | set(lookup_j1.keys())
    metier_variations = []
    
    for key in all_keys:
        groupe, metier = key
        if groupe in significant_groups:  # Seulement les groupes significatifs
            value_j = lookup_j.get(key, 0)
            value_j1 = lookup_j1.get(key, 0)
            variation = value_j - value_j1
            
            # Utiliser le mapping pour obtenir le nom complet
            display_name = metier_to_sous_metier.get(metier, metier)
            
            metier_variations.append({
                "groupe": groupe,
                "metier": metier,
                "display_name": display_name,
                "variation": variation,
                "abs_variation": abs(variation),
                "value_j": value_j,
                "value_j1": value_j1
            })
    
    # NOUVEAU: Grouper par groupe métier et prendre le top 3 de chaque groupe
    variations_by_group = {}
    for variation in metier_variations:
        groupe = variation["groupe"]
        if groupe not in variations_by_group:
            variations_by_group[groupe] = []
        variations_by_group[groupe].append(variation)
    
    # Trier chaque groupe par variation absolue décroissante et prendre le top 3
    top_variations_by_group = {}
    for groupe, variations in variations_by_group.items():
        # Trier par variation absolue décroissante
        sorted_variations = sorted(variations, key=lambda x: x["abs_variation"], reverse=True)
        # Prendre les 3 premières (ou moins si moins de 3 métiers)
        top_variations_by_group[groupe] = sorted_variations[:3]
    
    # Générer le texte d'analyse
    date_str = datetime.now().strftime("March %d")
    group_sentences = []
    
    # Traiter chaque groupe séparément pour créer des phrases distinctes
    for groupe in significant_groups:
        if groupe in top_variations_by_group:
            group_variations = top_variations_by_group[groupe]
            group_parts = []
            
            for item in group_variations:
                variation = item["variation"]
                abs_variation = item["abs_variation"]
                display_name = item["display_name"]
                
                # Ignorer les variations très faibles
                if abs_variation < 0.01:  # Moins de 10M€
                    continue
                
                direction = "increased" if variation > 0 else "decreased"
                group_parts.append(f"{display_name} {direction} by {abs_variation:.2f} Bn")
            
            # Créer une phrase complète pour ce groupe avec le nom du groupe en gras
            if group_parts:
                group_sentence = f"In <strong>{groupe}</strong>, {', '.join(group_parts)}"
                group_sentences.append(group_sentence)
    
    if group_sentences:
        # Joindre les phrases avec ". " pour séparer chaque groupe
        full_text = ". ".join(group_sentences)
        return f"At the detailed level: {full_text}."
    
    return ""


if __name__ == "__main__":
    print("🚀 Steering ALM Metrics - Version Templates")
    print("📊 Interface: http://localhost:8000")
    print("📁 Templates: templates/index.html")
    print("🎨 Styles: static/js/main.js")
    print("⏹️  Ctrl+C pour arrêter")
    
    uvicorn.run(
        app,
        host="localhost",
        port=8000,
        reload=False,
        log_level="info",
        timeout_keep_alive=300,  # 5 minutes
        limit_max_requests=1000
    )