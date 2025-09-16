#!/usr/bin/env python3
#run.py
"""
Steering ALM Metrics - Version avec Templates
============================================

Application FastAPI utilisant un système de templates Jinja2
pour séparer la logique métier de la présentation.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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
import io
import chardet
import json
from typing import Dict, Any, Optional
import psutil
import os
import tempfile
from user import authenticate_user, log_activity, get_logs, USERS_DB
import secrets

from llm_connector import LLMConnector
from report_generator import ReportGenerator

# Variables globales pour la session chatbot
chatbot_session = {
    "messages": [],
    "context_data": {},
    "uploaded_documents": []
}

# Initialiser le connecteur LLM
llm_connector = LLMConnector()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(title="Steering ALM Metrics", version="2.0.0")


# Session utilisateur global (en production: vraies sessions)
active_sessions = {}

def generate_session_token():
    return secrets.token_urlsafe(32)

def get_current_user_from_session(session_token: Optional[str] = Cookie(None)):
    """Récupère l'utilisateur depuis le token de session"""
    if not session_token or session_token not in active_sessions:
        return None
    return active_sessions[session_token]

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

def convert_file_content_to_dataframe(file_content: bytes, filename: str):
    """
    Convertit le contenu d'un fichier directement en DataFrame
    Sans écriture sur disque
    """
    try:
        extension = Path(filename).suffix.lower()
        
        # Excel - lecture directe depuis bytes
        if extension in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            df.columns = df.columns.astype(str).str.strip()
            return df, {'format': extension, 'method': 'direct_excel'}
        
        # CSV/TSV/TXT - traitement en mémoire
        elif extension in ['.csv', '.tsv', '.txt']:
            # Détecter l'encodage
            encoding = chardet.detect(file_content[:10000])['encoding'] or 'utf-8'
            
            # Décoder en string
            text_content = file_content.decode(encoding)
            
            # Détecter le délimiteur
            if extension == '.tsv':
                delimiter = '\t'
            else:
                first_line = text_content.split('\n')[0]
                if ';' in first_line:
                    delimiter = ';'
                elif '\t' in first_line:
                    delimiter = '\t'
                else:
                    delimiter = ','
            
            # Lire directement depuis StringIO (en mémoire)
            df = pd.read_csv(
                io.StringIO(text_content),
                delimiter=delimiter,
                low_memory=False,
                dtype=str,
                na_filter=False
            )
            
            # Nettoyer les colonnes
            df.columns = df.columns.astype(str).str.strip()
            
            # Convertir les colonnes numériques
            numeric_columns = ['Nominal Value', 'LCR_ECO_IMPACT_LCR']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].str.replace(',', '.'), errors='coerce')
            
            return df, {
                'format': extension, 
                'encoding': encoding, 
                'delimiter': delimiter,
                'method': 'memory_csv'
            }
        
        else:
            raise ValueError(f"Format non supporté: {extension}")
            
    except Exception as e:
        raise ValueError(f"Erreur lecture fichier: {str(e)}")

#######################################################################################################################################

#                           API

#######################################################################################################################################

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Page d'accueil - redirige vers login si non connecté"""
    session_token = request.cookies.get("session_token")
    current_user = get_current_user_from_session(session_token)
    
    if not current_user:
        # Utilisateur non connecté -> page de login
        return templates.TemplateResponse("login.html", {
            "request": request,
            "title": "Login - Steering ALM Metrics"
        })
    
    # Utilisateur connecté -> page principale
    log_activity(current_user["username"], "ACCESS", "Accessed main page")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Steering ALM Metrics",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "user": current_user
    })

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

@app.post("/api/login")
async def login(request: Request):
    """Authentification utilisateur"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        user = authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Créer une session
        session_token = generate_session_token()
        active_sessions[session_token] = user
        
        log_activity(username, "LOGIN", "Successful login")
        
        response = JSONResponse({
            "success": True,
            "message": f"Welcome {user['full_name']}!",
            "redirect": "/"
        })
        
        # Définir le cookie de session
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=24*60*60,  # 24 heures
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": str(e)}, 
            status_code=401
        )

@app.post("/api/logout")
async def logout(request: Request):
    """Déconnexion utilisateur"""
    session_token = request.cookies.get("session_token")
    
    if session_token and session_token in active_sessions:
        user = active_sessions[session_token]
        log_activity(user["username"], "LOGOUT", "User logged out")
        del active_sessions[session_token]
    
    response = JSONResponse({"success": True, "redirect": "/"})
    response.delete_cookie("session_token")
    return response

@app.get("/api/logs-stats")
async def get_logs_statistics(session_token: Optional[str] = Cookie(None)):
    """Statistiques sur les logs (admins seulement)"""
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from user import get_logs_stats
    stats = get_logs_stats()
    
    return {
        "success": True,
        "stats": stats
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), 
                     file_type: str = Form(...),
                     session_token: Optional[str] = Cookie(None)):
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    log_activity(current_user["username"], "FILE_UPLOAD", f"Uploaded {file.filename} as {file_type}")
    try:
        # MONITORING INITIAL
        process = psutil.Process(os.getpid())
        memory_start = process.memory_info().rss / 1024 / 1024
        logger.info(f"Mémoire avant upload {file_type}: {memory_start:.1f} MB")

        logger.info(f"Upload reçu: {file.filename}, type: {file_type}")
        
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Format non supporté: {file_extension}"
            )

        # Lire le contenu en mémoire
        contents = await file.read()
        file_size = len(contents)
        
        # TRAITEMENT DIRECT EN MÉMOIRE
        try:
            df, file_info = convert_file_content_to_dataframe(contents, file.filename)
            logger.info(f"Fichier traité en mémoire: {file_info}")
            
        except Exception as e:
            del contents
            raise HTTPException(status_code=422, detail=f"Erreur lecture: {str(e)}")
        
        # Sauvegarder les infos AVANT filtrage
        original_rows = len(df)
        original_columns = len(df.columns)
        
        # Vérifier les colonnes
        missing_columns = [col for col in ALL_REQUIRED_COLUMNS if col not in df.columns]

        # Filtrer seulement les lignes nécessaires
        df_filtered = df[df["Top Conso"] == "O"].copy() if "Top Conso" in df.columns else df.copy()

        # OPTIMISATION MÉMOIRE - Ne garder que les colonnes utiles
        required_cols = ["Top Conso", "Réaffectation", "Groupe De Produit", "Nominal Value", 
                        "LCR_ECO_GROUPE_METIERS", "LCR_ECO_IMPACT_LCR", "Métier", "Sous-Métier"]
        available_cols = [col for col in required_cols if col in df_filtered.columns]
        df_minimal = df_filtered[available_cols].copy()

        # Optimiser les types de données
        for col in df_minimal.select_dtypes(include=['float64']):
            df_minimal[col] = pd.to_numeric(df_minimal[col], downcast='float')

        # LIBÉRATION MÉMOIRE IMMÉDIATE
        del df_filtered
        del df
        del contents
        import gc
        gc.collect()

        # Diagnostic mémoire
        logger.info(f"DataFrame optimisé: {df_minimal.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
        logger.info(f"Shape finale: {df_minimal.shape}")

        # Stocker le DataFrame optimisé
        file_session["files"][file_type] = {
            "dataframe": df_minimal,  # DataFrame optimisé
            "original_name": file.filename,
            "file_format": file_info['format'],
            "encoding": file_info.get('encoding'),
            "delimiter": file_info.get('delimiter'),
            "rows": len(df_minimal),
            "columns": len(df_minimal.columns),
            "upload_time": datetime.now().isoformat(),
            "missing_columns": missing_columns
        }

        # MONITORING FINAL
        memory_end = process.memory_info().rss / 1024 / 1024
        logger.info(f"Mémoire après upload {file_type}: {memory_end:.1f} MB (diff: +{memory_end-memory_start:.1f} MB)")
        
        return {
            "success": True,
            "message": f"Fichier {file_type} traité en mémoire ({file_info['format']})",
            "filename": file.filename,
            "format": file_info['format'],
            "encoding": file_info.get('encoding'),
            "delimiter": file_info.get('delimiter'),
            "rows": original_rows,
            "columns": original_columns,
            "missing_columns": missing_columns,
            "file_size": file_size,
            "processing": "in_memory_optimized"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    

@app.get("/api/logs")
async def get_activity_logs(session_token: Optional[str] = Cookie(None), limit: int = 100):
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logs = get_logs(limit)
    return {
        "success": True,
        "logs": logs,
        "total": len(logs)
    }

@app.get("/api/users")
async def get_users_list(session_token: Optional[str] = Cookie(None)):
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = [
        {
            "username": user["username"],
            "full_name": user["full_name"], 
            "role": user["role"],
            "created_at": user["created_at"]
        }
        for user in USERS_DB.values()
    ]
    
    return {
        "success": True,
        "users": users
    }

@app.get("/api/uploaded-documents")
async def get_uploaded_documents():
    """
    Récupère la liste détaillée des documents uploadés
    """
    documents = []
    for doc in chatbot_session.get("uploaded_documents", []):
        documents.append({
            "filename": doc["filename"],
            "upload_time": doc["upload_time"],
            "size": doc["size"]
        })
    
    return {
        "success": True,
        "documents": documents,
        "count": len(documents)
    }


@app.post("/api/cleanup-memory")
async def cleanup_memory_endpoint(session_token: Optional[str] = Cookie(None)):
    """Endpoint pour nettoyer la mémoire manuellement"""
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024
        
        cleanup_session_memory()
        
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_freed = memory_before - memory_after
        
        log_activity(current_user["username"], "MEMORY_CLEANUP", f"Freed {memory_freed:.1f} MB")
        
        return {
            "success": True,
            "message": f"Memory cleaned: {memory_freed:.1f} MB freed",
            "memory_before": memory_before,
            "memory_after": memory_after
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")
    
    
def cleanup_session_memory():
    """Nettoie la mémoire des DataFrames de session"""
    try:
        if "files" in file_session:
            for file_type in list(file_session["files"].keys()):
                if file_type in file_session["files"] and "dataframe" in file_session["files"][file_type]:
                    del file_session["files"][file_type]["dataframe"]
                    logger.info(f"DataFrame {file_type} supprimé de la session")
        
        # Nettoyage complet
        file_session["files"].clear()
        
        import gc
        gc.collect()
        
        # Vérifier la mémoire après nettoyage
        process = psutil.Process(os.getpid())
        memory_after = process.memory_info().rss / 1024 / 1024
        logger.info(f"Mémoire après nettoyage complet: {memory_after:.1f} MB")
        
    except Exception as e:
        logger.warning(f"Erreur nettoyage mémoire: {e}")

@app.post("/api/analyze")
async def analyze_files(session_token: Optional[str] = Cookie(None)):
    # Vérifier l'authentification
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Logger l'activité
    log_activity(current_user["username"], "ANALYSIS", "Started LCR analysis")
    try:
        logger.info("Début de l'analyse depuis DataFrames en mémoire")
        
        # Vérification de la présence des deux fichiers
        if len(file_session.get("files", {})) < 2:
            raise HTTPException(status_code=400, detail="Les deux fichiers sont requis")
        
        if "j" not in file_session["files"] or "jMinus1" not in file_session["files"]:
            raise HTTPException(status_code=400, detail="Fichiers manquants")
        
        # Récupérer les DataFrames directement depuis la session
        dataframes = {}
        for file_type, file_info in file_session["files"].items():
            df = file_info["dataframe"]  # DataFrame déjà en mémoire
            dataframes[file_type] = df
            logger.info(f"{file_type}: {len(df)} lignes (depuis mémoire)")
        
        # Analyses
        balance_sheet_results = create_balance_sheet_pivot_table(dataframes)
        consumption_results = create_consumption_analysis_grouped_only(dataframes)
        
        logger.info("Analyses terminées (traitement mémoire)")

        # SAUVEGARDER LE CONTEXTE CHATBOT AVANT LA RÉPONSE
        chatbot_session["context_data"] = {
            "balance_sheet": balance_sheet_results,
            "consumption": consumption_results,
            "analysis_timestamp": datetime.now().isoformat(),
            "raw_dataframes_info": {
                file_type: {
                    "shape": [len(df), len(df.columns)],
                    "columns": df.columns.tolist(),
                    "sample_data": df.head(3).to_dict('records') if len(df) > 0 else [],
                    "file_info": file_session["files"][file_type]
                }
                for file_type, df in dataframes.items()
            }
        }

        logger.info("Analyses ET contexte chatbot terminés - tout est prêt")

        # MONITORING MÉMOIRE
        process = psutil.Process(os.getpid())
        memory_analysis = process.memory_info().rss / 1024 / 1024
        logger.info(f"Mémoire après analyse complète: {memory_analysis:.1f} MB")

        return {
            "success": True,
            "message": "Analyses terminées avec contexte chatbot prêt",
            "timestamp": datetime.now().isoformat(),
            "context_ready": True,  
            "results": {
                "balance_sheet": balance_sheet_results,
                "consumption": consumption_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")
    

@app.post("/api/chat")
async def chat_with_ai(request: Request, session_token: Optional[str] = Cookie(None)):
    """
    Endpoint pour le chatbot IA
    """
    # Vérifier l'authentification
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        user_message = data.get("message", "")
        
        if not user_message.strip():
            raise HTTPException(status_code=400, detail="Message vide")
        
        # NOUVEAU LOG : Message envoyé à l'IA
        log_activity(current_user["username"], "CHAT_MESSAGE", f"Sent message to AI: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
        
        # Préparer le contexte complet avec historique
        context_prompt = prepare_conversation_context()
        
        # Obtenir la réponse de l'IA
        ai_response = llm_connector.get_llm_response(
            user_prompt=user_message,
            context_prompt=context_prompt,
            modelID="gpt-4o-mini-2024-07-18",
            temperature=0.1
        )
        
        # Sauvegarder la conversation
        chatbot_session["messages"].append({
            "type": "user",
            "message": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        chatbot_session["messages"].append({
            "type": "assistant",
            "message": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "response": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur chatbot: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur chatbot: {str(e)}")

@app.get("/api/context-status")
async def get_context_status():
    """Vérifie si le contexte du chatbot est prêt"""
    has_context = bool(chatbot_session.get("context_data"))
    context_keys = list(chatbot_session.get("context_data", {}).keys()) if has_context else []
    
    return {
        "context_ready": has_context,
        "context_keys": context_keys,
        "timestamp": datetime.now().isoformat(),
        "analysis_timestamp": chatbot_session.get("context_data", {}).get("analysis_timestamp")
    }


@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...), session_token: Optional[str] = Cookie(None)):
    """
    Upload de documents pour le contexte du chatbot
    """
    # Vérifier l'authentification
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # NOUVEAU LOG : Document uploadé pour contexte
        log_activity(current_user["username"], "DOCUMENT_UPLOAD", f"Uploaded context document: {file.filename}")
        
        contents = await file.read()
        
        # Traiter selon le type de fichier
        if file.filename.endswith('.txt'):
            text_content = contents.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            # Vous devrez installer PyPDF2 : pip install PyPDF2
            import PyPDF2
            from io import BytesIO
            pdf_reader = PyPDF2.PdfReader(BytesIO(contents))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text()
        else:
            text_content = contents.decode('utf-8', errors='ignore')
        
        # Sauvegarder le document
        doc_data = {
            "filename": file.filename,
            "content": text_content,
            "upload_time": datetime.now().isoformat(),
            "size": len(contents)
        }
        
        chatbot_session["uploaded_documents"].append(doc_data)
        
        return {
            "success": True,
            "message": f"Document {file.filename} ajouté au contexte",
            "filename": file.filename,
            "size": len(contents)
        }
        
    except Exception as e:
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/view-report")
async def view_current_report(session_token: Optional[str] = Cookie(None)):
    """Affiche le dernier rapport généré"""
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Vérifier qu'une analyse existe
        if not chatbot_session.get("context_data"):
            raise HTTPException(status_code=400, detail="No analysis available")
        
        # Générer le rapport à la volée
        last_ai_response = None
        if chatbot_session.get("messages"):
            ai_messages = [msg for msg in chatbot_session["messages"] if msg["type"] == "assistant"]
            if ai_messages:
                last_ai_response = ai_messages[-1]["message"]
        
        generator = ReportGenerator(
            analysis_results={
                "balance_sheet": chatbot_session["context_data"].get("balance_sheet"),
                "consumption": chatbot_session["context_data"].get("consumption")
            },
            last_ai_response=last_ai_response
        )
        
        # Capturer graphiques et générer HTML
        generator.chart_images = generator.capture_charts_with_html2image()
        html_content = generator.generate_print_html()
        
        # Retourner directement le HTML
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"<h1>Erreur génération rapport</h1><p>{str(e)}</p>")
    

def prepare_analysis_context() -> str:
    """
    Prépare le contexte détaillé depuis les données sauvegardées
    """
    context_parts = []
    
    # Contexte métier de base
    context_parts.append("CONTEXTE MÉTIER:")
    context_parts.append("- Application d'analyse LCR (Liquidity Coverage Ratio) pour banque")
    context_parts.append("- Analyse Balance Sheet (ACTIF/PASSIF) en milliards d'euros")
    context_parts.append("- Analyse Consumption par groupes métiers en milliards")
    context_parts.append("- Comparaison J vs J-1 (aujourd'hui vs hier)")
    
    # Données d'analyse si disponibles
    if chatbot_session.get("context_data"):
        data = chatbot_session["context_data"]
        
        context_parts.append(f"\nANALYSE EFFECTUÉE LE : {data.get('analysis_timestamp', 'Inconnue')}")
        
        # Balance Sheet
        if data.get("balance_sheet") and not data["balance_sheet"].get("error"):
            bs = data["balance_sheet"]
            context_parts.append("\n=== BALANCE SHEET RESULTS ===")
            context_parts.append(f"Titre: {bs.get('title', 'Balance Sheet')}")
            
            if bs.get("variations"):
                context_parts.append("Variations détaillées:")
                for category, var_data in bs["variations"].items():
                    context_parts.append(f"- {category}: D-1 = {var_data['j_minus_1']} Md€, D = {var_data['j']} Md€")
                    context_parts.append(f"  → Variation = {var_data['variation']} Md€")
            
            if bs.get("summary"):
                context_parts.append(f"Résumé exécutif: {bs['summary']}")
        
        # Consumption
        if data.get("consumption") and not data["consumption"].get("error"):
            cons = data["consumption"]
            context_parts.append("\n=== CONSUMPTION LCR RESULTS ===")
            context_parts.append(f"Titre: {cons.get('title', 'Consumption Analysis')}")
            
            # Variation globale
            if cons.get("variations", {}).get("global"):
                global_var = cons["variations"]["global"]
                context_parts.append(f"Consumption total: D-1 = {global_var['j_minus_1']} Md, D = {global_var['j']} Md")
                context_parts.append(f"Variation globale = {global_var['variation']} Md")
            
            # Variations par groupe métier
            if cons.get("variations", {}).get("by_groupe_metiers"):
                context_parts.append("\nVariations par groupe métier:")
                for groupe, var_data in cons["variations"]["by_groupe_metiers"].items():
                    if abs(var_data["variation"]) > 0.01:  # Seulement les variations > 10M€
                        context_parts.append(f"- {groupe}: {var_data['variation']} Md (D-1: {var_data['j_minus_1']}, D: {var_data['j']})")
            
            # Analyses textuelles
            if cons.get("analysis_text"):
                context_parts.append(f"\nAnalyse principale: {cons['analysis_text']}")
            
            if cons.get("metier_detailed_analysis"):
                context_parts.append(f"Analyse détaillée: {cons['metier_detailed_analysis']}")
            
            # Groupes significatifs
            if cons.get("significant_groups"):
                context_parts.append(f"Groupes avec variations significatives: {', '.join(cons['significant_groups'])}")
        
        # Informations sur les fichiers source
        if data.get("raw_dataframes_info"):
            context_parts.append("\n=== FICHIERS SOURCE ===")
            for file_type, info in data["raw_dataframes_info"].items():
                context_parts.append(f"Fichier {file_type}: {info['shape'][0]} lignes, {info['shape'][1]} colonnes")
                context_parts.append(f"Colonnes: {', '.join(info['columns'])}")
                if info.get("sample_data"):
                    context_parts.append("Échantillon de données:")
                    for i, row in enumerate(info["sample_data"][:2]):  # 2 premières lignes
                        context_parts.append(f"  Ligne {i+1}: {str(row)[:200]}...")
    
    else:
        context_parts.append("\nAucune analyse disponible - les analyses doivent être lancées d'abord.")
    
    return "\n".join(context_parts)

def prepare_documents_context() -> str:
    """
    Prépare le contexte depuis les documents uploadés
    """
    if not chatbot_session["uploaded_documents"]:
        return ""
    
    context_parts = []
    for doc in chatbot_session["uploaded_documents"]:
        context_parts.append(f"Document: {doc['filename']}")
        context_parts.append(f"Contenu: {doc['content'][:2000]}...")  # Limiter à 2000 chars
        context_parts.append("---")
    
    return "\n".join(context_parts)

def prepare_conversation_context() -> str:
    """
    Prépare le contexte complet incluant analyses + documents + historique
    """
    context_parts = []
    
    # Contexte des analyses
    context_parts.append(prepare_analysis_context())
    
    # Documents uploadés
    docs_context = prepare_documents_context()
    if docs_context:
        context_parts.append(f"\n\nContext Documents:\n{docs_context}")
    
    # Historique de conversation (derniers 10 messages pour éviter de surcharger)
    if chatbot_session["messages"]:
        context_parts.append("\n\nHistory of conversation:")
        for msg in chatbot_session["messages"][-10:]:
            role = "Utilisateur" if msg["type"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['message']}")
        context_parts.append("\n--- End of history of conversation ---")
    
    return "\n".join(context_parts)


@app.get("/api/chat-history")
async def get_chat_history():
    """
    Récupère l'historique des messages du chatbot
    """
    return {
        "success": True,
        "messages": chatbot_session["messages"],
        "documents_count": len(chatbot_session["uploaded_documents"])
    }

@app.delete("/api/chat-clear")
async def clear_chat():
    """
    Vide l'historique du chatbot
    """
    chatbot_session["messages"].clear()
    chatbot_session["uploaded_documents"].clear()
    return {"success": True, "message": "Historique effacé"}

@app.get("/api/chatbot-context")
async def get_chatbot_context():
    """
    Endpoint de debug pour voir le contexte du chatbot
    """
    return {
        "success": True,
        "has_context_data": bool(chatbot_session.get("context_data")),
        "context_keys": list(chatbot_session.get("context_data", {}).keys()),
        "messages_count": len(chatbot_session.get("messages", [])),
        "documents_count": len(chatbot_session.get("uploaded_documents", []))
    }

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
            "title": "1. Balance Sheet",
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
        if category == "ACTIF":
            category_name = "ASSET"
        elif category == "PASSIF": 
            category_name = "LIABILITY"
        else:
            category_name = category  # fallback
        variation = data["variation"]
        if abs(variation) >= 0.1:  # Variations significatives >= 100M€
            direction = "increase" if variation > 0 else "decrease"
            summary_parts.append(f"{category_name}: {direction} of {abs(variation):.2f} Md€")
    
    if summary_parts:
        return f"On {date_str} Natixis' balance sheet presents some variations: {', '.join(summary_parts)}."
    else:
        return f"Balance Sheet on {date_str} - Small variations observed (< 100M€)."


@app.post("/api/export-pdf")
async def export_pdf(session_token: Optional[str] = Cookie(None)):
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Vérifier qu'une analyse existe
    if not chatbot_session.get("context_data"):
        raise HTTPException(status_code=400, detail="No analysis available")
    
    # Retourner juste l'URL de visualisation
    return JSONResponse({
        "success": True,
        "report_url": "/view-report"
    })  
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
    
        return {
            "title": "2. LCR Consumption",
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

            # GARANTIR AU MOINS 2 DRIVERS pour CAS 1
            if len(selected) < 2 and len(aligned) >= 2:
                # Prendre les 2 plus gros drivers alignés
                selected = aligned[:2]
            elif len(selected) < 1 and len(aligned) >= 1:
                # Fallback : au moins 1 driver si disponible
                selected = [aligned[0]]

        # CAS 2 : net ~ 0 -> sortir les vrais movers (IQR) des deux côtés
        else:
            abs_vars = [av for (_, _, av) in items]
            upper = _tukey_upper_threshold(abs_vars)
            movers = [(g, v, av) for (g, v, av) in items if av >= upper]
            movers.sort(key=lambda x: x[2], reverse=True)
            
            # GARANTIR AU MOINS 2 MOVERS pour CAS 2
            if len(movers) < 2 and len(items) >= 2:
                # Prendre les 2 plus grosses variations absolues
                items_sorted = sorted(items, key=lambda x: x[2], reverse=True)
                selected = items_sorted[:2]
            elif len(movers) >= 2:
                selected = movers
            elif len(movers) == 1:
                # 1 mover détecté, ajouter le suivant par taille
                items_sorted = sorted(items, key=lambda x: x[2], reverse=True)
                selected = movers + [item for item in items_sorted if item not in movers][:1]
            else:
                # Aucun mover détecté, prendre les 2 plus gros
                if len(items) >= 2:
                    items_sorted = sorted(items, key=lambda x: x[2], reverse=True)
                    selected = items_sorted[:2]
                elif len(items) == 1:
                    selected = items

        # Mise en forme avec mapping Métier -> Sous-Métier
        significant_variations = []
        for g, v, av in selected:
            sign_sym = "-" if v < 0 else "+"
            
            # Utiliser le mapping pour obtenir le nom complet
            display_name = metier_to_sous_metier.get(g, g)
            
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
    host="0.0.0.0",
    port=8000,
    reload=False,
    log_level="info",
    timeout_keep_alive=900,  # 15 minutes
    limit_max_requests=100,  # Réduire pour forcer le recyclage
    workers=1  # Une seule instance pour éviter la duplication mémoire
    )