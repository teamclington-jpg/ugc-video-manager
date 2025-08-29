"""
Product Matcher Module
Matches products from video analysis to Coupang/shopping links using Google Images
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
import hashlib
import re

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("product_matcher")

class ProductMatcher:
    """Matches products to shopping links using Google Custom Search"""
    
    def __init__(self):
        """Initialize Product Matcher"""
        self.db = get_db_manager()
        # settings.py 정의에 맞춘 환경 변수명 사용
        self.google_api_key = settings.google_api_key
        self.search_engine_id = settings.google_search_engine_id
        self.coupang_patterns = self._init_coupang_patterns()
        self.cache = {}  # Simple in-memory cache
        logger.info("Product Matcher initialized")
    
    def _init_coupang_patterns(self) -> List[re.Pattern]:
        """Initialize Coupang URL patterns"""
        return [
            re.compile(r'coupang\.com/vp/products/(\d+)'),
            re.compile(r'link\.coupang\.com/a/(\w+)'),
            re.compile(r'coupa\.ng/(\w+)'),
            re.compile(r'coupang\.com.*productId=(\d+)')
        ]
    
    async def match_products(
        self,
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Match products from analysis to shopping links
        
        Args:
            analysis_results: Video analysis results
            
        Returns:
            Product matching results with links
        """
        try:
            products = analysis_results.get("products", [])
            
            if not products:
                logger.info("No products to match")
                return {"matched_products": [], "coupang_links": []}
            
            matched_products = []
            coupang_links = []
            
            # Process each product
            for product in products[:3]:  # Limit to top 3 products
                product_info = await self._match_single_product(product)
                
                if product_info:
                    matched_products.append(product_info)
                    
                    if product_info.get("coupang_url"):
                        coupang_links.append({
                            "product_name": product_info["name"],
                            "url": product_info["coupang_url"],
                            "price_info": product_info.get("price_info")
                        })
            
            return {
                "matched_products": matched_products,
                "coupang_links": coupang_links,
                "total_matched": len(matched_products)
            }
            
        except Exception as e:
            logger.error(f"Error matching products: {e}")
            return {"matched_products": [], "coupang_links": []}
    
    async def _match_single_product(
        self,
        product: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Match a single product to shopping links
        
        Args:
            product: Product information
            
        Returns:
            Matched product info with links
        """
        try:
            product_name = product.get("name", "")
            brand = product.get("brand", "")
            category = product.get("category", "")
            
            if not product_name:
                return None
            
            # Check cache first
            cache_key = self._get_cache_key(product_name, brand)
            if cache_key in self.cache:
                logger.info(f"Using cached result for {product_name}")
                return self.cache[cache_key]
            
            # Search for product
            search_results = await self._search_product(
                product_name,
                brand,
                category
            )
            
            # Find Coupang links
            coupang_url = None
            price_info = None
            
            for result in search_results:
                url = result.get("link", "")
                if self._is_coupang_url(url):
                    coupang_url = url
                    price_info = await self._extract_price_info(result)
                    break
            
            # If no direct Coupang link, search specifically for Coupang
            if not coupang_url and search_results:
                coupang_url = await self._search_coupang_specific(
                    product_name,
                    brand
                )
            
            product_info = {
                "name": product_name,
                "brand": brand,
                "category": category,
                "coupang_url": coupang_url,
                "alternative_links": self._get_alternative_links(search_results),
                "price_info": price_info,
                "image_url": self._get_product_image(search_results)
            }
            
            # Cache result
            self.cache[cache_key] = product_info
            
            return product_info
            
        except Exception as e:
            logger.error(f"Error matching product {product}: {e}")
            return None
    
    async def _search_product(
        self,
        product_name: str,
        brand: str = "",
        category: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search for product using Google Custom Search API
        
        Args:
            product_name: Product name
            brand: Brand name
            category: Product category
            
        Returns:
            Search results
        """
        if not self.google_api_key or not self.search_engine_id:
            logger.warning("Google Search API not configured")
            return self._get_mock_search_results(product_name)
        
        try:
            # Build search query
            query_parts = [product_name]
            if brand:
                query_parts.append(brand)
            query_parts.append("쿠팡")  # Add Coupang to increase relevance
            
            query = " ".join(query_parts)
            
            # Google Custom Search API URL
            url = "https://www.googleapis.com/customsearch/v1"
            
            params = {
                "key": self.google_api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": 10,
                "searchType": "image" if category in ["beauty", "fashion"] else None,
                "gl": "kr",  # Korea
                "hl": "ko"   # Korean
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("items", [])
                    else:
                        logger.error(f"Search API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error searching product: {e}")
            return self._get_mock_search_results(product_name)
    
    async def _search_coupang_specific(
        self,
        product_name: str,
        brand: str = ""
    ) -> Optional[str]:
        """
        Search specifically for Coupang product URL
        
        Args:
            product_name: Product name
            brand: Brand name
            
        Returns:
            Coupang URL if found
        """
        try:
            # Build Coupang search URL
            query = f"{brand} {product_name}" if brand else product_name
            encoded_query = quote_plus(query)
            
            # Coupang search URL format
            coupang_search_url = f"https://www.coupang.com/np/search?q={encoded_query}"
            
            # For now, return the search URL
            # In production, you'd want to scrape or use Coupang Partners API
            return coupang_search_url
            
        except Exception as e:
            logger.error(f"Error searching Coupang: {e}")
            return None
    
    def _is_coupang_url(self, url: str) -> bool:
        """Check if URL is a Coupang URL"""
        return any(pattern.search(url) for pattern in self.coupang_patterns)
    
    async def _extract_price_info(self, search_result: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extract price information from search result
        
        Args:
            search_result: Search result item
            
        Returns:
            Price information if available
        """
        try:
            # Try to extract from snippet
            snippet = search_result.get("snippet", "")
            
            # Look for price patterns
            price_patterns = [
                re.compile(r'(\d{1,3}(?:,\d{3})*)\s*원'),
                re.compile(r'₩\s*(\d{1,3}(?:,\d{3})*)'),
                re.compile(r'가격\s*:\s*(\d{1,3}(?:,\d{3})*)')
            ]
            
            for pattern in price_patterns:
                match = pattern.search(snippet)
                if match:
                    return {
                        "price": match.group(1),
                        "currency": "KRW",
                        "source": "search_snippet"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price: {e}")
            return None
    
    def _get_alternative_links(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Get alternative shopping links from search results"""
        alternative_links = []
        
        shopping_domains = [
            "11st.co.kr", "gmarket.co.kr", "auction.co.kr",
            "tmon.co.kr", "wemakeprice.com", "ssg.com",
            "kurly.com", "ohou.se", "oliveyoung.co.kr"
        ]
        
        for result in search_results[:5]:
            link = result.get("link", "")
            if any(domain in link for domain in shopping_domains):
                alternative_links.append(link)
        
        return alternative_links[:3]  # Limit to 3 alternatives
    
    def _get_product_image(self, search_results: List[Dict[str, Any]]) -> Optional[str]:
        """Get product image URL from search results"""
        for result in search_results:
            if result.get("pagemap", {}).get("cse_image"):
                images = result["pagemap"]["cse_image"]
                if images and images[0].get("src"):
                    return images[0]["src"]
        return None
    
    def _get_cache_key(self, product_name: str, brand: str) -> str:
        """Generate cache key for product"""
        key_string = f"{product_name}_{brand}".lower()
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_mock_search_results(self, product_name: str) -> List[Dict[str, Any]]:
        """Get mock search results for testing"""
        return [
            {
                "title": f"{product_name} - 쿠팡",
                "link": f"https://www.coupang.com/np/search?q={quote_plus(product_name)}",
                "snippet": f"{product_name} 최저가 29,900원 무료배송",
                "pagemap": {
                    "cse_image": [{
                        "src": "https://via.placeholder.com/300x300"
                    }]
                }
            },
            {
                "title": f"{product_name} - 11번가",
                "link": f"https://www.11st.co.kr/search?q={quote_plus(product_name)}",
                "snippet": f"{product_name} 특가 판매중"
            }
        ]
    
    async def generate_infocrlink(
        self,
        coupang_url: str,
        channel_id: str
    ) -> Optional[str]:
        """
        Generate Infocrlink (affiliate link) for channel
        
        Args:
            coupang_url: Original Coupang URL
            channel_id: YouTube channel ID
            
        Returns:
            Infocrlink URL if configured
        """
        try:
            # Get channel's Infocrlink configuration
            query = """
            SELECT 
                c.infocrlink_url,
                i.infocrlink_type,
                i.commission_rate
            FROM youtube_channels c
            LEFT JOIN infocrlink_mapping i ON c.id = i.channel_id
            WHERE c.id = %s AND i.is_active = true
            """
            
            result = await self.db.execute_query(query, (channel_id,))
            
            if result and result.data:
                infocrlink_base = result.data[0].get("infocrlink_url")
                
                if infocrlink_base:
                    # Format Infocrlink URL
                    # This is a simplified version - actual implementation
                    # would depend on Coupang Partners API format
                    return f"{infocrlink_base}?url={quote_plus(coupang_url)}"
            
            return coupang_url  # Return original URL if no Infocrlink
            
        except Exception as e:
            logger.error(f"Error generating Infocrlink: {e}")
            return coupang_url
    
    async def save_product_match(
        self,
        queue_id: str,
        matched_products: List[Dict[str, Any]]
    ) -> bool:
        """
        Save product match results to database
        
        Args:
            queue_id: Upload queue ID
            matched_products: Matched product information
            
        Returns:
            Success status
        """
        try:
            # Update upload_queue with product match data
            infocrlink_data = {
                "matched_products": matched_products,
                "match_timestamp": datetime.now().isoformat(),
                "match_count": len(matched_products)
            }
            
            query = """
            UPDATE upload_queue
            SET 
                infocrlink_data = %s,
                coupang_url = %s,
                updated_at = NOW()
            WHERE id = %s
            """
            
            # Get primary Coupang URL
            primary_url = None
            if matched_products and matched_products[0].get("coupang_url"):
                primary_url = matched_products[0]["coupang_url"]
            
            await self.db.execute_query(
                query,
                (json.dumps(infocrlink_data), primary_url, queue_id)
            )
            
            logger.info(f"Saved product match for queue {queue_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving product match: {e}")
            return False

# Global matcher instance
_matcher: Optional[ProductMatcher] = None

def get_product_matcher() -> ProductMatcher:
    """Get or create global product matcher"""
    global _matcher
    if _matcher is None:
        _matcher = ProductMatcher()
    return _matcher