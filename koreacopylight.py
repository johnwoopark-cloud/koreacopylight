import os
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher

# 1. 검색 키워드 설정
KEYWORDS = ["저작권", "저작권 소송", "저작권 분쟁", "저작권 판결", "저작권 단속", "저작권 침해"]

# 2. 네이버 API 정보
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

def is_similar(str1, str2):
    """두 문장의 유사도를 0~1 사이로 반환"""
    return SequenceMatcher(None, str1, str2).ratio()

def fetch_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": 30, # 정렬을 위해 더 넉넉히 가져옴
        "sort": "date" # API 호출 자체를 최신순으로 요청
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('items', [])
    return []

def main():
    raw_news = []
    seen_links = set()

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
                    "similar_count": 0
                })
                seen_links.add(item['link'])

    # 1. 날짜 순서대로 정렬 (가장 최신이 위로)
    # 네이버 날짜 형식: "Fri, 08 May 2026 14:00:00 +0900"
    raw_news.sort(key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S +0900'), reverse=True)

    # 2. 유사 기사 그룹화 (0.4로 낮춤)
    final_news = []
    for item in raw_news:
        is_grouped = False
        for existing in final_news:
            # 유사도 기준을 0.4로 하향 조정
            if is_similar(item['title'], existing['title']) > 0.4:
                existing['similar_count'] += 1
                is_grouped = True
                break
        
        if not is_grouped:
            final_news.append(item)

    # 결과 저장
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, ensure_ascii=False, indent=4)
    
    print(f"총 {len(final_news)}건의 뉴스를 최신순으로 정리 완료.")

if __name__ == "__main__":
    main()
