import os
import requests
import json
from datetime import datetime

# 1. 검색 키워드 설정 (나중에 여기서 자유롭게 추가/삭제)
KEYWORDS = ["드라마 소송", "드라마 판결", "드라마 표절", "드라마 저작권", "저작권", "저작권 소송","저작권 분쟁", "저작권 판결", "저작권 단속"]

# 2. 네이버 API 정보 (GitHub Secrets)
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

def fetch_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": 10, # 키워드당 10개씩 가져옴
        "sort": "sim"  # 유사도순 (최신순은 'date')
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        print(f"Error: {response.status_code}")
        return []

def main():
    all_news = []
    seen_links = set() # 중복 기사 제거용

    for kw in KEYWORDS:
        news_items = fetch_naver_news(kw)
        for item in news_items:
            # 중복 체크 (링크 기준)
            if item['link'] not in seen_links:
                # HTML 태그 제거 및 데이터 정리
                clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                clean_desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                
                all_news.append({
                    "title": clean_title,
                    "description": clean_desc[:200], # 200자 내외 제한
                    "link": item['link'],
                    "pubDate": item['pubDate'],
                    "originallink": item['originallink'] # 매체사 확인용
                })
                seen_links.add(item['link'])

    # 결과를 JSON 파일로 저장
    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
    
    print(f"총 {len(all_news)}건의 뉴스 수집 완료.")

if __name__ == "__main__":
    main()
