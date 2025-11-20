# Configuration du Système RAG

## Vue d'ensemble

Le système RAG (Retrieval-Augmented Generation) permet d'analyser les attaques détectées et de fournir des recommandations de sécurité basées sur une base de connaissances.

## Installation

### 1. Installer les dépendances

```bash
pip install -r requirements-rag.txt
```

### 2. Configuration OpenAI

Le système utilise GPT-3.5-turbo par défaut. Configurez votre clé API :

```bash
export OPENAI_API_KEY="votre-clé-api"
```

### 3. Préparer la base de connaissances

Créez le dossier et ajoutez vos documents PDF :

```bash
mkdir -p /workspace/results-team-9/knowledge-base/docs
```

Placez vos documents de sécurité (guides, CVE, best practices, etc.) dans ce dossier :
- `/workspace/results-team-9/knowledge-base/docs/` - Documents PDF sources
- `/workspace/results-team-9/knowledge-base/vectorstore/` - Base vectorielle (créée automatiquement)

## Utilisation

### Via l'Interface Web

1. Effectuez une recherche de logs
2. Pour chaque attaque (pas les bugs), un bouton 🤖 apparaît
3. Cliquez sur le bouton pour analyser l'attaque avec le RAG
4. Consultez l'analyse initiale
5. Discutez avec le RAG pour approfondir

### Via l'API

#### Analyser une attaque

```bash
curl -X POST http://localhost:8000/v1/rag/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "log_entry": {
      "timestamp": "2025-04-01 00:00:39+00:00",
      "firewall_id": "FW-B",
      "src_ip": "192.168.109.185",
      "dst_ip": "210.35.190.91",
      "protocol": "TCP",
      "action": "DENY",
      "bug_type": "port_scan",
      "severity": "Medium",
      "type": "Attack"
    }
  }'
```

#### Discuter avec le RAG

```bash
curl -X POST http://localhost:8000/v1/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Comment mitiger ce type d'\''attaque ?",
    "session_id": "default"
  }'
```

#### Vérifier l'état du RAG

```bash
curl http://localhost:8000/v1/rag/health
```

## Architecture

### Backend (`src/app/services/rag_service.py`)

- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Vector Store**: ChromaDB
- **LLM**: GPT-3.5-turbo (OpenAI)
- **Memory**: Conversational Buffer Memory

### Workflow

1. **Chargement** : Les PDFs sont chargés et découpés en chunks de 1000 caractères
2. **Embedding** : Chaque chunk est converti en vecteur
3. **Storage** : Les vecteurs sont stockés dans ChromaDB
4. **Retrieval** : Lors d'une question, les 3 chunks les plus pertinents sont récupérés
5. **Generation** : Le LLM génère une réponse basée sur le contexte

## Optimisation

### Utiliser un modèle local (sans OpenAI)

Modifiez `rag_service.py` pour utiliser un modèle local :

```python
from langchain_community.llms import HuggingFacePipeline

llm = HuggingFacePipeline.from_model_id(
    model_id="mistralai/Mistral-7B-Instruct-v0.2",
    task="text-generation",
    device=0,  # GPU
    pipeline_kwargs={"max_new_tokens": 512}
)
```

### Améliorer les résultats

1. **Qualité des documents** : Ajoutez des guides de sécurité pertinents
2. **Chunking** : Ajustez `chunk_size` et `chunk_overlap`
3. **Retrieval** : Modifiez le paramètre `k` (nombre de chunks)
4. **Prompt Engineering** : Personnalisez les prompts dans `analyze_attack()`

## Dépannage

### Erreur "OpenAI API key not found"

```bash
export OPENAI_API_KEY="sk-..."
```

### Erreur "No documents found"

Vérifiez que des PDFs sont présents dans `/workspace/results-team-9/knowledge-base/docs/`

### Performance lente

- Utilisez un GPU pour les embeddings
- Réduisez le nombre de documents
- Utilisez un modèle d'embedding plus léger

## Exemples de documents à ajouter

- OWASP Top 10
- NIST Cybersecurity Framework
- CIS Controls
- CVE databases
- Guides de mitigation spécifiques (DDoS, SQL injection, etc.)
- Documentation firewall/IDS
- Playbooks de réponse aux incidents
