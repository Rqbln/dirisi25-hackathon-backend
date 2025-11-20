"""Service RAG pour l'analyse des attaques et recommandations de sécurité."""

import os
from typing import List, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage


class RAGService:
    """Service RAG pour analyser les attaques et fournir des recommandations."""
    
    def __init__(self, knowledge_base_path: str = "/workspace/results-team-9/knowledge-base"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.embeddings = None
        self.chat_history = []  # Historique de conversation simple
        self._initialize()
    
    def _initialize(self):
        """Initialise le RAG avec la base de connaissances."""
        print("🔧 Initialisation du RAG...")
        
        # Embeddings (modèle français optimisé)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Chemin du vectorstore
        vectorstore_path = self.knowledge_base_path / "vectorstore"
        
        # Charger ou créer le vectorstore
        if vectorstore_path.exists():
            print("📂 Chargement du vectorstore existant...")
            self.vectorstore = Chroma(
                persist_directory=str(vectorstore_path),
                embedding_function=self.embeddings
            )
        else:
            print("📚 Création du vectorstore depuis les documents...")
            self._create_vectorstore(vectorstore_path)
        
        # Créer le retriever
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        
        # Initialiser le LLM
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        
        print("✅ RAG initialisé")
    
    def _create_vectorstore(self, vectorstore_path: Path):
        """Crée le vectorstore depuis les documents PDF."""
        docs_path = self.knowledge_base_path / "docs"
        
        if not docs_path.exists():
            print(f"⚠️ Dossier {docs_path} non trouvé, création d'un vectorstore vide")
            self.vectorstore = Chroma(
                persist_directory=str(vectorstore_path),
                embedding_function=self.embeddings
            )
            return
        
        # Charger les PDFs
        loader = DirectoryLoader(
            str(docs_path),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        documents = loader.load()
        
        # Découper les documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        texts = text_splitter.split_documents(documents)
        
        # Créer le vectorstore
        self.vectorstore = Chroma.from_documents(
            documents=texts,
            embedding=self.embeddings,
            persist_directory=str(vectorstore_path)
        )
        
        print(f"✅ Vectorstore créé avec {len(texts)} chunks")
    
    def _format_docs(self, docs):
        """Formate les documents récupérés."""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def analyze_attack(self, log_entry: Dict[str, Any]) -> str:
        """Analyse initiale d'une attaque basée sur un log."""
        # Construire le contexte du log
        log_context = f"""
Analyse de l'attaque détectée:

Type d'attaque: {log_entry.get('bug_type', 'N/A')}
Sévérité: {log_entry.get('severity', 'N/A')}
Timestamp: {log_entry.get('timestamp', 'N/A')}
Firewall: {log_entry.get('firewall_id', 'N/A')}
IP Source: {log_entry.get('src_ip', 'N/A')}
IP Destination: {log_entry.get('dst_ip', 'N/A')}
Protocole: {log_entry.get('protocol', 'N/A')}
Action: {log_entry.get('action', 'N/A')}

Fournis une analyse détaillée de cette attaque, les risques associés, et les recommandations de mitigation.
"""
        
        # Créer le prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en cybersécurité. 
Utilise le contexte suivant pour analyser l'attaque:

{context}

Fournis une analyse structurée avec:
1. Nature de l'attaque
2. Risques associés
3. Recommandations de mitigation"""),
            ("human", "{question}")
        ])
        
        # Créer la chaîne RAG avec LCEL
        chain = (
            {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        # Générer la réponse
        try:
            answer = chain.invoke(log_context)
            # Réinitialiser l'historique pour une nouvelle analyse
            self.chat_history = [
                HumanMessage(content=log_context),
                AIMessage(content=answer)
            ]
            return answer
        except Exception as e:
            return f"Erreur lors de l'analyse: {str(e)}"
    
    def chat(self, question: str, session_id: str = "default") -> Dict[str, Any]:
        """Continue la conversation avec le RAG."""
        try:
            # Créer le prompt avec historique
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Tu es un expert en cybersécurité. 
Utilise le contexte suivant pour répondre:

{context}

Réponds de manière concise et précise."""),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}")
            ])
            
            # Créer la chaîne
            chain = (
                {
                    "context": self.retriever | self._format_docs,
                    "chat_history": lambda x: self.chat_history,
                    "question": RunnablePassthrough()
                }
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            # Invoquer
            answer = chain.invoke(question)
            
            # Mettre à jour l'historique
            self.chat_history.append(HumanMessage(content=question))
            self.chat_history.append(AIMessage(content=answer))
            
            # Récupérer les documents sources
            docs = self.retriever.invoke(question)
            sources = [doc.page_content[:200] for doc in docs]
            
            return {
                "answer": answer,
                "sources": sources
            }
        except Exception as e:
            return {
                "answer": f"Erreur: {str(e)}",
                "sources": []
            }
    
    def reset_conversation(self):
        """Réinitialise la mémoire conversationnelle."""
        self.chat_history = []


# Instance globale du RAG (chargé au démarrage)
_rag_service = None


def get_rag_service() -> RAGService:
    """Retourne l'instance du service RAG (singleton)."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

