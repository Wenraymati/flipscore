import httpx
import logging
import statistics
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
from duckduckgo_search import DDGS

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
                    logger.warning("MercadoLibre API 403 Forbidden. Is User-Agent blocked? Trying Web Search Backup.")
                    return self._search_web_backup(clean_q)
                
                response.raise_for_status()
                data = response.json()
                
                items = data.get("results", [])
                if not items:
                    logger.info("Direct API found nothing. Trying Web Search Backup.")
                    return self._search_web_backup(clean_q)
                
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

    def _search_web_backup(self, query: str) -> Dict:
        """Fallback: Busca precios en la web usando DuckDuckGo."""
        try:
            logger.info(f"Iniciando Web Search Backup para: {query}")
            results = DDGS().text(f"precio {query} site:mercadolibre.cl OR site:chileautos.cl OR site:yapo.cl", region="cl-es", max_results=15)
            
            prices = []
            
            # Regex simple para encontrar precios tipo $ 5.000.000 o 5.000.000
            # Busca patrones como "$ 1.200.300", "$1.200.000", "1.500.000"
            price_pattern = re.compile(r'[\$\s]*(\d{1,3}(?:\.\d{3})*)')
            
            for r in results:
                title = r.get('title', '')
                body = r.get('body', '')
                text = f"{title} {body}"
                
                # Ignorar si parece ser un accesorio barato
                if "funda" in text.lower() or "carcasa" in text.lower():
                    continue

                matches = price_pattern.findall(text)
                for m in matches:
                    # Limpiar puntos y convertir a int
                    try:
                        clean_price = int(m.replace('.', ''))
                        # Filtro heurístico: Precios 'razonables' para ser el producto principal
                        # Ej: evitar precios de $1.000 o $990 (accesorios/envío)
                        if clean_price > 5000: 
                            prices.append(clean_price)
                    except:
                        pass
            
            if not prices:
                logger.warning("Web Search Backup returned no valid prices.")
                return self._empty_stats()
                
            stats = {
                "source": "Web Search (Backup)",
                "count": len(prices),
                "min": min(prices),
                "max": max(prices),
                "avg": int(statistics.mean(prices)),
                "median": int(statistics.median(prices)),
                "prices_sample": sorted(prices)[:5],
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Web Search success: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Web Search Backup failed: {e}")
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
