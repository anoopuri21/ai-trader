"""
Groq AI Provider - Fastest free AI for trading analysis
Uses Llama 3.1 70B via Groq's free API
"""

import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class GroqProvider:
    """Groq AI provider - fastest free inference"""
    
    PROVIDER_NAME = "groq"
    MODEL = "llama-3.1-70b-versatile"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None
        self.available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Groq client"""
        if not self.api_key:
            logger.debug("Groq API key not provided")
            return
        
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            self.available = True
            logger.info("Groq provider initialized")
        except ImportError:
            logger.warning("Groq SDK not installed. Run: pip install groq")
        except Exception as e:
            logger.warning(f"Groq initialization failed: {e}")
    
    async def analyze(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Send analysis request to Groq"""
        if not self.available or not self.client:
            return None
        
        try:
            # Run synchronous Groq call in executor for async compatibility
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {"role": "system", "content": "You are ARTH, an expert AI trading analyst for Indian stock markets. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Groq returned invalid JSON: {e}")
            # Try to extract JSON from response
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
            return None
        except Exception as e:
            logger.error(f"Groq analysis error: {e}")
            return None
    
    def get_status(self) -> Dict:
        return {
            "provider": self.PROVIDER_NAME,
            "available": self.available,
            "model": self.MODEL,
            "speed": "fast"
        }
