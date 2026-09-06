"""
AI Router - Routes requests to best available AI provider
Handles fallback chain: OmniRoute (356 providers via one gateway) -> Groq -> Cohere -> HuggingFace -> Ollama -> Rule-based

OmniRoute reference: https://github.com/diegosouzapw/OmniRoute
  - Unified OpenAI-compatible gateway (default http://localhost:20128/v1)
  - Auto-combo routing, fallback, resilience across 356 providers
  - Configure via OMNIROUTE_API_KEY / OMNIROUTE_BASE_URL / OMNIROUTE_MODEL
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
        from ai_agent.providers.omniroute_provider import OmniRouteProvider
        
        # Initialize providers in priority order
        # OmniRoute first — when configured it multiplexes 356 providers behind one key
        try:
            self.providers['omniroute'] = OmniRouteProvider(
                api_key=getattr(settings, 'omniroute_api_key', None) or None,
                base_url=getattr(settings, 'omniroute_base_url', None) or None,
                model=getattr(settings, 'omniroute_model', None) or None,
            )
        except Exception as e:
            logger.warning(f"OmniRoute provider init failed: {e}")
            # Fallback dummy
            class _Dummy:
                available = False
                def get_status(self): return {"provider": "omniroute", "available": False, "model": "auto", "error": str(e)}
                async def analyze(self, *a, **kw): return None
            self.providers['omniroute'] = _Dummy()

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
        
        # Build priority order from settings or default (omniroute first = 356 providers)
        priority_str = getattr(settings, 'ai_priority', 'omniroute,groq,cohere,huggingface,ollama')
        self.priority_order = [p.strip().lower() for p in priority_str.split(',') if p.strip()]
        # Validate: keep only known providers
        known = set(self.providers.keys())
        self.priority_order = [p for p in self.priority_order if p in known]
        if not self.priority_order:
            self.priority_order = [k for k in ['omniroute', 'groq', 'cohere', 'huggingface', 'ollama'] if k in known]
        
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
                # OmniRoute uses dynamic model (auto), report actual model
                result['_model'] = getattr(provider, 'MODEL', getattr(provider, 'model', 'unknown'))
                # Surface OmniRoute routing trace if present
                if provider_name == 'omniroute' and result.get('_omni_decision'):
                    logger.info(f"Analysis completed by omniroute ({result.get('_omni_decision')})")
                else:
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
