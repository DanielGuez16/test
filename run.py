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

        # Nouvelles analyses
        buffer_results = create_buffer_table(dataframes)
        consumption_results = create_consumption_table(dataframes)
        resources_results = create_resources_table(dataframes)
        cappage_results = create_cappage_table(dataframes)
        buffer_nco_results = create_buffer_nco_table(dataframes)
        
        logger.info("Analyses terminées (nouveaux tableaux)")

        # SAUVEGARDER LE CONTEXTE CHATBOT
        chatbot_session["context_data"] = {
            "buffer": buffer_results,
            "consumption": consumption_results,
            "resources": resources_results,
            "cappage": cappage_results,
            "buffer_nco": buffer_nco_results,
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

        return {
            "success": True,
            "message": "Analyses terminées avec nouveaux tableaux",
            "timestamp": datetime.now().isoformat(),
            "context_ready": True,  
            "results": {
                "buffer": buffer_results,
                "consumption": consumption_results,
                "resources": resources_results,
                "cappage": cappage_results,
                "buffer_nco": buffer_nco_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")
    
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
    Crée le tableau BUFFER avec filtres spécifiques
    """
    try:
        logger.info("📊 Création du tableau BUFFER")
        
        buffer_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement BUFFER pour {file_type}")
            
            # Vérification des colonnes requises
            buffer_cols = ["Top Conso", "LCR_Catégorie", "LCR_Template Section 1", 
                          "Libellé Client", "LCR_Assiette Pondérée"]
            missing_cols = [col for col in buffer_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour BUFFER {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données
            df_filtered = df[df["Top Conso"] == "O"].copy()
            df_filtered = df_filtered[df_filtered["LCR_Catégorie"] == "1- Buffer"].copy()
            
            logger.info(f"📋 Après filtrage BUFFER: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée BUFFER pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["LCR_Template Section 1"] = df_filtered["LCR_Template Section 1"].astype(str).str.strip()
            df_filtered["Libellé Client"] = df_filtered["Libellé Client"].astype(str).str.strip()
            
            # Groupement
            grouped_data = []
            
            # Grouper par LCR_Template Section 1
            for section in df_filtered["LCR_Template Section 1"].unique():
                section_data = df_filtered[df_filtered["LCR_Template Section 1"] == section]
                
                if section == "1.1- Cash":
                    # Pour 1.1- Cash, montrer le détail par Libellé Client
                    for client in section_data["Libellé Client"].unique():
                        client_data = section_data[section_data["Libellé Client"] == client]
                        total = float(client_data["LCR_Assiette Pondérée"].sum())
                        grouped_data.append({
                            "section": section,
                            "client": client,
                            "total": total / 1_000_000_000,  # Conversion en milliards
                            "is_detail": True
                        })
                else:
                    # Pour les autres sections, montrer seulement le total
                    total = float(section_data["LCR_Assiette Pondérée"].sum())
                    grouped_data.append({
                        "section": section,
                        "client": "TOTAL",
                        "total": total / 1_000_000_000,  # Conversion en milliards
                        "is_detail": False
                    })
            
            buffer_results[file_type] = grouped_data
            logger.info(f"✅ BUFFER {file_type}: {len(grouped_data)} entrées")
        
        return {
            "title": "BUFFER",
            "data": buffer_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "lcr_categorie": "1- Buffer"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau BUFFER: {e}")
        return {
            "title": "BUFFER - Erreur",
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
    

# ========================== FONCTIONS CAPPAGE TABLE ===========================


def create_cappage_table(dataframes):
    """
    Crée le tableau CAPPAGE & Short_LCR avec structure pivot par date
    """
    try:
        logger.info("📊 Création du tableau CAPPAGE & Short_LCR")
        
        cappage_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement CAPPAGE pour {file_type}")
            
            # Vérification des colonnes requises
            cappage_cols = ["Top Conso", "SI Remettant", "Commentaire", 
                           "Date d'arrêté", "LCR_Assiette Pondérée"]
            missing_cols = [col for col in cappage_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"⚠️ Colonnes manquantes pour CAPPAGE {file_type}: {missing_cols}")
                continue
            
            # Filtrage des données
            df_filtered = df[df["Top Conso"] == "O"].copy()
            
            # Filtres spécifiques CAPPAGE
            allowed_si_remettant = ["SHORT_LCR", "CAPREOS"]
            df_filtered = df_filtered[df_filtered["SI Remettant"].isin(allowed_si_remettant)].copy()
            
            logger.info(f"📋 Après filtrage CAPPAGE: {len(df_filtered)} lignes")
            
            if len(df_filtered) == 0:
                logger.warning(f"⚠️ Aucune donnée CAPPAGE pour {file_type}")
                continue
            
            # Préparation des données
            df_filtered["LCR_Assiette Pondérée"] = pd.to_numeric(
                df_filtered["LCR_Assiette Pondérée"], errors='coerce'
            ).fillna(0)
            
            # Nettoyage des champs texte
            df_filtered["SI Remettant"] = df_filtered["SI Remettant"].astype(str).str.strip()
            df_filtered["Commentaire"] = df_filtered["Commentaire"].astype(str).str.strip()
            df_filtered["Date d'arrêté"] = df_filtered["Date d'arrêté"].astype(str).str.strip()
            
            # Structure de données pour le tableau croisé
            cappage_data = []
            
            # Obtenir toutes les dates uniques
            dates = sorted(df_filtered["Date d'arrêté"].unique())
            
            # Traitement par SI Remettant
            for si_remettant in allowed_si_remettant:
                si_data = df_filtered[df_filtered["SI Remettant"] == si_remettant]
                
                if si_remettant == "CAPREOS":
                    # Pour CAPREOS, montrer le détail par Commentaire
                    for commentaire in si_data["Commentaire"].unique():
                        commentaire_data = si_data[si_data["Commentaire"] == commentaire]
                        
                        # Créer une ligne pour chaque commentaire avec toutes les dates
                        row_data = {
                            "si_remettant": si_remettant,
                            "commentaire": commentaire,
                            "is_detail": True,
                            "dates": {}
                        }
                        
                        for date in dates:
                            date_data = commentaire_data[commentaire_data["Date d'arrêté"] == date]
                            total = float(date_data["LCR_Assiette Pondérée"].sum()) / 1_000_000_000
                            row_data["dates"][date] = total
                        
                        cappage_data.append(row_data)
                else:
                    # Pour SHORT_LCR, montrer seulement le total
                    row_data = {
                        "si_remettant": si_remettant,
                        "commentaire": "TOTAL",
                        "is_detail": False,
                        "dates": {}
                    }
                    
                    for date in dates:
                        date_data = si_data[si_data["Date d'arrêté"] == date]
                        total = float(date_data["LCR_Assiette Pondérée"].sum()) / 1_000_000_000
                        row_data["dates"][date] = total
                    
                    cappage_data.append(row_data)
            
            cappage_results[file_type] = {
                "data": cappage_data,
                "dates": dates
            }
            
            logger.info(f"✅ CAPPAGE {file_type}: {len(cappage_data)} lignes, {len(dates)} dates")
        
        return {
            "title": "CAPPAGE & Short_LCR",
            "data": cappage_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "si_remettant": allowed_si_remettant
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableau CAPPAGE: {e}")
        return {
            "title": "CAPPAGE & Short_LCR - Erreur",
            "error": str(e)
        }



# ========================== FONCTIONS BUFFER & NCO TABLE ===========================


def create_buffer_nco_table(dataframes):
    """
    Crée les tableaux BUFFER & NCO avec structure pivot par date
    """
    try:
        logger.info("📊 Création des tableaux BUFFER & NCO")
        
        buffer_nco_results = {}
        
        for file_type, df in dataframes.items():
            logger.info(f"📄 Traitement BUFFER & NCO pour {file_type}")
            
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
            
            # TABLEAU 1: BUFFER (avec filtre LCR_Catégorie = "1- Buffer")
            buffer_data = []
            df_buffer = df_filtered[df_filtered["LCR_Catégorie"] == "1- Buffer"].copy()
            
            if len(df_buffer) > 0:
                # Grouper par LCR_Template Section 1 et Libellé Client
                for section in df_buffer["LCR_Template Section 1"].unique():
                    section_data = df_buffer[df_buffer["LCR_Template Section 1"] == section]
                    
                    for client in section_data["Libellé Client"].unique():
                        client_data = section_data[section_data["Libellé Client"] == client]
                        
                        row_data = {
                            "lcr_template_section": section,
                            "libelle_client": client,
                            "dates": {}
                        }
                        
                        for date in dates:
                            date_data = client_data[client_data["Date d'arrêté"] == date]
                            total = float(date_data["LCR_Assiette Pondérée"].sum()) / 1_000_000_000
                            row_data["dates"][date] = total
                        
                        buffer_data.append(row_data)
            
            # TABLEAU 2: NCO (sans filtre, groupé par LCR_Catégorie)
            nco_data = []
            
            for categorie in df_filtered["LCR_Catégorie"].unique():
                categorie_data = df_filtered[df_filtered["LCR_Catégorie"] == categorie]
                
                row_data = {
                    "lcr_categorie": categorie,
                    "dates": {}
                }
                
                for date in dates:
                    date_data = categorie_data[categorie_data["Date d'arrêté"] == date]
                    total = float(date_data["LCR_Assiette Pondérée"].sum()) / 1_000_000_000
                    row_data["dates"][date] = total
                
                nco_data.append(row_data)
            
            buffer_nco_results[file_type] = {
                "buffer_data": buffer_data,
                "nco_data": nco_data,
                "dates": dates
            }
            
            logger.info(f"✅ BUFFER & NCO {file_type}: Buffer={len(buffer_data)} lignes, NCO={len(nco_data)} lignes, {len(dates)} dates")
        
        return {
            "title": "BUFFER & NCO",
            "data": buffer_nco_results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "filters_applied": {
                    "top_conso": "O",
                    "buffer_filter": "LCR_Catégorie = '1- Buffer'",
                    "nco_filter": "Aucun filtre supplémentaire"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création tableaux BUFFER & NCO: {e}")
        return {
            "title": "BUFFER & NCO - Erreur",
            "error": str(e)
        }
    

# ========================== FONCTIONS CONTEXTE CHATBOT ===========================


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