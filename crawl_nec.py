"""
선관위 서면/인터넷 질의회답 크롤러
실행: python3 crawl_nec.py
결과: nec_qa.json 생성
"""
import requests, json, time, re
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://www.nec.go.kr',
}

BASE_URL = "https://www.nec.go.kr"

# 공직선거법 질의회답: menuNo=200185
# 정치자금법 질의회답: menuNo=200186 (확인 필요)
TARGETS = [
    {"name": "공직선거법_질의회답", "url": f"{BASE_URL}/portal/bbs/list/B0000342.do?menuNo=200185"},
    {"name": "정치자금법_질의회답", "url": f"{BASE_URL}/portal/bbs/list/B0000343.do?menuNo=200186"},
]

def get_list_page(url, page=1):
    """목록 페이지 가져오기"""
    params = {"pageIndex": page}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'lxml')

def get_detail(href):
    """상세 페이지 가져오기"""
    url = BASE_URL + href if href.startswith('/') else href
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')

    # 제목
    title = ""
    for sel in ['h3.tit', '.view-title', '.board-view h3', 'h2']:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # 본문
    content = ""
    for sel in ['.view-content', '.board-content', '.bbs-view', 'article', '.cont']:
        el = soup.select_one(sel)
        if el:
            content = el.get_text(separator='\n', strip=True)
            break

    return {"title": title, "content": content, "url": url}

def crawl_target(target, max_pages=50):
    """단일 카테고리 크롤링"""
    results = []
    print(f"\n[{target['name']}] 크롤링 시작")

    for page in range(1, max_pages + 1):
        print(f"  페이지 {page}...", end=' ')
        try:
            soup = get_list_page(target['url'], page)

            # 목록 행 찾기
            rows = soup.select('table tbody tr')
            if not rows:
                rows = soup.select('.board-list li')

            if not rows:
                print("목록 없음 — 종료")
                break

            page_items = []
            for row in rows:
                link = row.select_one('a')
                if not link:
                    continue
                href = link.get('href', '')
                if not href:
                    continue

                # 제목 키워드 필터 (공직선거법/정치자금법 관련만)
                title_text = link.get_text(strip=True)

                time.sleep(0.5)  # 서버 부하 방지
                try:
                    detail = get_detail(href)
                    detail['category'] = target['name']
                    detail['list_title'] = title_text
                    page_items.append(detail)
                except Exception as e:
                    print(f"(상세 오류: {e})", end=' ')

            results.extend(page_items)
            print(f"{len(page_items)}건 수집")

            # 다음 페이지 없으면 종료
            next_btn = soup.select_one('a.next, .paging .next, [aria-label="다음"]')
            if not next_btn:
                print(f"  마지막 페이지")
                break

        except Exception as e:
            print(f"오류: {e}")
            break

    print(f"  [{target['name']}] 총 {len(results)}건 수집 완료")
    return results

def main():
    all_data = []

    for target in TARGETS:
        data = crawl_target(target, max_pages=100)
        all_data.extend(data)

    # 청크 변환 (RAG용)
    chunks = []
    for item in all_data:
        text = f"[질의제목] {item.get('title','')}\n[질의내용]\n{item.get('content','')}"
        # 1500자 단위 청크
        for i in range(0, len(text), 1500):
            chunk = text[i:i+1500].strip()
            if len(chunk) > 50:
                chunks.append({
                    "source": item.get('category', '선관위질의'),
                    "text": chunk,
                    "url": item.get('url', ''),
                    "title": item.get('title', ''),
                })

    # 저장
    with open('nec_qa_raw.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    with open('nec_qa_chunks.json', 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료!")
    print(f"   원본: nec_qa_raw.json ({len(all_data)}건)")
    print(f"   청크: nec_qa_chunks.json ({len(chunks)}개)")

if __name__ == '__main__':
    main()
