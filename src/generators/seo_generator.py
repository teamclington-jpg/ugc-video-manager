"""
SEO Generator Module
Generates optimized titles, descriptions, and tags for YouTube videos
"""

import asyncio
import random
from typing import Dict, List, Optional, Any
import re
from datetime import datetime

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("seo_generator")

class SEOGenerator:
    """Generates SEO-optimized content for YouTube videos"""
    
    def __init__(self):
        """Initialize SEO Generator"""
        self.title_templates = self._load_title_templates()
        self.description_templates = self._load_description_templates()
        self.trending_keywords = self._load_trending_keywords()
        self.emoji_map = self._load_emoji_map()
        logger.info("SEO Generator initialized")
    
    def _load_title_templates(self) -> Dict[str, List[str]]:
        """Load title templates by content type"""
        return {
            "review": [
                "{product} 리뷰 | 솔직 후기 {year}",
                "[{brand}] {product} 완벽 분석! 구매 전 필수 시청",
                "{product} {feature} 실사용 리뷰 | 장단점 총정리",
                "이거 실화? {product} {selling_point} 직접 써보니",
                "{product} vs 기대치 | 진짜 {mood} 리뷰"
            ],
            "unboxing": [
                "{product} 언박싱 | 첫인상 {mood}",
                "[개봉기] {brand} {product} 뭐가 들어있을까?",
                "{product} 언박싱 & 첫 사용기 | {feature}",
                "드디어 도착! {product} 개봉 리뷰",
                "{price}원 {product} 언박싱 | 가성비 {mood}"
            ],
            "tutorial": [
                "{product} 사용법 | 초보자 가이드",
                "{product} 활용 꿀팁 {count}가지",
                "[튜토리얼] {product} {feature} 마스터하기",
                "{product} 200% 활용법 | 숨겨진 기능들",
                "이렇게 쓰면 {product} 효과 2배!"
            ],
            "comparison": [
                "{product1} vs {product2} | 뭘 살까?",
                "[비교] {category} TOP {count} 완벽 분석",
                "{price}원대 {category} 비교 | 최종 승자는?",
                "{product} 대체품 {count}가지 비교분석",
                "가성비 대결! {category} 제품 비교"
            ],
            "haul": [
                "{category} 하울 | {price}원 쇼핑",
                "[{brand}] 대량구매 하울 & 리뷰",
                "{month}월 {category} 하울 | 득템 리스트",
                "{count}개 제품 하울 | {category} 쇼핑",
                "이번달 최고 득템! {category} 하울"
            ],
            "default": [
                "{product} | {feature} {mood}",
                "[{category}] {product} 소개",
                "{product} 추천 | {selling_point}",
                "신제품 {product} 첫인상",
                "{category} 추천템 | {product}"
            ]
        }
    
    def _load_description_templates(self) -> Dict[str, str]:
        """Load description templates by content type"""
        return {
            "review": """
{greeting}

오늘은 {product}의 리뷰를 준비했습니다!

📦 제품 정보
• 제품명: {product}
• 브랜드: {brand}
• 카테고리: {category}
• 특징: {features}

✨ 주요 포인트
{selling_points}

⏰ 타임스탬프
00:00 인트로
{timestamps}

🛍️ 구매 링크
{purchase_link}

{hashtags}

구독과 좋아요, 알림설정 부탁드려요! 💕
다음 영상에서 만나요~

#제품리뷰 #{category} #{product_tag}
""",
            "unboxing": """
{greeting}

드디어 도착한 {product} 언박싱!

📦 오늘의 언박싱
• {product} ({brand})
• 구매처: {purchase_info}
• 가격대: {price_range}

🎁 박스 구성품
{box_contents}

💭 첫인상
{first_impression}

🔗 관련 링크
{purchase_link}

{hashtags}

더 많은 언박싱 영상을 원하시면 구독 부탁드려요! 🔔

#언박싱 #개봉기 #{category}
""",
            "default": """
{greeting}

📌 영상 소개
{video_description}

🏷️ 제품 정보
• 제품: {product}
• 카테고리: {category}
• 특징: {features}

💡 핵심 내용
{key_points}

🔗 링크
{purchase_link}

{hashtags}

영상이 도움이 되셨다면 좋아요와 구독 부탁드려요! 😊

#{category} #추천 #리뷰
"""
        }
    
    def _load_trending_keywords(self) -> Dict[str, List[str]]:
        """Load trending keywords by category"""
        return {
            "technology": ["테크", "가젯", "신기술", "IT", "스마트", "혁신", "최신"],
            "beauty": ["뷰티", "화장품", "스킨케어", "메이크업", "K뷰티", "클린뷰티"],
            "fashion": ["패션", "스타일", "코디", "룩북", "트렌드", "데일리룩"],
            "food": ["먹방", "맛집", "요리", "레시피", "간편식", "신상", "편의점"],
            "lifestyle": ["라이프", "일상", "브이로그", "루틴", "꿀템", "인테리어"],
            "gaming": ["게임", "게이밍", "e스포츠", "플레이", "공략", "신작"],
            "general": ["추천", "리뷰", "후기", "꿀팁", "가성비", "신상품"]
        }
    
    def _load_emoji_map(self) -> Dict[str, List[str]]:
        """Load emoji mappings for different contexts"""
        return {
            "positive": ["✨", "🎉", "💕", "👍", "🔥", "⭐", "💯"],
            "surprise": ["😱", "🤯", "😲", "👀", "🎊", "💥", "⚡"],
            "tech": ["📱", "💻", "🖥️", "⌨️", "🖱️", "🎮", "🔌"],
            "beauty": ["💄", "💅", "👄", "💋", "🌸", "🌺", "✨"],
            "food": ["🍽️", "🥘", "🍜", "🍱", "🍔", "🍕", "☕"],
            "shopping": ["🛍️", "🛒", "💳", "💰", "🏪", "🎁", "📦"],
            "time": ["⏰", "⏱️", "🕐", "📅", "🗓️", "⌛", "⏳"],
            "link": ["🔗", "📎", "🔖", "📌", "🏷️", "🎯", "➡️"]
        }
    
    async def generate_seo_content(
        self,
        analysis_results: Dict[str, Any],
        channel_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete SEO content for a video
        
        Args:
            analysis_results: Video analysis results from Gemini
            channel_info: Optional channel information
            
        Returns:
            SEO content including title, description, tags
        """
        try:
            # Extract key information
            products = analysis_results.get("products", [])
            category = analysis_results.get("category", "general")
            content_type = analysis_results.get("content_type", "default")
            keywords = analysis_results.get("keywords", [])
            features = analysis_results.get("product_features", [])
            selling_points = analysis_results.get("selling_points", [])
            mood = analysis_results.get("mood", "neutral")
            
            # Generate title
            title = await self._generate_title(
                products, category, content_type, features, mood
            )
            
            # Generate description
            description = await self._generate_description(
                products, category, content_type, features, selling_points, channel_info
            )
            
            # Generate tags
            tags = await self._generate_tags(
                products, category, keywords, features
            )
            
            # Generate hashtags
            hashtags = await self._generate_hashtags(
                products, category, keywords
            )
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "hashtags": hashtags,
                "thumbnail_text": await self._generate_thumbnail_text(products, content_type)
            }
            
        except Exception as e:
            logger.error(f"Error generating SEO content: {e}")
            return self._get_fallback_content(analysis_results)
    
    async def _generate_title(
        self,
        products: List[Dict],
        category: str,
        content_type: str,
        features: List[str],
        mood: str
    ) -> str:
        """Generate SEO-optimized title"""
        try:
            # Get appropriate templates
            templates = self.title_templates.get(
                content_type,
                self.title_templates["default"]
            )
            
            # Select random template
            template = random.choice(templates)
            
            # Prepare substitution values
            product_name = products[0]["name"] if products else "신제품"
            brand_name = products[0].get("brand", "") if products else ""
            feature = features[0] if features else "특징"
            
            # Format title
            title = template.format(
                product=product_name,
                brand=brand_name,
                category=self._translate_category(category),
                feature=feature,
                mood=self._translate_mood(mood),
                year=datetime.now().year,
                month=datetime.now().month,
                count=random.choice([3, 5, 7, 10]),
                price=random.choice(["1만", "3만", "5만", "10만"]),
                selling_point=features[0] if features else "혁신",
                product1=product_name,
                product2="경쟁제품"
            )
            
            # Add emoji for engagement
            if random.random() > 0.5:
                emoji = random.choice(self.emoji_map.get(self._get_emoji_category(category), ["✨"]))
                title = f"{emoji} {title}"
            
            # Ensure title length is optimal (60-70 chars for Korean)
            if len(title) > 70:
                title = title[:67] + "..."
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return f"{products[0]['name'] if products else '제품'} 리뷰"
    
    async def _generate_description(
        self,
        products: List[Dict],
        category: str,
        content_type: str,
        features: List[str],
        selling_points: List[str],
        channel_info: Optional[Dict]
    ) -> str:
        """Generate SEO-optimized description"""
        try:
            # Get appropriate template
            template = self.description_templates.get(
                content_type,
                self.description_templates["default"]
            )
            
            # Prepare substitution values
            product_name = products[0]["name"] if products else "제품"
            brand_name = products[0].get("brand", "브랜드") if products else "브랜드"
            
            # Format features and selling points
            features_str = "\n".join(f"• {f}" for f in features[:5]) if features else "• 혁신적인 기능"
            selling_points_str = "\n".join(f"✓ {sp}" for sp in selling_points[:5]) if selling_points else "✓ 뛰어난 성능"
            
            # Generate timestamps (mock for now)
            timestamps = self._generate_timestamps(content_type)
            
            # Format description
            description = template.format(
                greeting=self._get_greeting(),
                product=product_name,
                brand=brand_name,
                category=self._translate_category(category),
                features=features_str,
                selling_points=selling_points_str,
                timestamps=timestamps,
                purchase_link="🔗 구매 링크는 고정댓글 확인!",
                hashtags=self._format_hashtags(await self._generate_hashtags(products, category, [])),
                purchase_info="공식 스토어",
                price_range="중저가",
                box_contents="• 본체\n• 설명서\n• 보증서",
                first_impression="기대 이상의 퀄리티!",
                video_description=f"{product_name}에 대한 상세 리뷰",
                key_points=selling_points_str,
                product_tag=product_name.replace(" ", "")
            )
            
            return description
            
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            return f"{products[0]['name'] if products else '제품'} 소개 영상입니다."
    
    async def _generate_tags(
        self,
        products: List[Dict],
        category: str,
        keywords: List[str],
        features: List[str]
    ) -> List[str]:
        """Generate YouTube tags"""
        tags = []
        
        try:
            # Add product names
            for product in products[:3]:
                tags.append(product["name"])
                if product.get("brand"):
                    tags.append(product["brand"])
            
            # Add category tags
            tags.append(self._translate_category(category))
            tags.extend(self.trending_keywords.get(category, [])[:5])
            
            # Add keywords from analysis
            tags.extend(keywords[:10])
            
            # Add feature tags
            for feature in features[:5]:
                tags.append(feature)
            
            # Add common engagement tags
            common_tags = [
                "리뷰", "후기", "추천", "언박싱", "사용기",
                "꿀팁", "가성비", "신상", "할인", "세일",
                f"{datetime.now().year}", f"{datetime.now().year}년",
                "한국", "korean", "review"
            ]
            tags.extend(random.sample(common_tags, min(5, len(common_tags))))
            
            # Remove duplicates and limit
            tags = list(dict.fromkeys(tags))[:30]  # YouTube allows max 500 chars total
            
            return tags
            
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return ["리뷰", category, "추천"]
    
    async def _generate_hashtags(
        self,
        products: List[Dict],
        category: str,
        keywords: List[str]
    ) -> List[str]:
        """Generate hashtags for description"""
        hashtags = []
        
        try:
            # Primary hashtags
            if products:
                hashtags.append(f"#{products[0]['name'].replace(' ', '')}")
                if products[0].get("brand"):
                    hashtags.append(f"#{products[0]['brand'].replace(' ', '')}")
            
            # Category hashtag
            hashtags.append(f"#{self._translate_category(category)}")
            
            # Keyword hashtags
            for keyword in keywords[:5]:
                hashtags.append(f"#{keyword.replace(' ', '')}")
            
            # Trending hashtags
            trending = ["#리뷰", "#추천", "#신상", f"#{datetime.now().year}"]
            hashtags.extend(random.sample(trending, 2))
            
            # Remove duplicates
            hashtags = list(dict.fromkeys(hashtags))[:15]
            
            return hashtags
            
        except Exception as e:
            logger.error(f"Error generating hashtags: {e}")
            return ["#리뷰", "#추천"]
    
    async def _generate_thumbnail_text(
        self,
        products: List[Dict],
        content_type: str
    ) -> Dict[str, str]:
        """Generate text overlay suggestions for thumbnail"""
        try:
            product_name = products[0]["name"] if products else "신제품"
            
            thumbnail_texts = {
                "review": [
                    f"{product_name}\n솔직 리뷰",
                    "살까? 말까?",
                    "진짜 후기"
                ],
                "unboxing": [
                    f"{product_name}\n언박싱",
                    "뭐가 들었을까?",
                    "개봉기"
                ],
                "tutorial": [
                    "이렇게 쓰세요!",
                    f"{product_name}\n사용법",
                    "꿀팁 대방출"
                ],
                "comparison": [
                    "VS",
                    "뭐가 더 좋을까?",
                    "비교분석"
                ],
                "default": [
                    product_name,
                    "추천템",
                    "Must Have"
                ]
            }
            
            texts = thumbnail_texts.get(content_type, thumbnail_texts["default"])
            
            return {
                "main_text": random.choice(texts),
                "sub_text": random.choice(["꼭 보세요!", "충격적", "대박", "리얼", "진짜"]),
                "emoji": random.choice(self.emoji_map["positive"] + self.emoji_map["surprise"])
            }
            
        except Exception as e:
            logger.error(f"Error generating thumbnail text: {e}")
            return {"main_text": "리뷰", "sub_text": "", "emoji": ""}
    
    def _translate_category(self, category: str) -> str:
        """Translate category to Korean"""
        translations = {
            "technology": "테크",
            "tech": "테크",
            "beauty": "뷰티",
            "fashion": "패션",
            "food": "푸드",
            "lifestyle": "라이프스타일",
            "gaming": "게이밍",
            "sports": "스포츠",
            "home": "홈/리빙",
            "kids": "키즈",
            "pet": "펫",
            "travel": "여행",
            "general": "일반"
        }
        return translations.get(category.lower(), category)
    
    def _translate_mood(self, mood: str) -> str:
        """Translate mood to Korean expression"""
        translations = {
            "energetic": "에너지 넘치는",
            "calm": "차분한",
            "professional": "전문적인",
            "casual": "캐주얼한",
            "fun": "재미있는",
            "neutral": "일반적인"
        }
        return translations.get(mood.lower(), "특별한")
    
    def _get_emoji_category(self, category: str) -> str:
        """Map category to emoji category"""
        mapping = {
            "technology": "tech",
            "tech": "tech",
            "beauty": "beauty",
            "food": "food",
            "shopping": "shopping"
        }
        return mapping.get(category.lower(), "positive")
    
    def _get_greeting(self) -> str:
        """Get random greeting"""
        greetings = [
            "안녕하세요 여러분! 👋",
            "안녕하세요~ 오늘도 찾아주셔서 감사합니다!",
            "구독자 여러분 안녕하세요!",
            "여러분 반갑습니다!",
            "안녕하세요! 오늘은 특별한 제품을 준비했어요~"
        ]
        return random.choice(greetings)
    
    def _generate_timestamps(self, content_type: str) -> str:
        """Generate mock timestamps"""
        timestamps_map = {
            "review": "00:30 제품 소개\n01:00 언박싱\n02:00 실사용 테스트\n05:00 장단점 정리\n07:00 총평",
            "unboxing": "00:30 박스 개봉\n01:00 구성품 확인\n02:30 첫인상\n04:00 간단 테스트",
            "tutorial": "00:30 준비물\n01:00 Step 1\n03:00 Step 2\n05:00 팁 & 주의사항",
            "comparison": "00:30 제품 소개\n01:30 스펙 비교\n03:00 실사용 비교\n06:00 결론",
            "default": "00:30 시작\n02:00 메인 내용\n05:00 마무리"
        }
        return timestamps_map.get(content_type, timestamps_map["default"])
    
    def _format_hashtags(self, hashtags: List[str]) -> str:
        """Format hashtags for description"""
        return " ".join(hashtags)
    
    def _get_fallback_content(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback SEO content when generation fails"""
        products = analysis_results.get("products", [])
        product_name = products[0]["name"] if products else "제품"
        
        return {
            "title": f"{product_name} 리뷰",
            "description": f"{product_name}에 대한 상세 리뷰 영상입니다.\n\n구독과 좋아요 부탁드려요!",
            "tags": ["리뷰", "추천", product_name],
            "hashtags": ["#리뷰", "#추천", f"#{product_name.replace(' ', '')}"],
            "thumbnail_text": {
                "main_text": product_name,
                "sub_text": "리뷰",
                "emoji": "✨"
            }
        }

# Global generator instance
_generator: Optional[SEOGenerator] = None

def get_seo_generator() -> SEOGenerator:
    """Get or create global SEO generator"""
    global _generator
    if _generator is None:
        _generator = SEOGenerator()
    return _generator