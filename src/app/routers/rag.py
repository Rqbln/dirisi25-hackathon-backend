"""Router pour le système RAG d'analyse d'attaques."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/v1/rag", tags=["rag"])


class AttackAnalysisRequest(BaseModel):
    """Requête d'analyse d'attaque."""
    log_entry: Dict[str, Any]


class ChatRequest(BaseModel):
    """Requête de chat avec le RAG."""
    question: str
    session_id: str = "default"


class AttackAnalysisResponse(BaseModel):
    """Réponse d'analyse d'attaque."""
    analysis: str
    log_summary: Dict[str, Any]


class ChatResponse(BaseModel):
    """Réponse de chat."""
    answer: str
    sources: list


@router.post("/analyze", response_model=AttackAnalysisResponse)
async def analyze_attack(request: AttackAnalysisRequest) -> AttackAnalysisResponse:
    """
    Analyse une attaque détectée et fournit des recommandations.
    
    Utilise le RAG pour:
    - Comprendre le type d'attaque
    - Évaluer les risques
    - Proposer des mesures de mitigation
    """
    try:
        rag = get_rag_service()
        analysis = rag.analyze_attack(request.log_entry)
        
        return AttackAnalysisResponse(
            analysis=analysis,
            log_summary=request.log_entry
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(request: ChatRequest) -> ChatResponse:
    """
    Continue la conversation avec le RAG pour approfondir l'analyse.
    """
    try:
        rag = get_rag_service()
        result = rag.chat(request.question, request.session_id)
        
        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chat: {str(e)}"
        )


@router.post("/reset")
async def reset_conversation():
    """Réinitialise la conversation RAG."""
    try:
        rag = get_rag_service()
        rag.reset_conversation()
        return {"message": "Conversation réinitialisée"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/health")
async def rag_health():
    """Vérifie l'état du service RAG."""
    try:
        rag = get_rag_service()
        return {
            "status": "ok",
            "vectorstore_loaded": rag.vectorstore is not None,
            "llm_ready": rag.llm is not None,
            "retriever_ready": rag.retriever is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
