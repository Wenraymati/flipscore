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
            
        clean = re.sub(r'[^\w\s]', '', clean)
        return " ".join(clean.split())

    def _filter_outliers(self, prices: List[int]) -> List[int]:
        """Filtra precios usando Rango Intercuartil (IQR) para eliminar outliers."""
        if len(prices) < 4: return prices
        
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        q1 = sorted_prices[n // 4]
        q3 = sorted_prices[3 * n // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered = [x for x in prices if lower_bound <= x <= upper_bound]
        
        # Safety check: si borramos todo, devolvemos original (menos los muy bajos)
        return filtered if filtered else [p for p in prices if p > 5000]

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
                
                # Filtrar Outliers (Nuevo)
                prices_clean = self._filter_outliers(prices)
                if not prices_clean: 
                     prices_clean = prices # Revertir si filtramos todo agresivamente
                
                # Calculate stats
                stats = {
                    "source": "MercadoLibre Chile (Used)",
                    "count": len(prices_clean),
                    "min": min(prices_clean),
                    "max": max(prices_clean),
                    "avg": int(statistics.mean(prices_clean)),
                    "median": int(statistics.median(prices_clean)),
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
            # Query más amplia sin restricciones de sitio tan estrictas
            results = DDGS().text(f"{query} valor precio chile usado", region="cl-es", max_results=20)
            
            prices = []
            
            # Regex mejorado para capturar:
            # 1. $ 5.000.000 (standard)
            # 2. $5000000 (plain digits with symbol)
            # 3. 5.000.000 (dot separated without symbol)
            price_pattern = re.compile(r'(?:(?:\$|CLP|Valor|Precio)\s*(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,8})|(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?))', re.IGNORECASE)
            
            for r in results:
                title = r.get('title', '')
                body = r.get('body', '')
                text = f"{title} {body}"
                
                # Ignorar accesorios baratos
                if "funda" in text.lower() or "carcasa" in text.lower() or "mica" in text.lower():
                    continue

                matches = price_pattern.findall(text)
                for m in matches:
                    try:
                        # Extract non-empty group
                        raw_str = m[0] if m[0] else m[1]
                        
                        # Limpiar puntos y comas
                        clean_str = raw_str.replace('.', '').split(',')[0]
                        clean_price = int(clean_str)
                        
                        # Filtro heurístico:
                        if clean_price > 5000: 
                            prices.append(clean_price)
                    except:
                        pass
            
            # Filtrar outliers también en web search
            prices_clean = self._filter_outliers(prices) if prices else []
            
            if not prices_clean:
                logger.warning("Web Search Backup returned no valid prices (after filter).")
                return self._empty_stats()
                
            stats = {
                "source": "Web Search (Backup)",
                "count": len(prices_clean),
                "min": min(prices_clean),
                "max": max(prices_clean),
                "avg": int(statistics.mean(prices_clean)),
                "median": int(statistics.median(prices_clean)),
                "prices_sample": sorted(prices_clean)[:5],
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
