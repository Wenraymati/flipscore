import httpx
import logging
import statistics
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class PriceClient:
    """Cliente para obtener precios de mercado en tiempo real (MercadoLibre Chile)."""
    
    BASE_URL = "https://api.mercadolibre.com/sites/MLC/search"
    
    
    def __init__(self, access_token: Optional[str] = None):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
            
        self._cache = {} # Key: query, Value: (timestamp, data)
        self._cache_ttl = timedelta(hours=1)
        
    def _clean_query(self, query: str) -> str:
        """Limpia la query de spam y palabras irrelevantes."""
        # Palabras a eliminar
        stop_words = ["vendo", "compro", "busco", "usado", "nuevo", "barato", "oferta", "excelente", "estado", "buen", "permuto"]
        
        # Normalizar
        clean = query.lower()
        for word in stop_words:
            clean = re.sub(r'\b' + word + r'\b', '', clean)
            
        # Quitar caracteres especiales y espacios extra
        clean = re.sub(r'[^\w\s]', '', clean)
        return " ".join(clean.split())

    async def fetch_market_data(self, product_name: str, limit: int = 20) -> Dict:
        """
        Busca productos usados en ML y calcula estadísticas.
        """
        """
        try:
            # 0. Limpiar query
            clean_q = self._clean_query(product_name)
            if len(clean_q) < 3: clean_q = product_name # Revertir si borramos todo

            # 1. Check Cache
            cached = self._cache.get(clean_q)
            if cached:
                ts, data = cached
                if datetime.now() - ts < self._cache_ttl:
                    logger.info(f"Cache hit for '{clean_q}'")
                    return data

            params = {
                "q": clean_q,
                "condition": "used",
                "limit": limit,
                #"sort": "price_asc" # Optional: get cheapest first?
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, headers=self.headers, timeout=10.0)
                
                if response.status_code == 403:
                    logger.warning("MercadoLibre API 403 Forbidden. Is User-Agent blocked?")
                    return self._empty_stats()
                
                response.raise_for_status()
                data = response.json()
                
                items = data.get("results", [])
                if not items:
                    return self._empty_stats()
                
                # Extract prices
                prices = [item["price"] for item in items if item.get("currency_id") == "CLP"]
                
                if not prices:
                    return self._empty_stats()
                
                # Calculate stats
                stats = {
                    "source": "MercadoLibre Chile (Used)",
                    "count": len(prices),
                    "min": min(prices),
                    "max": max(prices),
                    "avg": int(statistics.mean(prices)),
                    "median": int(statistics.median(prices)),
                    "prices_sample": sorted(prices)[:5], # Cheapest 5
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Market data for '{clean_q}': {stats['count']} items, median={stats['median']}")
                
                # Update Cache
                self._cache[clean_q] = (datetime.now(), stats)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error fetching market prices for {product_name}: {e}")
            return self._empty_stats()

    def _empty_stats(self) -> Dict:
        return {
            "source": "N/A", 
            "count": 0, 
            "min": 0, 
            "max": 0, 
            "avg": 0, 
            "median": 0,
            "error": "No data found or API error"
        }
