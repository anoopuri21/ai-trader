"""
AI Router - Routes requests to best available AI provider
Handles fallback chain: Groq -> Cohere -> HuggingFace -> Ollama -> Rule-based
"""

import logging
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)


class AIRouter:
    """Routes AI requests to the best available provider with fallback"""
    
    def __init__(self):
        self.providers = {}
        self.priority_order = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available AI providers"""
        from ai_agent.providers.groq_provider import GroqProvider
        from ai_agent.providers.cohere_provider import CohereProvider
        from ai_agent.providers.huggingface_provider import HuggingFaceProvider
        from ai_agent.providers.ollama_provider import OllamaProvider
        
        # Initialize providers in priority order
        self.providers['groq'] = GroqProvider(
            api_key=getattr(settings, 'groq_api_key', None) or None
        )
        self.providers['cohere'] = CohereProvider(
            api_key=getattr(settings, 'cohere_api_key', None) or None
        )
        self.providers['huggingface'] = HuggingFaceProvider(
            api_key=getattr(settings, 'huggingface_api_key', None) or None
        )
        self.providers['ollama'] = OllamaProvider()
        
        # Build priority order from settings or default
        priority_str = getattr(settings, 'ai_priority', 'groq,cohere,huggingface,ollama')
        self.priority_order = [p.strip() for p in priority_str.split(',')]
        
        # Log availability
        for name, provider in self.providers.items():
            status = "✅" if provider.available else "❌"
            logger.info(f"  {status} {name}: {'available' if provider.available else 'not available'}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [name for name, p in self.providers.items() if p.available]
    
    async def analyze(self, prompt: str, temperature: float = 0.3, 
                     preferred_provider: str = None) -> Optional[Dict[str, Any]]:
        """
        Route analysis to best available provider.
        Tries providers in priority order with fallback.
        Returns result with provider info added.
        """
        # Build try order
        if preferred_provider and preferred_provider in self.providers:
            order = [preferred_provider] + [p for p in self.priority_order if p != preferred_provider]
        else:
            order = self.priority_order
        
        # Try each provider
        for provider_name in order:
            provider = self.providers.get(provider_name)
            if not provider or not provider.available:
                continue
            
            logger.debug(f"Trying {provider_name} for analysis...")
            result = await provider.analyze(prompt, temperature)
            
            if result:
                result['_provider'] = provider_name
                result['_model'] = getattr(provider, 'MODEL', 'unknown')
                logger.info(f"Analysis completed by {provider_name}")
                return result
            
            logger.warning(f"{provider_name} failed, trying next...")
        
        logger.warning("All AI providers failed - will use rule-based fallback")
        return None
    
    def get_status(self) -> List[Dict]:
        """Get status of all providers"""
        return [p.get_status() for p in self.providers.values()]


# Singleton
ai_router = AIRouter()
