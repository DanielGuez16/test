#!/usr/bin/env python3
#run.py
"""
Steering ALM Metrics - Version avec Templates
============================================

Application FastAPI utilisant un système de templates Jinja2
pour séparer la logique métier de la présentation.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import uvicorn
import logging
from pathlib import Path
from datetime import datetime
import io
import chardet
from typing import Optional
import psutil
import os
from user import authenticate_user, log_activity, get_logs, USERS_DB
import secrets

from llm_connector import LLMConnector
from report_generator import ReportGenerator
from data_persistence import init_database, save_table_result, get_historical_data

# Initialiser le connecteur LLM
llm_connector = LLMConnector()

# Formats supportés
SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', '.tsv', '.txt']

# Variables globales pour la session chatbot
chatbot_session = {
    "messages": [],
    "context_data": {},
    "uploaded_documents": []
}
# Variables globales pour la session (en production: utiliser une base de données)
file_session = {"files": {}}
# Session utilisateur global (en production: vraies sessions SSH si possible)
active_sessions = {}

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création des dossiers requis
required_dirs = ["data", "templates", "static", "static/js", "static/css", "static/images"]
for directory in required_dirs:
    Path(directory).mkdir(exist_ok=True)

required_cols = ["Top Conso", "LCR_Catégorie", "LCR_Template Section 1", "Libellé Client", 
                "LCR_Assiette Pondérée", "LCR_ECO_GROUPE_METIERS", "Sous-Métier", "Produit", 
                "LCR_ECO_IMPACT_LCR", "SI Remettant", "Commentaire", "Date d'arrêté"]
                
# Création de l'application FastAPI
app = FastAPI(title="Steering ALM Metrics", version="2.0.0")

# Initialiser la base de données historique
init_database()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# =========================== FONCTIONS UTILITAIRES ===========================


def generate_session_token():
    return secrets.token_urlsafe(32)

def get_current_user_from_session(session_token: Optional[str] = Cookie(None)):
    """Récupère l'utilisateur depuis le token de session"""
    if not session_token or session_token not in active_sessions:
        return None
    return active_sessions[session_token]

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


# ========================== ENDPOINTS EXPORT ===========================  


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


# =========================== ENDPOINTS AUTHENTIFICATION ===========================


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


# =========================== ENDPOINTS FICHIERS ===========================


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

        # Filtrer seulement les lignes nécessaires
        df_filtered = df[df["Top Conso"] == "O"].copy() if "Top Conso" in df.columns else df.copy()

        # OPTIMISATION MÉMOIRE - Ne garder que les colonnes utiles
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
            "file_size": file_size,
            "processing": "in_memory_optimized"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    
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


# ========================== ENDPOINTS ANALYSE ===========================


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
        
        # Vérification de la présence des TROIS fichiers
        if len(file_session.get("files", {})) < 3:
            raise HTTPException(status_code=400, detail="Les trois fichiers sont requis")
        
        if "j" not in file_session["files"] or "jMinus1" not in file_session["files"] or "mMinus1" not in file_session["files"]:
            raise HTTPException(status_code=400, detail="Fichiers manquants")
        
        # Récupérer les DataFrames directement depuis la session
        dataframes = {}
        for file_type, file_info in file_session["files"].items():
            df = file_info["dataframe"]
            dataframes[file_type] = df
            logger.info(f"{file_type}: {len(df)} lignes (depuis mémoire)")

        # Nouvelles analyses
        buffer_results = create_buffer_table(dataframes)
        summary_results = create_summary_table(dataframes)  # NOUVEAU
        consumption_results = create_consumption_table(dataframes)
        resources_results = create_resources_table(dataframes)
        cappage_results = create_cappage_table(dataframes)
        buffer_nco_results = create_buffer_nco_table(dataframes)
        consumption_resources_results = create_consumption_resources_table(dataframes)
        
        logger.info("Analyses terminées (nouveaux tableaux)")

        # SAUVEGARDER LE CONTEXTE CHATBOT
        chatbot_session["context_data"] = {
            "buffer": buffer_results,
            "summary": summary_results,  # NOUVEAU
            "consumption": consumption_results,
            "resources": resources_results,
            "cappage": cappage_results,
            "buffer_nco": buffer_nco_results,
            "consumption_resources": consumption_resources_results,
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

        # ========= SAUVEGARDE HISTORIQUE =========
        try:
            # Extraire la date d'arrêté du fichier J
            analysis_date = None
            if "j" in file_session["files"]:
                df_j = file_session["files"]["j"]["dataframe"]
                if "Date d'arrêté" in df_j.columns:
                    # Prendre la première date d'arrêté
                    analysis_date = str(df_j["Date d'arrêté"].iloc[0])
            
            if analysis_date:
                # Sauvegarder uniquement les 5 tableaux concernés
                save_table_result(analysis_date, "cappage", cappage_results)
                save_table_result(analysis_date, "buffer_nco_buffer", 
                                buffer_nco_results.get("data", {}).get("j", {}).get("buffer_pivot_data", []))
                save_table_result(analysis_date, "buffer_nco_nco",
                                buffer_nco_results.get("data", {}).get("j", {}).get("nco_pivot_data", []))
                save_table_result(analysis_date, "consumption_resources_consumption",
                                consumption_resources_results.get("data", {}).get("j", {}).get("consumption_data", []))
                save_table_result(analysis_date, "consumption_resources_resources",
                                consumption_resources_results.get("data", {}).get("j", {}).get("resources_data", []))
                
                logger.info(f"✅ Historique sauvegardé pour {analysis_date}")
            else:
                logger.warning("⚠️ Impossible de trouver la date d'arrêté")
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur sauvegarde historique: {e}")
        # =========================================

        return {
            "success": True,
            "message": "Analyses terminées avec nouveaux tableaux",
            "timestamp": datetime.now().isoformat(),
            "context_ready": True,  
            "results": {
                "buffer": buffer_results,
                "summary": summary_results,  # NOUVEAU
                "consumption": consumption_results,
                "resources": resources_results,
                "cappage": cappage_results,
                "buffer_nco": buffer_nco_results,
                "consumption_resources": consumption_resources_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

@app.get("/api/analyze-historical/{table_name}")
async def get_table_historical(table_name: str, days_back: int = 10, session_token: Optional[str] = Cookie(None)):
    """Récupère l'historique d'un tableau spécifique"""
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Récupérer l'historique depuis la DB
        historical_data = get_historical_data(table_name, days_back)
        
        if not historical_data:
            return {
                "success": False,
                "message": f"Aucun historique trouvé pour {table_name}"
            }
        
        # Transformer en format utilisable par le frontend
        dates = [item[0] for item in historical_data]
        data_by_date = {item[0]: item[1] for item in historical_data}
        
        return {
            "success": True,
            "table_name": table_name,
            "dates": dates,
            "data_by_date": data_by_date,
            "total_days": len(dates)
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération historique {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/analyze-consumption-resources")
async def analyze_consumption_resources(request: Request, session_token: Optional[str] = Cookie(None)):
    """
    Génère une analyse IA des données Consumption & Resources
    """
    # Vérifier l'authentification
    current_user = get_current_user_from_session(session_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        context_data = data.get("context_data", {})
        
        # Préparer le prompt d'analyse
        analysis_prompt = prepare_consumption_resources_analysis_prompt(context_data)
        
        # Obtenir l'analyse de l'IA
        ai_analysis = llm_connector.get_llm_response(
            user_prompt="Analyze the Consumption and Resources data provided in the context. Focus on key trends, variations between periods, and strategic insights.",
            context_prompt=analysis_prompt,
            modelID="gpt-4o-mini-2024-07-18",
            temperature=0.3
        )
        
        # Logger l'activité
        log_activity(current_user["username"], "AI_ANALYSIS", "Generated Consumption & Resources analysis")
        
        return {
            "success": True,
            "analysis": ai_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse Consumption & Resources: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analyse: {str(e)}")

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


# ========================== ENDPOINTS CHATBOT ===========================


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


# ========================== ENDPOINTS ADMIN ===========================


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


# ========================== ENDPOINTS EXPORT ===========================  


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
    


# ========================== FONCTIONS BUFFER TABLE ===========================


def create_buffer_table(dataframes):
    """
    Crée le tableau BUFFER avec structure TCD Excel
    Filtre: LCR_Catégorie = "1- Buffer"
    Lignes: LCR_Template Section 1 + Libellé Client (hiérarchie)
    Valeurs: D (Today), Variation D vs D-1, Variation D vs M-1
    """
    try:
        logger.info("📊 Création du tableau BUFFER - Style TCD Excel avec variations")
        
        # Vérification que nous avons les trois fichiers nécessaires
        if not all(key in dataframes for key in ['j', 'jMinus1', 'mMinus1']):
            return {
                "title": "BUFFER - Erreur",
                "error": "Les trois fichiers (J, J-1, M-1) sont requis pour calculer les variations"
            }
        
        buffer_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement BUFFER TCD pour {file_type}")
            
            # Vérification des colonnes requises
            buffer_cols = ["Top Conso", "LCR_Catégorie", "LCR_Template Section 1", 
                          "Libellé Client", "LCR_Assiette Pondérée"]
            missing_cols = [col for col in buffer_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour BUFFER {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données - TCD Style
            df_filtered = df[df["Top Conso"] == "O"].copy()
            df_filtered = df_filtered[df_filtered["LCR_Catégorie"] == "1- Buffer"].copy()
            
            logger.info(f"📋 Après filtrage BUFFER TCD: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée BUFFER pour {file_type}")
                buffer_results[file_type] = {
                    "pivot_data": [],
                    "sections": []
                }
                continue
            
            # Préparation des données
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["LCR_Template Section 1"] = df_filtered["LCR_Template Section 1"].astype(str).str.strip()
            df_filtered["Libellé Client"] = df_filtered["Libellé Client"].astype(str).str.strip()
            
            # Grouper les données pour créer la structure pivot
            pivot_data = []
            sections = sorted(df_filtered["LCR_Template Section 1"].unique())
            
            for section in sections:
                section_data = df_filtered[df_filtered["LCR_Template Section 1"] == section]
                clients = sorted(section_data["Libellé Client"].unique())
                
                # Calculer les totaux de section pour toutes les périodes
                section_total_j = section_data["LCR_Assiette Pondérée"].sum() / 1_000_000_000
                
                # Données clients détaillées
                client_details = []
                
                for client in clients:
                    client_data = section_data[section_data["Libellé Client"] == client]
                    value_j = client_data["LCR_Assiette Pondérée"].sum() / 1_000_000_000
                    
                    client_details.append({
                        "client": client,
                        "value_j": float(value_j),
                        "is_detail": True
                    })
                
                # Ajouter le groupe de section avec ses détails
                pivot_data.append({
                    "section": section,
                    "client_details": client_details,
                    "section_total_j": float(section_total_j),
                    "is_section_group": True
                })
            
            buffer_results[file_type] = {
                "pivot_data": pivot_data,
                "sections": sections
            }
            
            logger.info(f"✅ BUFFER TCD {file_type}: {len(pivot_data)} sections")
        
        # Calculer les variations entre les périodes
        if 'j' in buffer_results and 'jMinus1' in buffer_results and 'mMinus1' in buffer_results:
            buffer_results_with_variations = calculate_buffer_variations(
                buffer_results['j'], 
                buffer_results['jMinus1'], 
                buffer_results['mMinus1']
            )
        else:
            buffer_results_with_variations = buffer_results.get('j', {"pivot_data": [], "sections": []})
        
        return {
            "title": "BUFFER - TCD Analysis with Variations",
            "data": buffer_results_with_variations,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "tcd_config": {
                    "filters": {"lcr_categorie": "1- Buffer", "top_conso": "O"},
                    "rows": ["LCR_Template Section 1", "Libellé Client"],
                    "values": ["D (Today) Bn €", "Variation D vs D-1", "Variation D vs M-1"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau BUFFER TCD: {e}")
        return {
            "title": "BUFFER - Erreur",
            "error": str(e)
        }

def calculate_buffer_variations(data_j, data_j1, data_m1):
    """
    Calcule les variations pour le tableau BUFFER
    """
    try:
        # Créer des mappings pour les recherches rapides
        j1_map = {}
        m1_map = {}
        
        # Mapper les données J-1
        for section_group in data_j1.get("pivot_data", []):
            section = section_group["section"]
            for client_detail in section_group.get("client_details", []):
                key = f"{section}|{client_detail['client']}"
                j1_map[key] = client_detail["value_j"]
        
        # Mapper les données M-1
        for section_group in data_m1.get("pivot_data", []):
            section = section_group["section"]
            for client_detail in section_group.get("client_details", []):
                key = f"{section}|{client_detail['client']}"
                m1_map[key] = client_detail["value_j"]
        
        # Calculer les variations pour les données J
        result_data = {"pivot_data": [], "sections": data_j.get("sections", [])}
        
        for section_group in data_j.get("pivot_data", []):
            section = section_group["section"]
            
            # Calculer les variations pour chaque client
            client_details_with_variations = []
            section_total_j = 0
            section_total_j1 = 0
            section_total_m1 = 0
            
            for client_detail in section_group.get("client_details", []):
                client = client_detail["client"]
                key = f"{section}|{client}"
                
                value_j = client_detail["value_j"]
                value_j1 = j1_map.get(key, 0)
                value_m1 = m1_map.get(key, 0)
                
                variation_daily = value_j - value_j1
                variation_monthly = value_j - value_m1
                
                # Cumuler pour les totaux de section
                section_total_j += value_j
                section_total_j1 += value_j1
                section_total_m1 += value_m1
                
                client_details_with_variations.append({
                    "client": client,
                    "value_j": float(value_j),
                    "variation_daily": float(variation_daily),
                    "variation_monthly": float(variation_monthly),
                    "is_detail": True
                })
            
            # Calculer les variations de section
            section_variation_daily = section_total_j - section_total_j1
            section_variation_monthly = section_total_j - section_total_m1
            
            result_data["pivot_data"].append({
                "section": section,
                "client_details": client_details_with_variations,
                "section_total_j": float(section_total_j),
                "section_variation_daily": float(section_variation_daily),
                "section_variation_monthly": float(section_variation_monthly),
                "is_section_group": True
            })
        
        return result_data
        
    except Exception as e:
        logger.error(f"Erreur calcul variations BUFFER: {e}")
        return data_j
    

# ========================== FONCTIONS SUMMARY TABLE ===========================


def create_summary_table(dataframes):
    """
    Crée le tableau de synthèse sans titre avec comparaison des deux fichiers
    """
    try:
        logger.info("📊 Création du tableau de synthèse")
        
        summary_results = {}
        
        # Vérification que nous avons les deux fichiers
        if "j" not in dataframes or "jMinus1" not in dataframes:
            logger.warning("⚠️ Les deux fichiers sont requis pour le tableau de synthèse")
            return {
                "title": "Summary Table",
                "error": "Les deux fichiers sont requis"
            }
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement synthèse pour {file_type}")
            
            # Vérification des colonnes requises
            summary_cols = ["Top Conso", "Date d'arrêté", "LCR_Assiette Pondérée", "LCR_ECO_IMPACT_LCR"]
            missing_cols = [col for col in summary_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour synthèse {file_type}: {missing_cols}")
                continue
            
            # Filtrage Top Conso = "O"
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            logger.info(f"📋 Après filtrage Top Conso: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée pour synthèse {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            df_filtered["LCR_ECO_IMPACT_LCR"] = pd.to_numeric(
                df_filtered["LCR_ECO_IMPACT_LCR"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage du champ date
            df_filtered["Date d'arrêté"] = df_filtered["Date d'arrêté"].astype(str).str.strip()
            
            # Obtenir les dates uniques pour ce fichier
            dates = sorted(df_filtered["Date d'arrêté"].unique())
            
            # Calculer les sommes par date
            summary_data = []
            
            for date in dates:
                date_data = df_filtered[df_filtered["Date d'arrêté"] == date]
                
                sum_assiette = float(date_data["LCR_Assiette Pondérée"].sum()) / 1_000_000_000
                sum_impact = float(date_data["LCR_ECO_IMPACT_LCR"].sum()) / 1_000_000_000
                sum_difference = sum_assiette - sum_impact
                
                summary_data.append({
                    "date": date,
                    "sum_assiette": sum_assiette,
                    "sum_impact": sum_impact,
                    "sum_difference": sum_difference,
                    "file_type": file_type
                })
            
            summary_results[file_type] = summary_data
            logger.info(f"✅ Synthèse {file_type}: {len(summary_data)} dates")
        
        return {
            "title": "",  # Pas de titre
            "data": summary_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau synthèse: {e}")
        return {
            "title": "Summary Table - Erreur",
            "error": str(e)
        }
    

# ========================== FONCTIONS CONSUMPTION TABLE ===========================


def create_consumption_table(dataframes):
    """
    Crée le tableau CONSUMPTION avec filtres spécifiques
    """
    try:
        logger.info("📊 Création du tableau CONSUMPTION")
        
        consumption_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement CONSUMPTION pour {file_type}")
            
            # Vérification des colonnes requises
            consumption_cols = ["Top Conso", "LCR_ECO_GROUPE_METIERS", "Sous-Métier", 
                              "Produit", "LCR_ECO_IMPACT_LCR"]
            missing_cols = [col for col in consumption_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour CONSUMPTION {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            # Filtres spécifiques CONSUMPTION
            allowed_groupes = ["A&WM & Insurance", "CIB Financing", "CIB Markets", "GLOBAL TRADE", "Other Consumption"]
            df_filtered = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(allowed_groupes)].copy()
            
            excluded_sous_metier = ["GT TREASURY SOLUTIONS", "GT GROUP SERVICES"]
            df_filtered = df_filtered[~df_filtered["Sous-Métier"].isin(excluded_sous_metier)].copy()
            
            excluded_produit = ["SIGHT DEPOSIT MIRROR", "SIGHT FINANCING MIRROR"]
            df_filtered = df_filtered[~df_filtered["Produit"].isin(excluded_produit)].copy()
            
            logger.info(f"📋 Après filtrage CONSUMPTION: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée CONSUMPTION pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_ECO_IMPACT_LCR"] = pd.to_numeric(
                df_filtered["LCR_ECO_IMPACT_LCR"], errors='coerce'
            ).fillna(0)

            # Groupement par LCR_ECO_GROUPE_METIERS
            grouped = df_filtered.groupby("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR"].sum().reset_index()
            grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)

            # Convertir en dictionnaire avec types Python natifs
            consumption_results[file_type] = [
                {
                    "LCR_ECO_GROUPE_METIERS": str(row["LCR_ECO_GROUPE_METIERS"]),
                    "LCR_ECO_IMPACT_LCR": float(row["LCR_ECO_IMPACT_LCR"]),
                    "LCR_ECO_IMPACT_LCR_Bn": float(row["LCR_ECO_IMPACT_LCR_Bn"])
                }
                for _, row in grouped.iterrows()
            ]
            logger.info(f"✅ CONSUMPTION {file_type}: {len(grouped)} groupes")
        
        return {
            "title": "CONSUMPTION",
            "data": consumption_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "groupe_metiers": allowed_groupes,
                    "excluded_sous_metier": excluded_sous_metier,
                    "excluded_produit": excluded_produit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau CONSUMPTION: {e}")
        return {
            "title": "CONSUMPTION - Erreur",
            "error": str(e)
        }


# ========================== FONCTIONS RESOURCES TABLE ===========================


def create_resources_table(dataframes):
    """
    Crée le tableau RESOURCES avec filtres spécifiques
    """
    try:
        logger.info("📊 Création du tableau RESOURCES")
        
        resources_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement RESOURCES pour {file_type}")
            
            # Vérification des colonnes requises
            resources_cols = ["Top Conso", "LCR_ECO_GROUPE_METIERS", "Sous-Métier", 
                            "Produit", "LCR_ECO_IMPACT_LCR"]
            missing_cols = [col for col in resources_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour RESOURCES {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            # Filtres spécifiques RESOURCES
            allowed_groupes = ["GLOBAL TRADE", "Other Contribution", "Treasury"]
            df_filtered = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(allowed_groupes)].copy()
            
            excluded_sous_metier = ["GT GROUP SERVICES", "GT COMMODITY", "GT TRADE FINANCE", "SYN GLOBAL TRADE"]
            df_filtered = df_filtered[~df_filtered["Sous-Métier"].isin(excluded_sous_metier)].copy()
            
            excluded_produit = ["SIGHT DEPOSIT MIRROR", "SIGHT FINANCING MIRROR"]
            df_filtered = df_filtered[~df_filtered["Produit"].isin(excluded_produit)].copy()
            
            logger.info(f"📋 Après filtrage RESOURCES: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée RESOURCES pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_ECO_IMPACT_LCR"] = pd.to_numeric(
                df_filtered["LCR_ECO_IMPACT_LCR"], errors='coerce'
            ).fillna(0)
            
            # Groupement par LCR_ECO_GROUPE_METIERS
            grouped = df_filtered.groupby("LCR_ECO_GROUPE_METIERS")["LCR_ECO_IMPACT_LCR"].sum().reset_index()
            grouped["LCR_ECO_IMPACT_LCR_Bn"] = (grouped["LCR_ECO_IMPACT_LCR"] / 1_000_000_000).round(3)
            
            # Convertir en dictionnaire avec types Python natifs
            resources_results[file_type] = [
                {
                    "LCR_ECO_GROUPE_METIERS": str(row["LCR_ECO_GROUPE_METIERS"]),
                    "LCR_ECO_IMPACT_LCR": float(row["LCR_ECO_IMPACT_LCR"]),
                    "LCR_ECO_IMPACT_LCR_Bn": float(row["LCR_ECO_IMPACT_LCR_Bn"])
                }
                for _, row in grouped.iterrows()
            ]
            
            logger.info(f"✅ RESOURCES {file_type}: {len(grouped)} groupes")
        
        return {
            "title": "RESOURCES",
            "data": resources_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "groupe_metiers": allowed_groupes,
                    "excluded_sous_metier": excluded_sous_metier,
                    "excluded_produit": excluded_produit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau RESOURCES: {e}")
        return {
            "title": "RESOURCES - Erreur",
            "error": str(e)
        }
    
def prepare_consumption_resources_analysis_prompt(context_data):
    """
    Prépare le prompt d'analyse pour Consumption & Resources
    """
    prompt_parts = []
    
    prompt_parts.append("ANALYSIS CONTEXT: LCR (Liquidity Coverage Ratio) Banking Analysis")
    prompt_parts.append("You are analyzing Consumption and Resources data from a bank's LCR reporting.")
    prompt_parts.append("Values are in billions of euros (Bn €).")
    prompt_parts.append("Data compares D (Today) vs D-1 (Yesterday).")
    prompt_parts.append("")
    
    # Données Consumption
    if context_data.get("consumption_data"):
        prompt_parts.append("=== CONSUMPTION DATA ===")
        consumption_data = context_data["consumption_data"]
        
        if consumption_data.get("j") and consumption_data.get("jMinus1"):
            prompt_parts.append("CONSUMPTION ANALYSIS (Filtered Business Groups):")
            
            # Données D (aujourd'hui)
            prompt_parts.append("\nD (Today) - Consumption by Business Group:")
            for item in consumption_data["j"]:
                prompt_parts.append(f"- {item['LCR_ECO_GROUPE_METIERS']}: {item['LCR_ECO_IMPACT_LCR_Bn']:.3f} Bn €")
            
            # Données D-1 (hier)
            prompt_parts.append("\nD-1 (Yesterday) - Consumption by Business Group:")
            for item in consumption_data["jMinus1"]:
                prompt_parts.append(f"- {item['LCR_ECO_GROUPE_METIERS']}: {item['LCR_ECO_IMPACT_LCR_Bn']:.3f} Bn €")
    
    # Données Resources
    if context_data.get("resources_data"):
        prompt_parts.append("\n=== RESOURCES DATA ===")
        resources_data = context_data["resources_data"]
        
        if resources_data.get("j") and resources_data.get("jMinus1"):
            prompt_parts.append("RESOURCES ANALYSIS (Filtered Business Groups):")
            
            # Données D (aujourd'hui)
            prompt_parts.append("\nD (Today) - Resources by Business Group:")
            for item in resources_data["j"]:
                prompt_parts.append(f"- {item['LCR_ECO_GROUPE_METIERS']}: {item['LCR_ECO_IMPACT_LCR_Bn']:.3f} Bn €")
            
            # Données D-1 (hier)
            prompt_parts.append("\nD-1 (Yesterday) - Resources by Business Group:")
            for item in resources_data["jMinus1"]:
                prompt_parts.append(f"- {item['LCR_ECO_GROUPE_METIERS']}: {item['LCR_ECO_IMPACT_LCR_Bn']:.3f} Bn €")
    
    prompt_parts.append("\n=== ANALYSIS REQUIREMENTS ===")
    prompt_parts.append("Please provide:")
    prompt_parts.append("1. Key variations between D and D-1 for both Consumption and Resources")
    prompt_parts.append("2. Most significant changes by business group")
    prompt_parts.append("3. Strategic insights and potential risk implications")
    prompt_parts.append("4. Summary of net impact on liquidity position")
    prompt_parts.append("Keep the analysis concise but insightful (max 300 words).")
    
    return "\n".join(prompt_parts)


# ========================== FONCTIONS CAPPAGE TABLE ===========================


def create_cappage_table(dataframes):
    """
    Crée le tableau CAPPAGE avec structure TCD Excel style
    Filtre: SI Remettant = SHORT_LCR ou CAPREOS
    Lignes: SI Remettant + Commentaire (hiérarchie)
    Colonnes: Date d'arrêté
    Valeurs: Somme LCR_Assiette Pondérée
    """
    try:
        logger.info("📊 Création du tableau CAPPAGE - Style TCD Excel")
        
        cappage_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement CAPPAGE TCD pour {file_type}")
            
            # Vérification des colonnes requises
            cappage_cols = ["Top Conso", "SI Remettant", "Commentaire", 
                           "Date d'arrêté", "LCR_Assiette Pondérée"]
            missing_cols = [col for col in cappage_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour CAPPAGE {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données - TCD Style
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            # Filtre principal: SI Remettant
            allowed_si_remettant = ["SHORT_LCR", "CAPREOS"]
            df_filtered = df_filtered[df_filtered["SI Remettant"].isin(allowed_si_remettant)].copy()
            
            logger.info(f"📋 Après filtrage CAPPAGE TCD: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée CAPPAGE pour {file_type}")
                cappage_results[file_type] = {
                    "pivot_data": [],
                    "dates": [],
                    "si_remettant_groups": []
                }
                continue
            
            # Préparation des données pour le TCD
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["SI Remettant"] = df_filtered["SI Remettant"].astype(str).str.strip()
            df_filtered["Commentaire"] = df_filtered["Commentaire"].astype(str).str.strip()
            df_filtered["Date d'arrêté"] = df_filtered["Date d'arrêté"].astype(str).str.strip()
            
            # Récupérer toutes les dates uniques (colonnes du TCD)
            dates = sorted(df_filtered["Date d'arrêté"].unique())
            
            # Créer la structure TCD hiérarchique
            pivot_structure = []
            
            # Grouper par SI Remettant (niveau 1 de hiérarchie)
            for si_remettant in allowed_si_remettant:
                si_data = df_filtered[df_filtered["SI Remettant"] == si_remettant]
                
                if len(si_data) == 0:
                    continue
                
                # Sous-groupes par Commentaire (niveau 2 de hiérarchie)
                commentaires = sorted(si_data["Commentaire"].unique())
                
                # Données détaillées par commentaire
                commentaire_details = []
                si_totals_by_date = {}
                
                for commentaire in commentaires:
                    commentaire_data = si_data[si_data["Commentaire"] == commentaire]
                    
                    # Calculer les valeurs par date pour ce commentaire
                    date_values = {}
                    for date in dates:
                        date_total = commentaire_data[
                            commentaire_data["Date d'arrêté"] == date
                        ]["LCR_Assiette Pondérée"].sum()
                        
                        # Conversion en milliards
                        date_values[date] = float(date_total) / 1_000_000_000
                        
                        # Cumuler pour les totaux SI Remettant
                        if date not in si_totals_by_date:
                            si_totals_by_date[date] = 0
                        si_totals_by_date[date] += date_values[date]
                    
                    # Ajouter cette ligne de détail
                    commentaire_details.append({
                        "commentaire": commentaire,
                        "date_values": date_values,
                        "is_detail": True,
                        "total": sum(date_values.values())
                    })
                
                # Ajouter le groupe SI Remettant avec ses détails
                pivot_structure.append({
                    "si_remettant": si_remettant,
                    "commentaire_details": commentaire_details,
                    "si_totals_by_date": si_totals_by_date,
                    "grand_total": sum(si_totals_by_date.values()),
                    "is_si_group": True
                })
            
            cappage_results[file_type] = {
                "pivot_data": pivot_structure,
                "dates": dates,
                "si_remettant_groups": allowed_si_remettant
            }
            
            logger.info(f"✅ CAPPAGE TCD {file_type}: {len(pivot_structure)} groupes SI, {len(dates)} dates")
        
        return {
            "title": "CAPPAGE & Short_LCR - TCD Analysis",
            "data": cappage_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "tcd_config": {
                    "filters": {"si_remettant": allowed_si_remettant, "top_conso": "O"},
                    "rows": ["SI Remettant", "Commentaire"],
                    "columns": ["Date d'arrêté"],
                    "values": "Somme LCR_Assiette Pondérée (Bn €)"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau CAPPAGE TCD: {e}")
        return {
            "title": "CAPPAGE & Short_LCR - Erreur",
            "error": str(e)
        }


# ========================== FONCTIONS BUFFER & NCO TABLE ===========================


def create_buffer_nco_table(dataframes):
    """
    Crée les tableaux BUFFER & NCO avec structure TCD Excel style
    
    Tableau 1 - BUFFER:
    - Filtre: LCR_Catégorie = "1- Buffer"
    - Lignes: LCR_Template Section 1 + Libellé Client (hiérarchie)
    - Colonnes: Date d'arrêté
    - Valeurs: Somme LCR_Assiette Pondérée
    
    Tableau 2 - NCO:
    - Pas de filtre
    - Lignes: LCR_Catégorie
    - Colonnes: Date d'arrêté
    - Valeurs: Somme LCR_Assiette Pondérée
    """
    try:
        logger.info("📊 Création des tableaux BUFFER & NCO - Style TCD Excel")
        
        buffer_nco_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement BUFFER & NCO TCD pour {file_type}")
            
            # Vérification des colonnes requises
            buffer_nco_cols = ["Top Conso", "LCR_Catégorie", "LCR_Template Section 1", 
                              "Libellé Client", "Date d'arrêté", "LCR_Assiette Pondérée"]
            missing_cols = [col for col in buffer_nco_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour BUFFER & NCO {file_type}: {missing_cols}")
                continue
            
            # Filtrage Top Conso pour les deux tableaux
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            logger.info(f"📋 Après filtrage Top Conso: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée BUFFER & NCO pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["LCR_Catégorie"] = df_filtered["LCR_Catégorie"].astype(str).str.strip()
            df_filtered["LCR_Template Section 1"] = df_filtered["LCR_Template Section 1"].astype(str).str.strip()
            df_filtered["Libellé Client"] = df_filtered["Libellé Client"].astype(str).str.strip()
            df_filtered["Date d'arrêté"] = df_filtered["Date d'arrêté"].astype(str).str.strip()
            
            # Obtenir toutes les dates uniques
            dates = sorted(df_filtered["Date d'arrêté"].unique())
            
            # =============================================================================
            # TABLEAU 1: BUFFER (avec filtre LCR_Catégorie = "1- Buffer")
            # =============================================================================
            buffer_pivot_data = []
            df_buffer = df_filtered[df_filtered["LCR_Catégorie"] == "1- Buffer"].copy()
            
            if len(df_buffer) > 0:
                # Grouper par LCR_Template Section 1 (niveau 1 de hiérarchie)
                sections = sorted(df_buffer["LCR_Template Section 1"].unique())
                
                for section in sections:
                    section_data = df_buffer[df_buffer["LCR_Template Section 1"] == section]
                    
                    # Sous-groupes par Libellé Client (niveau 2 de hiérarchie)
                    clients = sorted(section_data["Libellé Client"].unique())
                    
                    # Données détaillées par client
                    client_details = []
                    section_totals_by_date = {}
                    
                    for client in clients:
                        client_data = section_data[section_data["Libellé Client"] == client]
                        
                        # Calculer les valeurs par date pour ce client
                        date_values = {}
                        for date in dates:
                            date_total = client_data[
                                client_data["Date d'arrêté"] == date
                            ]["LCR_Assiette Pondérée"].sum()
                            
                            # Conversion en milliards
                            date_values[date] = float(date_total) / 1_000_000_000
                            
                            # Cumuler pour les totaux de section
                            if date not in section_totals_by_date:
                                section_totals_by_date[date] = 0
                            section_totals_by_date[date] += date_values[date]
                        
                        # Ajouter cette ligne de détail client
                        client_details.append({
                            "client": client,
                            "date_values": date_values,
                            "is_detail": True
                        })
                    
                    # Ajouter le groupe Section avec ses détails
                    buffer_pivot_data.append({
                        "section": section,
                        "client_details": client_details,
                        "section_totals_by_date": section_totals_by_date,
                        "is_section_group": True
                    })
            
            # =============================================================================
            # TABLEAU 2: NCO (pas de filtre, groupé par LCR_Catégorie)
            # =============================================================================
            nco_pivot_data = []
            
            # Grouper par LCR_Catégorie
            categories = sorted(df_filtered["LCR_Catégorie"].unique())
            
            for categorie in categories:
                categorie_data = df_filtered[df_filtered["LCR_Catégorie"] == categorie]
                
                # Calculer les valeurs par date pour cette catégorie
                date_values = {}
                for date in dates:
                    date_total = categorie_data[
                        categorie_data["Date d'arrêté"] == date
                    ]["LCR_Assiette Pondérée"].sum()
                    
                    # Conversion en milliards
                    date_values[date] = float(date_total) / 1_000_000_000
                
                # Ajouter cette catégorie
                nco_pivot_data.append({
                    "categorie": categorie,
                    "date_values": date_values
                })
            
            buffer_nco_results[file_type] = {
                "buffer_pivot_data": buffer_pivot_data,
                "nco_pivot_data": nco_pivot_data,
                "dates": dates
            }
            
            logger.info(f"✅ BUFFER & NCO TCD {file_type}: Buffer={len(buffer_pivot_data)} sections, NCO={len(nco_pivot_data)} catégories, {len(dates)} dates")
        
        return {
            "title": "BUFFER & NCO - TCD Analysis",
            "data": buffer_nco_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "tcd_config": {
                    "buffer_table": {
                        "filters": {"lcr_categorie": "1- Buffer", "top_conso": "O"},
                        "rows": ["LCR_Template Section 1", "Libellé Client"],
                        "columns": ["Date d'arrêté"],
                        "values": "Somme LCR_Assiette Pondérée (Bn €)"
                    },
                    "nco_table": {
                        "filters": {"top_conso": "O"},
                        "rows": ["LCR_Catégorie"],
                        "columns": ["Date d'arrêté"],
                        "values": "Somme LCR_Assiette Pondérée (Bn €)"
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableaux BUFFER & NCO TCD: {e}")
        return {
            "title": "BUFFER & NCO - Erreur",
            "error": str(e)
        }
      

# ========================== FONCTIONS CONSUMPTION & RESOURCES TABLE ===========================


def create_consumption_resources_table(dataframes):
    """
    Crée les tableaux CONSUMPTION & RESOURCES avec structure pivot par date
    """
    try:
        logger.info("📊 Création des tableaux CONSUMPTION & RESOURCES")
        
        consumption_resources_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement CONSUMPTION & RESOURCES pour {file_type}")
            
            # Vérification des colonnes requises
            cons_res_cols = ["Top Conso", "LCR_ECO_GROUPE_METIERS", "Sous-Métier", 
                            "Date d'arrêté", "LCR_ECO_IMPACT_LCR"]
            missing_cols = [col for col in cons_res_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour CONSUMPTION & RESOURCES {file_type}: {missing_cols}")
                continue
            
            # Filtrage Top Conso pour les deux tableaux
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            logger.info(f"📋 Après filtrage Top Conso: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée CONSUMPTION & RESOURCES pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_ECO_IMPACT_LCR"] = pd.to_numeric(
                df_filtered["LCR_ECO_IMPACT_LCR"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["LCR_ECO_GROUPE_METIERS"] = df_filtered["LCR_ECO_GROUPE_METIERS"].astype(str).str.strip()
            df_filtered["Sous-Métier"] = df_filtered["Sous-Métier"].astype(str).str.strip()
            df_filtered["Date d'arrêté"] = df_filtered["Date d'arrêté"].astype(str).str.strip()
            
            # Obtenir toutes les dates uniques
            dates = sorted(df_filtered["Date d'arrêté"].unique())
            
            # TABLEAU 1: CONSUMPTION
            consumption_data = []
            allowed_groupes_cons = ["A&WM & Insurance", "CIB Financing", "CIB Markets", "GLOBAL TRADE", "Other Consumption"]
            excluded_sous_metier_cons = ["GT TREASURY SOLUTIONS", "GT GROUP SERVICES"]
            
            df_consumption = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(allowed_groupes_cons)].copy()
            df_consumption = df_consumption[~df_consumption["Sous-Métier"].isin(excluded_sous_metier_cons)].copy()
            
            if len(df_consumption) > 0:
                for groupe in allowed_groupes_cons:
                    groupe_data = df_consumption[df_consumption["LCR_ECO_GROUPE_METIERS"] == groupe]
                    
                    if len(groupe_data) > 0:
                        row_data = {
                            "lcr_eco_groupe_metiers": groupe,
                            "dates": {}
                        }
                        
                        for date in dates:
                            date_data = groupe_data[groupe_data["Date d'arrêté"] == date]
                            total = float(date_data["LCR_ECO_IMPACT_LCR"].sum()) / 1_000_000_000
                            row_data["dates"][date] = total
                        
                        consumption_data.append(row_data)
            
            # TABLEAU 2: RESOURCES
            resources_data = []
            allowed_groupes_res = ["GLOBAL TRADE", "Other Contribution", "Treasury"]
            excluded_sous_metier_res = ["GT GROUP SERVICES", "GT COMMODITY", "GT TRADE FINANCE"]
            
            df_resources = df_filtered[df_filtered["LCR_ECO_GROUPE_METIERS"].isin(allowed_groupes_res)].copy()
            df_resources = df_resources[~df_resources["Sous-Métier"].isin(excluded_sous_metier_res)].copy()
            
            if len(df_resources) > 0:
                for groupe in allowed_groupes_res:
                    groupe_data = df_resources[df_resources["LCR_ECO_GROUPE_METIERS"] == groupe]
                    
                    if len(groupe_data) > 0:
                        row_data = {
                            "lcr_eco_groupe_metiers": groupe,
                            "dates": {}
                        }
                        
                        for date in dates:
                            date_data = groupe_data[groupe_data["Date d'arrêté"] == date]
                            total = float(date_data["LCR_ECO_IMPACT_LCR"].sum()) / 1_000_000_000
                            row_data["dates"][date] = total
                        
                        resources_data.append(row_data)
            
            consumption_resources_results[file_type] = {
                "consumption_data": consumption_data,
                "resources_data": resources_data,
                "dates": dates
            }
            
            logger.info(f"✅ CONSUMPTION & RESOURCES {file_type}: Consumption={len(consumption_data)} lignes, Resources={len(resources_data)} lignes, {len(dates)} dates")
        
        return {
            "title": "CONSUMPTION & RESOURCES",
            "data": consumption_resources_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "consumption_filters": {
                        "groupe_metiers": allowed_groupes_cons,
                        "excluded_sous_metier": excluded_sous_metier_cons
                    },
                    "resources_filters": {
                        "groupe_metiers": allowed_groupes_res,
                        "excluded_sous_metier": excluded_sous_metier_res
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableaux CONSUMPTION & RESOURCES: {e}")
        return {
            "title": "CONSUMPTION & RESOURCES - Erreur",
            "error": str(e)
        }
    

# ========================== FONCTIONS CONTEXTE CHATBOT ===========================


def prepare_system_prompt() -> str:
    """
    Prepare the system prompt in English for LCR banking analysis
    """
    return """You are an expert LCR (Liquidity Coverage Ratio) banking analyst and financial consultant. 

Your role is to:
- Analyze complex banking liquidity data from multiple pivot tables
- Provide strategic insights on LCR compliance and risk management
- Explain variations between time periods (D vs D-1 vs M-1)
- Identify trends, anomalies, and business implications
- Offer actionable recommendations for liquidity management

You have access to comprehensive LCR analysis including:
- BUFFER analysis (LCR Template sections and client details)
- SUMMARY comparisons (LCR Assiette Pondérée vs ECO Impact)
- CONSUMPTION analysis by business groups (A&WM, CIB, GLOBAL TRADE, etc.)
- RESOURCES analysis by business groups (Treasury, Other Contribution, etc.)
- CAPPAGE & Short_LCR pivot analysis by SI Remettant
- BUFFER & NCO detailed breakdowns by categories and dates
- CONSUMPTION & RESOURCES time-series analysis

Key context:
- All values are in billions of euros (Bn €)
- Data compares current day (D) vs previous day (D-1) vs previous month (M-1)
- Focus on regulatory compliance, risk management, and business impact
- Consider both quantitative analysis and qualitative insights

Communication style:
- Be precise and professional
- Use banking terminology appropriately
- Provide both summary and detailed analysis when relevant
- Highlight significant variations and their potential causes
- Suggest actionable next steps when appropriate"""

def prepare_analysis_context() -> str:
    """
    Prepare detailed context from all saved analysis data
    """
    context_parts = []
    
    # Base business context in English
    context_parts.append("BUSINESS CONTEXT:")
    context_parts.append("- LCR (Liquidity Coverage Ratio) banking analysis application")
    context_parts.append("- Multi-table pivot analysis with Excel-style presentation")
    context_parts.append("- Comparison between D (Today) vs D-1 (Yesterday) vs M-1 (Month-1)")
    context_parts.append("- All monetary values in billions of euros (Bn €)")
    
    # Analysis data if available
    if chatbot_session.get("context_data"):
        data = chatbot_session["context_data"]
        
        context_parts.append(f"\nANALYSIS PERFORMED ON: {data.get('analysis_timestamp', 'Unknown')}")
        
        # BUFFER Table Analysis
        buffer = data.get("buffer")
        if buffer and isinstance(buffer, dict) and not buffer.get("error"):
            context_parts.append("\n=== BUFFER TABLE ANALYSIS ===")
            context_parts.append(f"Title: {buffer.get('title', 'BUFFER')}")
            context_parts.append("Filter: LCR_Catégorie = '1- Buffer', Top Conso = 'O'")
            
            buffer_data = buffer.get("data")
            if buffer_data and isinstance(buffer_data, dict):
                context_parts.append("Key Buffer sections with variations:")
                pivot_data = buffer_data.get("pivot_data", [])
                if pivot_data and isinstance(pivot_data, list):
                    for section_group in pivot_data[:3]:  # First 3 sections
                        if isinstance(section_group, dict):
                            section = section_group.get('section', 'N/A')
                            total_j = section_group.get('section_total_j', 0)
                            var_daily = section_group.get('section_variation_daily', 0)
                            var_monthly = section_group.get('section_variation_monthly', 0)
                            context_parts.append(f"- {section}: D={total_j:.3f} Bn €, Daily Var={var_daily:+.3f}, Monthly Var={var_monthly:+.3f}")
        
        # SUMMARY Table Analysis  
        summary = data.get("summary")
        if summary and isinstance(summary, dict) and not summary.get("error"):
            context_parts.append("\n=== SUMMARY TABLE ANALYSIS ===")
            context_parts.append("Comparison of LCR Assiette Pondérée vs LCR ECO Impact")
            
            summary_data = summary.get("data")
            if summary_data and isinstance(summary_data, dict):
                for file_type, file_data in summary_data.items():
                    if file_data and isinstance(file_data, list):
                        context_parts.append(f"\n{file_type.upper()} summary:")
                        for item in file_data[:2]:  # First 2 dates
                            if isinstance(item, dict):
                                date = item.get('date', 'N/A')
                                assiette = item.get('sum_assiette', 0)
                                impact = item.get('sum_impact', 0)
                                diff = item.get('sum_difference', 0)
                                context_parts.append(f"- Date {date}: Assiette={assiette:.3f}, Impact={impact:.3f}, Diff={diff:.3f} Bn €")
        
        # CONSUMPTION Table Analysis
        consumption = data.get("consumption")
        if consumption and isinstance(consumption, dict) and not consumption.get("error"):
            context_parts.append("\n=== CONSUMPTION TABLE ANALYSIS ===")
            context_parts.append("Filtered business groups: A&WM & Insurance, CIB Financing, CIB Markets, GLOBAL TRADE, Other Consumption")
            
            consumption_data = consumption.get("data")
            if consumption_data and isinstance(consumption_data, dict):
                for file_type, file_data in consumption_data.items():
                    if file_data and isinstance(file_data, list):
                        context_parts.append(f"\n{file_type.upper()} consumption by business group:")
                        for item in file_data:
                            if isinstance(item, dict):
                                groupe = item.get('LCR_ECO_GROUPE_METIERS', 'N/A')
                                impact = item.get('LCR_ECO_IMPACT_LCR_Bn', 0)
                                context_parts.append(f"- {groupe}: {impact:.3f} Bn €")
        
        # RESOURCES Table Analysis
        resources = data.get("resources")
        if resources and isinstance(resources, dict) and not resources.get("error"):
            context_parts.append("\n=== RESOURCES TABLE ANALYSIS ===")
            context_parts.append("Filtered business groups: GLOBAL TRADE, Other Contribution, Treasury")
            
            resources_data = resources.get("data")
            if resources_data and isinstance(resources_data, dict):
                for file_type, file_data in resources_data.items():
                    if file_data and isinstance(file_data, list):
                        context_parts.append(f"\n{file_type.upper()} resources by business group:")
                        for item in file_data:
                            if isinstance(item, dict):
                                groupe = item.get('LCR_ECO_GROUPE_METIERS', 'N/A')
                                impact = item.get('LCR_ECO_IMPACT_LCR_Bn', 0)
                                context_parts.append(f"- {groupe}: {impact:.3f} Bn €")
        
        # CAPPAGE Table Analysis
        cappage = data.get("cappage")
        if cappage and isinstance(cappage, dict) and not cappage.get("error"):
            context_parts.append("\n=== CAPPAGE & SHORT_LCR TCD ANALYSIS ===")
            context_parts.append("Pivot Table: SI Remettant (SHORT_LCR, CAPREOS) × Commentaire × Date d'arrêté")
            
            cappage_data = cappage.get("data")
            if cappage_data and isinstance(cappage_data, dict):
                for file_type, file_data in cappage_data.items():
                    pivot_data = file_data.get("pivot_data") if isinstance(file_data, dict) else None
                    if pivot_data and isinstance(pivot_data, list):
                        context_parts.append(f"\n{file_type.upper()} CAPPAGE pivot data:")
                        for si_group in pivot_data[:2]:  # First 2 SI groups
                            if isinstance(si_group, dict):
                                si_name = si_group.get("si_remettant", "N/A")
                                totals = si_group.get("si_totals_by_date", {})
                                if isinstance(totals, dict):
                                    total_str = ', '.join([f'{date}={val:.3f}' for date, val in list(totals.items())[:3]])
                                    context_parts.append(f"- {si_name}: {total_str}")
        
        # BUFFER & NCO Table Analysis
        buffer_nco = data.get("buffer_nco")
        if buffer_nco and isinstance(buffer_nco, dict) and not buffer_nco.get("error"):
            context_parts.append("\n=== BUFFER & NCO TCD ANALYSIS ===")
            context_parts.append("Two pivot tables: 1) BUFFER filtered by LCR_Catégorie='1- Buffer', 2) NCO all categories")
            
            bnco_data = buffer_nco.get("data")
            if bnco_data and isinstance(bnco_data, dict):
                for file_type, file_data in bnco_data.items():
                    if isinstance(file_data, dict):
                        context_parts.append(f"\n{file_type.upper()} Buffer & NCO:")
                        
                        # Buffer data
                        buffer_pivot = file_data.get("buffer_pivot_data")
                        if buffer_pivot and isinstance(buffer_pivot, list):
                            context_parts.append("Buffer sections:")
                            for section_group in buffer_pivot[:3]:  # First 3 sections
                                if isinstance(section_group, dict):
                                    section_name = section_group.get("section", "N/A")
                                    client_count = len(section_group.get('client_details', []))
                                    context_parts.append(f"- {section_name} with {client_count} clients")
                        
                        # NCO data
                        nco_pivot = file_data.get("nco_pivot_data")
                        if nco_pivot and isinstance(nco_pivot, list):
                            context_parts.append("NCO categories:")
                            for category in nco_pivot[:3]:  # First 3 categories
                                if isinstance(category, dict):
                                    cat_name = category.get("categorie", "N/A")
                                    context_parts.append(f"- {cat_name}")
        
        # CONSUMPTION & RESOURCES Table Analysis
        cons_res = data.get("consumption_resources")
        if cons_res and isinstance(cons_res, dict) and not cons_res.get("error"):
            context_parts.append("\n=== CONSUMPTION & RESOURCES TCD ANALYSIS ===")
            context_parts.append("Two pivot tables with date columns: Consumption (filtered groups) + Resources (filtered groups)")
            
            cr_data = cons_res.get("data")
            if cr_data and isinstance(cr_data, dict):
                for file_type, file_data in cr_data.items():
                    if isinstance(file_data, dict):
                        context_parts.append(f"\n{file_type.upper()} Consumption & Resources by date:")
                        
                        dates = file_data.get("dates", [])
                        if dates and isinstance(dates, list):
                            context_parts.append(f"Available dates: {', '.join(dates[:5])}...")  # First 5 dates
                        
                        # Consumption data summary
                        cons_data = file_data.get("consumption_data")
                        if cons_data and isinstance(cons_data, list):
                            context_parts.append("Consumption groups:")
                            for cons_item in cons_data:
                                if isinstance(cons_item, dict):
                                    group_name = cons_item.get("lcr_eco_groupe_metiers", "N/A")
                                    context_parts.append(f"- {group_name}")
                        
                        # Resources data summary
                        res_data = file_data.get("resources_data")
                        if res_data and isinstance(res_data, list):
                            context_parts.append("Resources groups:")
                            for res_item in res_data:
                                if isinstance(res_item, dict):
                                    group_name = res_item.get("lcr_eco_groupe_metiers", "N/A")
                                    context_parts.append(f"- {group_name}")
        
        # Source files information
        raw_df_info = data.get("raw_dataframes_info")
        if raw_df_info and isinstance(raw_df_info, dict):
            context_parts.append("\n=== SOURCE FILES INFORMATION ===")
            for file_type, info in raw_df_info.items():
                if isinstance(info, dict):
                    shape = info.get('shape', [0, 0])
                    cols = info.get('columns', [])
                    context_parts.append(f"File {file_type}: {shape[0]} rows, {shape[1]} columns")
                    if cols and isinstance(cols, list):
                        context_parts.append(f"Key columns: {', '.join(cols[:10])}...")  # First 10 columns
    
    else:
        context_parts.append("\nNo analysis available - analyses must be run first.")
    
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
    Prepare complete context including system prompt + analysis + documents + history
    """
    context_parts = []
    
    # System prompt in English
    context_parts.append(prepare_system_prompt())
    context_parts.append("\n" + "="*80 + "\n")
    
    # Analysis context
    context_parts.append(prepare_analysis_context())
    
    # Uploaded documents context
    docs_context = prepare_documents_context()
    if docs_context:
        context_parts.append(f"\n\nADDITIONAL CONTEXT DOCUMENTS:\n{docs_context}")
    
    # Conversation history (last 10 messages to avoid overloading)
    if chatbot_session["messages"]:
        context_parts.append("\n\nCONVERSATION HISTORY:")
        for msg in chatbot_session["messages"][-10:]:
            role = "USER" if msg["type"] == "user" else "ASSISTANT"
            context_parts.append(f"{role}: {msg['message']}")
        context_parts.append("\n--- End of conversation history ---")
    
    return "\n".join(context_parts)


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