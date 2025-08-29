"""
Video Analyzer Module using Gemini Vision API
Analyzes video content to extract product information and generate metadata
"""

import asyncio
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import cv2
import google.generativeai as genai
from PIL import Image
import io

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("video_analyzer")

class GeminiVideoAnalyzer:
    """Analyzes videos using Google's Gemini Vision API"""
    
    def __init__(self):
        """Initialize Gemini API client"""
        self.api_key = settings.gemini_api_key
        if not self.api_key:
            logger.warning("Gemini API key not configured")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            # Use Gemini Pro Vision model for video/image analysis
            self.model = genai.GenerativeModel('gemini-pro-vision')
            logger.info("Gemini Vision API initialized")
    
    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze video content using Gemini Vision API
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Analysis results including products, category, keywords
        """
        if not self.model:
            logger.error("Gemini API not initialized")
            return self._get_mock_analysis(video_path)
        
        try:
            video_path = Path(video_path)
            logger.info(f"Analyzing video: {video_path.name}")
            
            # Extract key frames from video
            frames = await self.extract_key_frames(str(video_path))
            
            if not frames:
                logger.warning("No frames extracted from video")
                return self._get_mock_analysis(str(video_path))
            
            # Analyze frames with Gemini
            analysis_results = await self.analyze_frames_with_gemini(frames, video_path.name)

            # If Gemini returned an error, gracefully fall back to mock
            if not analysis_results or analysis_results.get("error"):
                logger.warning("Gemini analysis error; falling back to mock analysis")
                return self._get_mock_analysis(str(video_path))

            # Process and structure results
            structured_result = self.structure_analysis_results(analysis_results)

            # If confidence is still low, prefer mock to keep pipeline flowing
            if structured_result.get("confidence_score", 0.0) < 0.3:
                logger.warning("Analysis confidence too low; using mock analysis fallback")
                return self._get_mock_analysis(str(video_path))

            logger.info(f"Analysis complete for {video_path.name}")
            return structured_result
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return self._get_mock_analysis(str(video_path))
    
    async def extract_key_frames(self, video_path: str, num_frames: int = 5) -> List[Image.Image]:
        """
        Extract key frames from video
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract
            
        Returns:
            List of PIL Image objects
        """
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                logger.warning(f"No frames in video: {video_path}")
                return frames
            
            # Calculate frame intervals
            interval = max(1, total_frames // num_frames)
            
            for i in range(0, total_frames, interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Convert to PIL Image
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append(pil_image)
                    
                    if len(frames) >= num_frames:
                        break
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video")
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
        
        return frames
    
    async def analyze_frames_with_gemini(self, frames: List[Image.Image], video_name: str) -> Dict[str, Any]:
        """
        Send frames to Gemini Vision API for analysis
        
        Args:
            frames: List of PIL Image objects
            video_name: Name of the video file
            
        Returns:
            Raw analysis results from Gemini
        """
        try:
            # Prepare the prompt for product analysis
            prompt = """
            이 영상을 분석해서 다음 정보를 JSON 형식으로 추출해주세요:
            
            1. products: 영상에 나오는 제품 목록 (제품명, 브랜드, 카테고리)
            2. main_category: 영상의 주요 카테고리 (tech, beauty, fashion, food, lifestyle, gaming 중 선택)
            3. keywords: SEO를 위한 핵심 키워드 5-10개
            4. content_type: 콘텐츠 유형 (review, unboxing, tutorial, comparison, haul 중 선택)
            5. target_audience: 타겟 시청자 (연령대, 성별, 관심사)
            6. mood: 영상의 분위기 (energetic, calm, professional, casual, fun 중 선택)
            7. product_features: 강조되는 제품 특징들
            8. selling_points: 제품의 주요 판매 포인트
            
            JSON 형식으로만 응답해주세요. 추가 설명은 필요 없습니다.
            """
            
            # Send frames and prompt to Gemini
            response = self.model.generate_content([prompt] + frames)
            
            # Parse the response
            try:
                # Extract JSON from response text
                response_text = response.text
                # Find JSON content
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {"error": "No JSON found in response", "raw": response_text}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                result = {"error": str(e), "raw": response.text}
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {"error": str(e)}
    
    def structure_analysis_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the raw Gemini analysis results
        
        Args:
            raw_results: Raw results from Gemini API
            
        Returns:
            Structured analysis results
        """
        # Default structure
        structured = {
            "products": [],
            "category": "unknown",
            "keywords": [],
            "content_type": "unknown",
            "target_audience": {},
            "mood": "neutral",
            "product_features": [],
            "selling_points": [],
            "confidence_score": 0.0,
            "gemini_response": raw_results
        }
        
        try:
            if "error" not in raw_results:
                # Extract and validate each field
                structured["products"] = raw_results.get("products", [])
                structured["category"] = raw_results.get("main_category", "unknown")
                structured["keywords"] = raw_results.get("keywords", [])
                structured["content_type"] = raw_results.get("content_type", "unknown")
                structured["target_audience"] = raw_results.get("target_audience", {})
                structured["mood"] = raw_results.get("mood", "neutral")
                structured["product_features"] = raw_results.get("product_features", [])
                structured["selling_points"] = raw_results.get("selling_points", [])
                
                # Calculate confidence based on data completeness
                confidence = 0.0
                if structured["products"]:
                    confidence += 0.3
                if structured["category"] != "unknown":
                    confidence += 0.2
                if len(structured["keywords"]) >= 3:
                    confidence += 0.2
                if structured["content_type"] != "unknown":
                    confidence += 0.15
                if structured["product_features"]:
                    confidence += 0.15
                
                structured["confidence_score"] = min(1.0, confidence)
            else:
                logger.warning(f"Error in Gemini response: {raw_results.get('error')}")
                
        except Exception as e:
            logger.error(f"Error structuring results: {e}")
        
        return structured
    
    def _get_mock_analysis(self, video_path: str) -> Dict[str, Any]:
        """
        Return mock analysis for testing when API is not available
        
        Args:
            video_path: Path to video file
            
        Returns:
            Mock analysis results
        """
        video_name = Path(video_path).stem
        
        return {
            "products": [
                {"name": "테스트 제품", "brand": "샘플 브랜드", "category": "technology"}
            ],
            "category": "technology",
            "keywords": ["제품리뷰", "언박싱", "테크", "가젯", "신제품"],
            "content_type": "review",
            "target_audience": {
                "age_range": "20-35",
                "gender": "all",
                "interests": ["technology", "gadgets"]
            },
            "mood": "professional",
            "product_features": ["고성능", "휴대성", "디자인"],
            "selling_points": ["최신 기술", "합리적 가격", "사용 편의성"],
            "confidence_score": 0.5,
            "gemini_response": {"mock": True, "reason": "API not configured"}
        }
    
    async def generate_seo_content(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate SEO-optimized title and description based on analysis
        
        Args:
            analysis_results: Video analysis results
            
        Returns:
            SEO content including title and description
        """
        if not self.model:
            return self._get_mock_seo_content(analysis_results)
        
        try:
            products = analysis_results.get("products", [])
            keywords = analysis_results.get("keywords", [])
            features = analysis_results.get("product_features", [])
            
            prompt = f"""
            다음 정보를 바탕으로 유튜브 영상을 위한 SEO 최적화된 제목과 설명을 생성해주세요:
            
            제품: {products}
            키워드: {keywords}
            특징: {features}
            
            요구사항:
            1. 제목: 60자 이내, 클릭을 유도하는 매력적인 제목
            2. 설명: 500자 이내, 키워드를 자연스럽게 포함
            3. 해시태그: 관련 해시태그 10개
            
            JSON 형식으로 응답:
            {{
                "title": "제목",
                "description": "설명",
                "hashtags": ["태그1", "태그2", ...]
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse response
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
        except Exception as e:
            logger.error(f"Error generating SEO content: {e}")
        
        return self._get_mock_seo_content(analysis_results)
    
    def _get_mock_seo_content(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """Generate mock SEO content for testing"""
        
        products = analysis_results.get("products", [])
        product_name = products[0]["name"] if products else "신제품"
        
        return {
            "title": f"[리뷰] {product_name} 완벽 분석! 구매 전 필수 시청",
            "description": f"""
            {product_name}의 모든 것을 알려드립니다!
            
            ✅ 장단점 완벽 분석
            ✅ 실사용 후기
            ✅ 구매 가이드
            
            이 영상을 보시면 현명한 구매 결정을 하실 수 있습니다.
            
            #제품리뷰 #언박싱 #{product_name}
            """.strip(),
            "hashtags": [
                "#제품리뷰", "#언박싱", f"#{product_name}",
                "#신제품", "#테크", "#가젯",
                "#추천", "#리뷰", "#꿀템", "#쇼핑"
            ]
        }

# Global analyzer instance
_analyzer: Optional[GeminiVideoAnalyzer] = None

def get_video_analyzer() -> GeminiVideoAnalyzer:
    """Get or create global video analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = GeminiVideoAnalyzer()
    return _analyzer
