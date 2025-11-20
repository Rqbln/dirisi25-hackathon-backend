"""Wrapper LLM pour OVH AI Endpoints compatible avec LangChain."""

import os
from openai import OpenAI
from langchain_core.language_models.llms import LLM
from typing import Optional, List


class OVH_LLM(LLM):
    """LLM OVH AI Endpoints (Qwen2.5-Coder) compatible avec LangChain."""
    
    model: str = "Qwen2.5-Coder-32B-Instruct"
    base_url: str = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
    temperature: float = 0.3
    max_tokens: int = 2048
    client: Optional[OpenAI] = None

    def model_post_init(self, __context):
        """Initialise le client OpenAI après validation Pydantic."""
        # Récupérer la clé API depuis la variable d'environnement
        # Même si elle est None ou vide, initialiser quand même le client
        # car OVH AI Endpoints peut utiliser une auth alternative
        api_key = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN")
        
        # Initialiser le client (même si api_key est None)
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=api_key
        )
        
        print(f"🔧 OVH_LLM initialisé - API Key présente: {api_key is not None and len(api_key) > 0 if api_key else False}")

    @property
    def _llm_type(self) -> str:
        return "ovh_openai"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Appel au LLM OVH."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erreur lors de l'appel à l'API OVH: {str(e)}"
