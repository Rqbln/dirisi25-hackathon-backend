"""Service RAG pour l'analyse des attaques et recommandations de sécurité."""

import os
from dotenv import load_dotenv

load_dotenv()
from typing import List, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# from app.services.ovh_llm import OVH_LLM


class RAGService:
    """Service RAG pour analyser les attaques et fournir des recommandations."""

    def __init__(self, knowledge_base_path: str = "data/knowledge-base"):
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

        # Embeddings (Gemini)
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("⚠️ GOOGLE_API_KEY non trouvé dans les variables d'environnement!")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=api_key
        )

        # Chemin du vectorstore
        vectorstore_path = self.knowledge_base_path / "vectorstore"

        # Charger ou créer le vectorstore
        if vectorstore_path.exists():
            print(f"📂 Chargement du vectorstore existant: {vectorstore_path}")
            self.vectorstore = Chroma(
                persist_directory=str(vectorstore_path), embedding_function=self.embeddings
            )

            # Vérifier le nombre de documents
            try:
                collection = self.vectorstore._collection
                doc_count = collection.count()
                print(f"   ℹ️ Vectorstore contient {doc_count} documents")

                if doc_count == 0:
                    print("   ⚠️ VECTORSTORE VIDE! Aucun document n'a été indexé.")
                    print("   💡 Vérifiez que les PDFs sont présents dans knowledge-base/docs/")
                else:
                    # Afficher un exemple de document
                    sample = collection.peek(limit=1)
                    if sample and sample.get("documents"):
                        print(f"   📄 Exemple de document: {sample['documents'][0][:100]}...")
            except Exception as e:
                print(f"   ⚠️ Impossible de compter les documents: {e}")
        else:
            print("📚 Création du vectorstore depuis les documents...")
            self._create_vectorstore(vectorstore_path)

        # Créer le retriever avec plus de contexte
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # Initialiser le LLM Gemini
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            max_tokens=2048,
            convert_system_message_to_human=True,
            google_api_key=api_key,
        )

        print("✅ RAG initialisé avec Gemini LLM")

    def _create_vectorstore(self, vectorstore_path: Path):
        """Crée le vectorstore depuis les documents PDF."""
        docs_path = self.knowledge_base_path / "docs"

        if not docs_path.exists():
            print(f"⚠️ Dossier {docs_path} non trouvé, création d'un vectorstore vide")
            self.vectorstore = Chroma(
                persist_directory=str(vectorstore_path), embedding_function=self.embeddings
            )
            return

        # Charger les PDFs
        pdf_loader = DirectoryLoader(str(docs_path), glob="**/*.pdf", loader_cls=PyPDFLoader)
        pdf_docs = pdf_loader.load()

        # Charger les fichiers TXT
        txt_loader = DirectoryLoader(str(docs_path), glob="**/*.txt", loader_cls=TextLoader)
        txt_docs = txt_loader.load()

        documents = pdf_docs + txt_docs

        # Découper les documents avec plus de contexte
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
        texts = text_splitter.split_documents(documents)

        # Créer le vectorstore
        self.vectorstore = Chroma.from_documents(
            documents=texts, embedding=self.embeddings, persist_directory=str(vectorstore_path)
        )

        print(f"✅ Vectorstore créé avec {len(texts)} chunks")

    def _format_docs(self, docs):
        """Formate les documents récupérés."""
        return "\n\n".join(doc.page_content for doc in docs)

    def analyze_attack(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse automatique et contextuelle d'un log (attaque ou bug) avec RAG."""

        # Construire une question enrichie pour le RAG
        bug_type = log_entry.get("bug_type", "N/A")
        severity = log_entry.get("severity", "N/A")
        src_ip = log_entry.get("src_ip", "N/A")
        dst_ip = log_entry.get("dst_ip", "N/A")
        protocol = log_entry.get("protocol", "N/A")
        action = log_entry.get("action", "N/A")
        firewall = log_entry.get("firewall_id", "N/A")
        timestamp = log_entry.get("timestamp", "N/A")

        # Question détaillée pour le retriever
        query = f"""
Log de sécurité firewall détecté:
- Type: {bug_type}
- Sévérité: {severity}
- Source: {src_ip} vers Destination: {dst_ip}
- Protocole: {protocol}
- Action: {action}
- Firewall: {firewall}
- Timestamp: {timestamp}

Analyse cette entrée réseau et fournis:
1. Nature exacte de l'anomalie ou attaque
2. Gravité et impact potentiel
3. Recommandations de mitigation concrètes
4. Mesures préventives
"""

        # Template amélioré avec contexte riche
        template = """Tu es un expert en cybersécurité réseau et analyse de logs firewall.

Voici les informations techniques pertinentes extraites de la base de connaissances:

{context}

---

Sur la base de ces informations techniques et de ton expertise, analyse le log suivant:

{query}

Fournis une analyse détaillée et structurée incluant:
- La nature technique de l'anomalie/attaque
- Les risques et impacts potentiels
- Les recommandations de mitigation immédiate
- Les mesures préventives à mettre en place

Sois précis, concret et actionnable. Utilise les informations du contexte pour enrichir ton analyse.

Réponse:"""

        prompt = PromptTemplate(input_variables=["context", "query"], template=template)

        # Créer la chaîne RAG avec LCEL
        chain = (
            {"context": self.retriever | self._format_docs, "query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        # Générer la réponse
        try:
            print(f"🔍 Query envoyée au retriever: {query[:200]}...")

            # Récupérer les documents sources
            source_docs = self.retriever.invoke(query)

            print(f"📚 Retriever a trouvé {len(source_docs)} documents")
            if source_docs:
                print(f"   Premier doc - Source: {source_docs[0].metadata.get('source', 'N/A')}")
                print(f"   Premier doc - Page: {source_docs[0].metadata.get('page', 'N/A')}")
                print(f"   Premier doc - Contenu (100 car): {source_docs[0].page_content[:100]}...")
            else:
                print("   ⚠️ AUCUN DOCUMENT TROUVÉ PAR LE RETRIEVER!")

            # Générer l'analyse
            answer = chain.invoke(query)

            # Sauvegarder dans l'historique pour le chat
            self.chat_history = [HumanMessage(content=query), AIMessage(content=answer)]

            # Formatter les sources
            sources = [
                {
                    "content": doc.page_content[:500],  # Premier 500 caractères
                    "metadata": {
                        "source": doc.metadata.get("source", "Inconnu"),
                        "page": doc.metadata.get("page", "N/A"),
                    },
                }
                for doc in source_docs
            ]

            print(f"✅ Analyse terminée - {len(sources)} sources trouvées (après formatage)")

            # Retourner avec les sources
            return {"analysis": answer, "sources": sources}
        except Exception as e:
            return {"analysis": f"Erreur lors de l'analyse: {str(e)}", "sources": []}

    def chat(self, question: str, session_id: str = "default") -> Dict[str, Any]:
        """Continue la conversation avec le RAG en tenant compte du contexte."""
        try:
            # Construire l'historique formaté
            history_text = "\n".join(
                [
                    f"{'Question' if isinstance(msg, HumanMessage) else 'Réponse'}: {msg.content[:500]}"
                    for msg in self.chat_history[-4:]  # Garder les 2 derniers échanges
                ]
            )

            # Template pour chat contextuel
            template = """Tu es un expert en cybersécurité.

Informations techniques de la base de connaissances:

{context}

---

Historique de la conversation:
{history}

---

Question actuelle: {question}

Réponds de manière précise et technique en t'appuyant sur le contexte et l'historique.

Réponse:"""

            prompt = PromptTemplate(
                input_variables=["context", "history", "question"], template=template
            )

            # Créer la chaîne
            chain = (
                {
                    "context": self.retriever | self._format_docs,
                    "history": lambda x: history_text,
                    "question": RunnablePassthrough(),
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

            return {"answer": answer, "sources": sources}
        except Exception as e:
            return {"answer": f"Erreur: {str(e)}", "sources": []}

    def reset_conversation(self):
        """Réinitialise la mémoire conversationnelle."""
        self.chat_history = []


# Instance globale du RAG (chargé au démarrage)
_rag_service = None
_rag_init_error = None


def get_rag_service() -> RAGService:
    """Retourne l'instance du service RAG (singleton)."""
    global _rag_service, _rag_init_error

    if _rag_service is None and _rag_init_error is None:
        try:
            print("🔧 Initialisation du service RAG...")
            _rag_service = RAGService()
        except Exception as e:
            _rag_init_error = str(e)
            print(f"❌ Erreur initialisation RAG: {_rag_init_error}")
            raise RuntimeError(f"Impossible d'initialiser le service RAG: {_rag_init_error}")

    if _rag_init_error is not None:
        raise RuntimeError(
            f"Service RAG non disponible (erreur d'initialisation): {_rag_init_error}"
        )

    return _rag_service
