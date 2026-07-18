#!/usr/bin/env python3
"""
사람인 오픈 API로 신입/인턴 인프라·클라우드 계열 공고를 수집해 jobs.json 생성.
- 저장 위치: 저장소 루트 jobs.json (앱이 자동으로 읽음)
- 필요: 환경변수 SARAMIN_API_KEY (https://oapi.saramin.co.kr 에서 무료 발급)
- 실행: GitHub Actions가 매일 KST 06:00에 자동 실행 (jobs-crawler.yml)
"""
import json, os, sys, urllib.request, urllib.parse

API_KEY = os.environ.get("SARAMIN_API_KEY", "")
if not API_KEY:
    print("SARAMIN_API_KEY 미설정 — jobs.json을 갱신하지 않고 종료")
    sys.exit(0)

KEYWORDS = ["클라우드 엔지니어", "인프라 엔지니어", "시스템 엔지니어",
            "네트워크 엔지니어", "DevOps", "SRE", "MSP"]
PRIORITY = ["CJ올리브네트웍스", "삼성SDS", "LG CNS", "현대오토에버", "포스코DX",
            "롯데이노베이트", "신세계아이앤씨", "한화시스템", "코오롱베니트",
            "메가존", "베스핀글로벌", "클루커스", "교보DTS", "농심NDS",
            "웅진", "GS네오텍", "메타넷"]

def search(keyword):
    params = urllib.parse.urlencode({
        "access-key": API_KEY,
        "keywords": keyword,
        "count": 50,
        "sort": "pd",          # 게시일 역순
        "sr": "directhire",
    })
    url = f"https://oapi.saramin.co.kr/job-search?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def is_entry_level(job):
    """신입/인턴만 통과 (경력직 제외)"""
    exp = (job.get("position", {}).get("experience-level", {}) or {})
    code = str(exp.get("code", ""))
    name = str(exp.get("name", ""))
    # code 1 = 신입, 3 = 신입/경력 / 이름에 신입·인턴 포함 여부도 확인
    return code in ("1", "3") or "신입" in name or "인턴" in name

def to_entry(job):
    pos = job.get("position", {})
    comp = (job.get("company", {}).get("detail", {}) or {}).get("name", "")
    due_ts = job.get("expiration-date", "")
    due = due_ts[:10] if due_ts else ""
    return {
        "c": comp,
        "r": pos.get("title", "")[:60],
        "due": due,
        "url": job.get("url", ""),
        "src": "사람인",
        "pri": any(p in comp for p in PRIORITY),
    }

seen, results = set(), []
for kw in KEYWORDS:
    try:
        data = search(kw)
    except Exception as e:
        print(f"[warn] '{kw}' 검색 실패: {e}")
        continue
    for job in (data.get("jobs", {}).get("job", []) or []):
        if not is_entry_level(job):
            continue
        e = to_entry(job)
        k = e["c"] + "|" + e["r"]
        if not e["c"] or k in seen:
            continue
        seen.add(k)
        results.append(e)

# 우선순위 기업 먼저, 이후 마감 임박 순
results.sort(key=lambda x: (not x["pri"], x["due"] or "9999-99-99"))
results = results[:80]  # 앱 표시 상한

with open("jobs.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
print(f"jobs.json 갱신 완료: {len(results)}건 (우선순위 {sum(1 for r in results if r['pri'])}건)")
