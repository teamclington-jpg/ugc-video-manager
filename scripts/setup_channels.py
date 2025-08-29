#!/usr/bin/env python3
"""
초기 채널 설정 스크립트
지정된 폴더 구조에 맞는 채널들을 데이터베이스에 추가합니다.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.database import get_db_manager

async def setup_initial_channels():
    """초기 채널 데이터 설정"""
    db = get_db_manager()
    
    # 테스트 연결
    connected = await db.test_connection()
    print(f"📊 Database connection: {'✅ Connected' if connected else '⚠️ Using in-memory mode'}")
    
    # 채널 데이터 정의
    channels = [
        {
            'channel_name': '반려동물 꿀템',
            'channel_url': 'https://youtube.com/@pet-honey-items',
            'channel_type': 'main',
            'category': 'pet',
            'description': '반려동물 관련 제품 리뷰 채널',
            'account_id': 'pet_channel@example.com',
            'account_password': 'temp_password_1',
            'max_daily_uploads': 3,
            'is_active': True,
            'infocrlink_url': None
        },
        {
            'channel_name': '자취생 꿀템',
            'channel_url': 'https://youtube.com/@student-honey-items',
            'channel_type': 'main',
            'category': 'lifestyle',
            'description': '자취생활 필수 아이템 리뷰 채널',
            'account_id': 'student_channel@example.com',
            'account_password': 'temp_password_2',
            'max_daily_uploads': 3,
            'is_active': True,
            'infocrlink_url': None
        },
        {
            'channel_name': '주부채널 (신규)',
            'channel_url': 'https://youtube.com/@housewife-channel',
            'channel_type': 'main',
            'category': 'home',
            'description': '주방용품 및 생활용품 리뷰 채널',
            'account_id': 'housewife_channel@example.com',
            'account_password': 'temp_password_3',
            'max_daily_uploads': 3,
            'is_active': True,
            'infocrlink_url': None
        }
    ]
    
    print("\n📝 Creating channels...")
    for channel_data in channels:
        try:
            # 이미 존재하는지 확인
            existing = await db.get_channel_by_name(channel_data['channel_name'])
            if existing:
                print(f"  ⚠️ Channel '{channel_data['channel_name']}' already exists - skipping")
                continue
            
            # 새 채널 생성
            result = await db.create_channel(channel_data)
            if result:
                print(f"  ✅ Created channel: {channel_data['channel_name']}")
            else:
                print(f"  ❌ Failed to create channel: {channel_data['channel_name']}")
        except Exception as e:
            print(f"  ❌ Error creating channel '{channel_data['channel_name']}': {e}")
    
    # 채널 목록 확인
    print("\n📋 Current channels:")
    all_channels = await db.list_channels_all()
    for ch in all_channels:
        print(f"  - {ch.get('channel_name')} ({ch.get('category')}) - {'Active' if ch.get('is_active') else 'Inactive'}")
    
    print(f"\n✅ Total channels: {len(all_channels)}")

if __name__ == "__main__":
    asyncio.run(setup_initial_channels())