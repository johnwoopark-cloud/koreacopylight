import os
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# 1. 설정
KEYWORDS = ["저작권", "저작권 소송", "저작권 분쟁", "저작권 판결", "저작권 단속", "저작권 침해"]
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
DATA_FILE = 'news_data.json'

def is_similar(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()

def fetch_naver_news():
    """네이버 API를 통해 뉴스 수집"""
    raw_news = []
    seen_links = set()
    
    for kw in KEYWORDS:
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
        params = {"query": kw, "display": 15, "sort": "date"}
        
        try:
            res = requests.get(url, headers=headers, params=params)
            items = res.json().get('items', [])
            for item in items:
                if item['link'] not in seen_links:
                    title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                    desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
                    raw_news.append({
                        "id": datetime.now().timestamp() + len(raw_news),
                        "title": title,
                        "description": desc[:180],
                        "link": item['link'],
                        "pubDate": item['pubDate'],
                        "similar_count": 0
                    })
                    seen_links.add(item['link'])
        except:
            continue
    
    # 정렬 및 유사도 필터링
    raw_news.sort(key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S +0900'), reverse=True)
    
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
    return final_news

@app.route('/')
def index():
    # 1. 페이지 접속 시 즉시 수집
    news_list = fetch_naver_news()
    
    # 2. 수집된 데이터를 파일로 저장 (삭제 기능을 위해 필요)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=4)
        
    return render_template('index.html', news_list=news_list)

@app.route('/delete/<float:news_id>', methods=['POST'])
def delete_news(news_id):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            news_list = json.load(f)
        
        # 삭제 버튼을 누른 항목만 제외
        filtered_list = [n for n in news_list if n.get('id') != news_id]
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered_list, f, ensure_ascii=False, indent=4)
            
    return jsonify({"status": "deleted"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
