"""
Cohere AI Provider - Good for chart analysis and detailed reasoning
Uses Command R via Cohere's free API
"""

import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class CohereProvider:
    """Cohere AI provider - good reasoning capabilities"""
    
    PROVIDER_NAME = "cohere"
    MODEL = "command-r"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None
        self.available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Cohere client"""
        if not self.api_key:
            logger.debug("Cohere API key not provided")
            return
        
        try:
            import cohere
            self.client = cohere.Client(self.api_key)
            self.available = True
            logger.info("Cohere provider initialized")
        except ImportError:
            logger.warning("Cohere SDK not installed. Run: pip install cohere")
        except Exception as e:
            logger.warning(f"Cohere initialization failed: {e}")
    
    async def analyze(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Send analysis request to Cohere"""
        if not self.available or not self.client:
            return None
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat(
                    model=self.MODEL,
                    message=prompt,
                    temperature=temperature,
                )
            )
            
            content = response.text
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
                # Return as structured text
                return {"raw_response": content, "provider": self.PROVIDER_NAME}
            
        except Exception as e:
            logger.error(f"Cohere analysis error: {e}")
            return None
    
    def get_status(self) -> Dict:
        return {
            "provider": self.PROVIDER_NAME,
            "available": self.available,
            "model": self.MODEL,
            "speed": "medium"
        }
