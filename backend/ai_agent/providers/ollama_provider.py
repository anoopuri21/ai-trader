"""
Ollama AI Provider - Offline/local AI that runs on your machine
No API key needed, unlimited usage
"""

import logging
from typing import Optional, Dict, Any
import json
import httpx

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama provider - runs locally, no cloud needed"""
    
    PROVIDER_NAME = "ollama"
    DEFAULT_MODEL = "llama3.1"
    BASE_URL = "http://localhost:11434"
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or self.BASE_URL
        self.model = model or self.DEFAULT_MODEL
        self.available = False
        self._check_available()
    
    def _check_available(self):
        """Check if Ollama is running locally"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(self.model in m for m in model_names):
                    self.available = True
                    logger.info(f"Ollama available with model: {self.model}")
                else:
                    logger.info(f"Ollama running but model {self.model} not found. Available: {model_names}")
                    if model_names:
                        self.model = model_names[0].split(":")[0]
                        self.available = True
            else:
                logger.debug("Ollama not responding")
        except Exception:
            logger.debug("Ollama not available (not running locally)")
    
    async def analyze(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Send analysis request to local Ollama"""
        if not self.available:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"Respond ONLY with valid JSON. {prompt}",
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 2000,
                        }
                    },
                    timeout=120  # Local models can be slower
                )
                
                if response.status_code == 200:
                    content = response.json().get("response", "")
                    
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        import re
                        json_match = re.search(r'\{[\s\S]*\}', content)
                        if json_match:
                            return json.loads(json_match.group())
                        return {"raw_response": content, "provider": self.PROVIDER_NAME}
                
                return None
                
        except Exception as e:
            logger.error(f"Ollama analysis error: {e}")
            return None
    
    def get_status(self) -> Dict:
        return {
            "provider": self.PROVIDER_NAME,
            "available": self.available,
            "model": self.model,
            "speed": "local",
            "url": self.base_url
        }
