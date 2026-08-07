"""
HuggingFace AI Provider - Vision models and free inference
"""

import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class HuggingFaceProvider:
    """HuggingFace provider - free inference API"""
    
    PROVIDER_NAME = "huggingface"
    MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize HuggingFace client"""
        if not self.api_key:
            logger.debug("HuggingFace API key not provided")
            return
        
        try:
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(token=self.api_key)
            self.available = True
            logger.info("HuggingFace provider initialized")
        except ImportError:
            logger.warning("huggingface_hub not installed. Run: pip install huggingface-hub")
        except Exception as e:
            logger.warning(f"HuggingFace initialization failed: {e}")
    
    async def analyze(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Send analysis request to HuggingFace"""
        if not self.available:
            return None
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.text_generation(
                    prompt=f"<s>[INST] You are ARTH, an expert AI trading analyst. Respond ONLY with valid JSON.\n\n{prompt} [/INST]",
                    model=self.MODEL,
                    max_new_tokens=2000,
                    temperature=temperature,
                    return_full_text=False,
                )
            )
            
            content = response.strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
                return {"raw_response": content, "provider": self.PROVIDER_NAME}
            
        except Exception as e:
            logger.error(f"HuggingFace analysis error: {e}")
            return None
    
    def get_status(self) -> Dict:
        return {
            "provider": self.PROVIDER_NAME,
            "available": self.available,
            "model": self.MODEL,
            "speed": "medium"
        }
