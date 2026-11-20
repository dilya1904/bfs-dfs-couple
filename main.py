import json
import os
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="Our Little World - Couple App API",
    version="3.0.0",
    description="Couple app backend powering AI Date Maker and Gemini itinerary curation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATE_SPOTS: Dict[str, List[Dict[str, object]]] = {
    "대전 둔산&갈마": [
        {"name": "갈마동 웜테이블", "category": "카페", "moods": ["아늑한 실내", "로맨틱", "맛집 탐방"], "budget": "3만원 이하", "indoor": True, "desc": "따스한 우드톤과 시그니처 디저트가 있는 갈마동 감성 카페"},
        {"name": "한밭수목원 열대식물원 & 단풍길 산책", "category": "산책", "moods": ["로맨틱", "활동적인", "아늑한 실내"], "budget": "무료/알뜰", "indoor": True, "desc": "계절의 꽃길과 유리온실 열대식물원이 어우러진 도심 산책"},
        {"name": "둔산 비스트로 낭만", "category": "맛집", "moods": ["로맨틱", "맛집 탐방"], "budget": "5~10만원", "indoor": True, "desc": "캔들라이트와 와인 페어링이 완벽한 기념일 다이닝"},
        {"name": "성심당 본점 & 으능정이 거리", "category": "맛집", "moods": ["맛집 탐방", "활동적인"], "budget": "3만원 이하", "indoor": False, "desc": "갓 구운 빵 향기와 활기찬 스카이로드 산책 코스"},
        {"name": "소제동 한옥 로스터리", "category": "카페", "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "오래된 관사촌을 개조한 조용한 한옥 감성 카페"},
        {"name": "엑스포 다리 야경 산책", "category": "야경", "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "갑천 위로 반짝이는 조명을 보며 하루를 마무리하는 야경 코스"},
    ],
    "서울 성수동": [
        {"name": "서울숲 거울연못 & 숲길", "category": "산책", "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "햇살이 스며드는 숲길과 커플 스냅 명소"},
        {"name": "서울숲 아틀리에길 로스터리", "category": "카페", "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "작은 소품샵과 향긋한 커피가 이어지는 감성 골목"},
        {"name": "성수 시그니처 향수 공방", "category": "체험", "moods": ["로맨틱", "아늑한 실내"], "budget": "5~10만원", "indoor": True, "desc": "서로에게 어울리는 단 하나의 향수를 조향하는 시간"},
        {"name": "연무장길 팝업 & 갤러리", "category": "전시", "moods": ["활동적인", "맛집 탐방"], "budget": "3만원 이하", "indoor": True, "desc": "트렌디한 전시와 감각적인 브랜드 팝업 투어"},
        {"name": "성수 루프탑 와인바", "category": "맛집", "moods": ["로맨틱", "맛집 탐방"], "budget": "특별한 날 플렉스", "indoor": True, "desc": "성수의 노을을 바라보며 즐기는 프라이빗 디너"},
    ],
    "부산 광안리": [
        {"name": "광안리 해변 산책로", "category": "산책", "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "파도 소리와 광안대교가 펼쳐지는 바다 데이트"},
        {"name": "광안 오션뷰 로스터리", "category": "카페", "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "통창 너머 윤슬을 바라보며 마시는 시그니처 라떼"},
        {"name": "밀락더마켓", "category": "맛집", "moods": ["맛집 탐방", "활동적인"], "budget": "3만원 이하", "indoor": True, "desc": "바다 전망 계단 좌석과 감각적인 먹거리 마켓"},
        {"name": "광안대교 파인다이닝", "category": "맛집", "moods": ["로맨틱", "맛집 탐방"], "budget": "특별한 날 플렉스", "indoor": True, "desc": "광안대교 야경을 감상하는 2인 전용 창가 테이블"},
        {"name": "민락수변공원 야경", "category": "야경", "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "시원한 바닷바람과 반짝이는 야경으로 하루 마무리"},
    ],
}


class DateMakerRequest(BaseModel):
    mood: str = Field(default="로맨틱")
    budget: str = Field(default="5~10만원")
    weather: str = Field(default="화창한 맑음")
    location: str = Field(default="대전 둔산&갈마")


def _enrich_with_gemini(req: DateMakerRequest, stops: List[Dict[str, object]]) -> Optional[Dict[str, str]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    stop_names = " -> ".join(str(s["name"]) for s in stops)
    prompt = (
        "당신은 감성적인 커플 데이트 플래너입니다. 아래 조건과 선택된 스팟을 바탕으로 "
        "한국어 JSON만 반환하세요(마크다운 코드블록 없이 순수 JSON).\n"
        f"- 지역: {req.location}\n- 분위기: {req.mood}\n- 예산: {req.budget}\n- 날씨: {req.weather}\n"
        f"- 데이트 코스: {stop_names}\n"
        '응답 형식: {"title": "감성적인 한 줄 코스 제목", "summary": "2문장 커플 추천 코멘트", "love_tip": "오늘 데이트를 더 특별하게 만드는 한 줄 팁"}'
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 280},
        }
    ).encode("utf-8")
    http_req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(http_req, timeout=6) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = (
                body.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            cleaned = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and parsed.get("title"):
                return {
                    "title": str(parsed.get("title")),
                    "summary": str(parsed.get("summary", "")),
                    "love_tip": str(parsed.get("love_tip", "")),
                }
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None
    return None


@app.get("/")
def root() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": "couple",
        "app": "Our Little World Couple App",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/health")
def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": "couple",
        "app": "Our Little World Couple App",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/date-maker")
def date_maker(req: DateMakerRequest) -> Dict[str, object]:
    t0 = time.perf_counter()
    region_key = req.location if req.location in DATE_SPOTS else "대전 둔산&갈마"
    spots = DATE_SPOTS[region_key]

    def score_spot(spot: Dict[str, object]) -> int:
        score = 0
        if req.mood in spot.get("moods", []):
            score += 4
        if req.budget == spot.get("budget"):
            score += 3
        if "비" in req.weather and spot.get("indoor"):
            score += 3
        if "맑음" in req.weather and not spot.get("indoor"):
            score += 2
        return score

    ranked = sorted(spots, key=score_spot, reverse=True)
    selected: List[Dict[str, object]] = []
    used_categories = set()
    for s in ranked:
        if s["category"] not in used_categories:
            selected.append(s)
            used_categories.add(s["category"])
        if len(selected) == 3:
            break
    for s in ranked:
        if len(selected) >= 3:
            break
        if s not in selected:
            selected.append(s)

    time_slots = ["13:00", "15:30", "18:30"]
    itinerary = [
        {
            "time": time_slots[i],
            "name": s["name"],
            "category": s["category"],
            "budget": s["budget"],
            "desc": s["desc"],
        }
        for i, s in enumerate(selected[:3])
    ]

    ai_copy = _enrich_with_gemini(req, itinerary)
    ai_powered = ai_copy is not None
    if not ai_copy:
        ai_copy = {
            "title": f"{req.weather} 날, {req.mood} 감성 가득한 {region_key} 데이트 코스",
            "summary": (
                f"{req.budget} 예산에 맞춰 {itinerary[0]['name']}에서 시작해 "
                f"{itinerary[-1]['name']}까지 이어지는 둘만의 맞춤 하루 코스입니다."
            ),
            "love_tip": "오늘의 가장 예쁜 순간을 사진으로 남겨 추억 앨범에 꼭 기록해 보세요 ♥",
        }

    return {
        "status": "ok",
        "region": region_key,
        "preferences": req.model_dump(),
        "ai_powered": ai_powered,
        "title": ai_copy["title"],
        "summary": ai_copy["summary"],
        "love_tip": ai_copy["love_tip"],
        "itinerary": itinerary,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
