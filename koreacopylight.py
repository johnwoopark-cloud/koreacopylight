import os
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# 1. 설정 및 API 정보
KEYWORDS = ["저작권", "저작권 소송", "저작권 분쟁", "저작권 판결", "저작권 단속", "저작권 침해"]
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
DATA_FILE = 'news_data.json'

def is_similar(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()

def fetch_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    params = {"query": keyword, "display": 30, "sort": "date"}
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('items', []) if response.status_code == 200 else []
    except:
        return []

@app.route('/')
def index():
    news_list = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            news_list = json.load(f)
    return render_template('index.html', news_list=news_list)

@app.route('/scrape')
def scrape():
    raw_news = []
    seen_links = set()

    # 기존 데이터 로드 (유지하면서 업데이트)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw_news = json.load(f)
            seen_links = {item['link'] for item in raw_news}

    for kw in KEYWORDS:
        items = fetch_naver_news(kw)
        for item in items:
            if item['link'] not in seen_links:
                clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&apos;', "'")
                clean_desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&apos;', "'")
                
                raw_news.append({
                    "id": datetime.now().timestamp() + len(raw_news), # 고유 ID 생성
                    "title": clean_title,
                    "description": clean_desc[:180],
                    "link": item['link'],
                    "pubDate": item['pubDate'],
                    "similar_count": 0
                })
                seen_links.add(item['link'])

    # 최신순 정렬
    raw_news.sort(key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S +0900'), reverse=True)

    # 중복/유사 기사 묶기
    final_news = []
    for item in raw_news:
        is_grouped = False
        for existing in final_news:
            if is_similar(item['title'], existing['title']) > 0.4:
                existing['similar_count'] += 1
                is_grouped = True
                break
        if not is_grouped:
            final_news.append(item)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_news, f, ensure_ascii=False, indent=4)
    
    return jsonify({"status": "success"})

@app.route('/delete/<float:news_id>', methods=['POST'])
def delete_news(news_id):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            news_list = json.load(f)
        
        # 해당 ID 기사 필터링
        filtered_list = [n for n in news_list if n.get('id') != news_id]
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered_list, f, ensure_ascii=False, indent=4)
            
    return jsonify({"status": "deleted"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
