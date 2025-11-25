"""Wrapper LLM pour Google Gemini compatible avec LangChain."""

import os
from google import genai
from langchain_core.language_models.llms import LLM
from typing import Optional, List


class GeminiLLM(LLM):
    """LLM Google Gemini compatible avec LangChain."""

    model: str = "gemini-2.5-flash"
    temperature: float = 0.3
    max_tokens: int = 2048
    client: Optional[genai.Client] = None

    def model_post_init(self, __context):
        """Initialise le client Gemini après validation Pydantic."""
        # Récupérer la clé API depuis la variable d'environnement
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY non trouvée dans les variables d'environnement. "
                "Veuillez définir votre clé API Gemini dans le fichier .env"
            )

        # Initialiser le client Gemini
        self.client = genai.Client(api_key=api_key)

        print(f"🔧 GeminiLLM initialisé - Modèle: {self.model}")

    @property
    def _llm_type(self) -> str:
        return "google_gemini"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """Appel au LLM Gemini."""
        try:
            # Configuration de génération
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

            # Appel à l'API Gemini
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=generation_config
            )

            return response.text
        except Exception as e:
            return f"Erreur lors de l'appel à l'API Gemini: {str(e)}"
