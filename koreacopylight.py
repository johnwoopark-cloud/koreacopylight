import os
import re
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

# 1. 검색 키워드 설정
KEYWORDS = ["저작권", "저작권 소송", "저작권 분쟁", "저작권 판결", "저작권 단속", "저작권 침해"]

# 2. 네이버 API 정보
CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

# 3. "저작권 고지 문구" 패턴 (기사 하단 상투 문구)
#    이 패턴이 제목/요약에 걸리면, 실제 저작권 '주제' 기사인지 본문을 검토함
NOTICE_PATTERNS = [
    r'저작권은\s*[^.\n]{1,40}?에\s*있(습니다|음)',   # "저작권은 ~에 있습니다"
    r'저작권자\s*[ⓒ©Ⓒ]?',                          # "저작권자 ⓒ ~"
    r'[ⓒ©Ⓒ]\s*\S+',                                # "ⓒ 연합뉴스" 등
    r'무단\s*(전재|복제|배포|사용)',                  # "무단 전재 및 재배포 금지"
    r'재배포\s*금지',
    r'AI\s*학습\s*(및\s*활용)?\s*금지',
]

# 4. 본문에서 실제 저작권 '주제'를 판단할 핵심 키워드
CONTENT_KEYWORDS = ['저작권', '저작물', '저작인접권', '저작인격권',
                    '지식재산', '지재권', '표절', '불법복제', '저작권료']

# 본문에서 핵심 키워드가 이 횟수 이상 나오면 "저작권 관련 기사"로 판정
MIN_MENTIONS = 4

REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}


def is_similar(str1, str2):
    """두 문장의 유사도를 0~1 사이로 반환"""
    return SequenceMatcher(None, str1, str2).ratio()


def has_notice_phrase(text):
    """저작권 고지(상투) 문구 포함 여부"""
    return any(re.search(p, text) for p in NOTICE_PATTERNS)


def strip_notice_phrases(text):
    """본문에서 고지 문구를 제거 (주제 판단 시 노이즈 방지)"""
    for p in NOTICE_PATTERNS:
        text = re.sub(p, ' ', text)
    return text


def fetch_article_body(url):
    """기사 링크에서 본문 텍스트 추출 (네이버 뉴스 + 일반 언론사 대응)"""
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # 자주 쓰이는 본문 selector 순서대로 시도
        selectors = [
            '#dic_area',                    # 네이버 뉴스 (신형)
            '#newsct_article',              # 네이버 뉴스
            '#articleBodyContents',         # 네이버 뉴스 (구형)
            '#article-view-content-div',    # 다수 지역/전문지
            'div.article_body', 'div.news_body', 'div.article-body',
            'article',
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                text = node.get_text(' ', strip=True)
                if len(text) > 100:
                    return text

        # 폴백: p 태그 전체 수집
        text = ' '.join(p.get_text(' ', strip=True) for p in soup.find_all('p'))
        return text if len(text) > 100 else None
    except Exception:
        return None


def verify_copyright_article(body):
    """본문에서 고지 문구를 제외하고 핵심 키워드 등장 횟수로 관련성 판단"""
    cleaned = strip_notice_phrases(body)
    mentions = sum(cleaned.count(kw) for kw in CONTENT_KEYWORDS)
    return mentions >= MIN_MENTIONS, mentions


def fetch_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": 30,
        "sort": "date"
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
                clean_title = item['title'].replace('<b>', '').replace('</b>', '') \
                    .replace('&quot;', '"').replace('&apos;', "'")
                clean_desc = item['description'].replace('<b>', '').replace('</b>', '') \
                    .replace('&quot;', '"').replace('&apos;', "'")

                raw_news.append({
                    "title": clean_title,
                    "description": clean_desc[:200],
                    "link": item['link'],
                    "pubDate": item['pubDate'],
                    "similar_count": 0
                })
                seen_links.add(item['link'])

    # 1. 날짜 순서대로 정렬 (가장 최신이 위로)
    raw_news.sort(key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S +0900'),
                  reverse=True)

    # 2. 유사 기사 그룹화
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

    # 3. 고지 문구가 걸린 기사만 본문 검토
    for item in final_news:
        combined = item['title'] + ' ' + item['description']

        if has_notice_phrase(combined):
            body = fetch_article_body(item['link'])
            if body is None:
                item['content_check'] = "본문수집실패"
                item['is_copyright_topic'] = None
                item['keyword_mentions'] = 0
            else:
                is_relevant, mentions = verify_copyright_article(body)
                item['content_check'] = "본문검토완료"
                item['is_copyright_topic'] = is_relevant
                item['keyword_mentions'] = mentions
        else:
            # 고지 문구 없이 검색에 걸린 기사는 검토 대상 아님
            item['content_check'] = "검토불필요"
            item['is_copyright_topic'] = True
            item['keyword_mentions'] = None

    # (선택) 본문 검토 결과 관련 없는 기사를 제외하려면 아래 주석 해제
    final_news = [n for n in final_news if n['is_copyright_topic'] is not False]

    with open('news_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, ensure_ascii=False, indent=4)

    reviewed = sum(1 for n in final_news if n['content_check'] == "본문검토완료")
    excluded = sum(1 for n in final_news if n['is_copyright_topic'] is False)
    print(f"총 {len(final_news)}건 정리 완료. (본문 검토 {reviewed}건, 저작권 무관 판정 {excluded}건)")


if __name__ == "__main__":
    main()
