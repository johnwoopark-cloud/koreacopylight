import os
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher # 유사도 분석을 위한 라이브러리

# 1. 검색 키워드 설정
KEYWORDS = ["저작권", "저작권 소송", "저작권 분쟁", "저작권 판결", "저작권 단속"]

# 2. 네이버 API 정보
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

def is_similar(str1, str2):
    """두 문장의 유사도를 0~1 사이로 반환 (0.6 이상이면 유사하다고 판단)"""
    return SequenceMatcher(None, str1, str2).ratio()

def fetch_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": 20, # 더 많은 후보를 가져와서 그룹화
        "sort": "sim"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('items', [])
    return []

def main():
    raw_news = []
    seen_links = set()

    # 데이터 수집
    for kw in KEYWORDS:
        items = fetch_naver_news(kw)
        for item in items:
            if item['link'] not in seen_links:
                clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&apos;', "'")
                clean_desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&apos;', "'")
                
                raw_news.append({
                    "title": clean_title,
                    "description": clean_desc[:200],
                    "link": item['link'],
                    "pubDate": item['pubDate'],
                    "similar_count": 0 # 유사 기사 개수 초기화
                })
                seen_links.add(item['link'])

    # 유사 기사 그룹화 로직
    final_news = []
    for item in raw_news:
        is_grouped = False
        for existing in final_news:
            # 제목 유사도가 0.6(60%) 이상이면 유사 기사로 판단
            if is_similar(item['title'], existing['title']) > 0.6:
                existing['similar_count'] += 1
                is_grouped = True
                break
        
        if not is_grouped:
            final_news.append(item)

    # 결과 저장
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, ensure_ascii=False, indent=4)
    
    print(f"총 {len(final_news)}건의 대표 뉴스 정리 완료.")

if __name__ == "__main__":
    main()
