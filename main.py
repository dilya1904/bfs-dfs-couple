import json
import os
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="Our Little World - Couple Date & BFS/DFS Route API",
    version="2.0.0",
    description="Couple app backend powering BFS/DFS date-route comparison, couple place graphs, and AI Date Maker.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Curated Couple Places Graph Data (Aligned with Stitch Project 2412381284142136498)
# ---------------------------------------------------------------------------
REGIONS_DATA: Dict[str, Dict[str, object]] = {
    "대전 둔산&갈마": {
        "center_label": "대전 둔산 · 갈마 · 은행동",
        "places": [
            {"id": "sungsimdang", "name": "성심당 본점", "category": "맛집", "status": "visited", "x": 14, "y": 54, "moods": ["맛집 탐방", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "대전 데이트의 시작, 갓 구운 튀김소보로와 달콤한 빵 향기"},
            {"id": "euneungjeongi", "name": "으능정이 문화의거리", "category": "산책", "status": "visited", "x": 28, "y": 36, "moods": ["활동적인", "로맨틱"], "budget": "무료/알뜰", "indoor": False, "desc": "스카이로드 불빛 아래 손잡고 걷는 감성 거리"},
            {"id": "sojedong", "name": "소제동 카페거리", "category": "카페", "status": "visited", "x": 30, "y": 72, "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "오래된 관사촌을 개조한 감성 한옥 카페 골목"},
            {"id": "warmtable", "name": "갈마동 웜테이블", "category": "카페", "status": "wishlist", "x": 49, "y": 24, "moods": ["아늑한 실내", "로맨틱", "맛집 탐방"], "budget": "3만원 이하", "indoor": True, "desc": "따스한 우드톤과 시그니처 디저트가 있는 갈마동 아지트"},
            {"id": "galma_bistro", "name": "갈마동 작은 공방", "category": "공방", "status": "wishlist", "x": 54, "y": 58, "moods": ["로맨틱", "아늑한 실내"], "budget": "5~10만원", "indoor": True, "desc": "서로의 향기와 반지를 직접 만드는 프라이빗 원데이 클래스"},
            {"id": "daedong_sky", "name": "대동 하늘공원", "category": "야경", "status": "visited", "x": 46, "y": 84, "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "노을빛과 대전 시내 야경이 한눈에 펼쳐지는 풍차 언덕"},
            {"id": "hanbat", "name": "한밭수목원 열대식물원", "category": "산책", "status": "wishlist", "x": 72, "y": 28, "moods": ["로맨틱", "활동적인", "아늑한 실내"], "budget": "무료/알뜰", "indoor": True, "desc": "계절의 꽃길과 유리온실 열대식물원이 어우러진 도심 산책로"},
            {"id": "dunsan_nangman", "name": "둔산 비스트로 낭만", "category": "맛집", "status": "wishlist", "x": 74, "y": 64, "moods": ["로맨틱", "맛집 탐방"], "budget": "5~10만원", "indoor": True, "desc": "캔들라이트와 와인 페어링이 완벽한 기념일 다이닝"},
            {"id": "expo_bridge", "name": "엑스포 다리 야경", "category": "야경", "status": "visited", "x": 88, "y": 44, "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "갑천 위로 반짝이는 조명을 보며 하루를 마무리하는 산책 코스"},
        ],
        "edges": [
            ["sungsimdang", "euneungjeongi", 6],
            ["sungsimdang", "sojedong", 9],
            ["euneungjeongi", "warmtable", 14],
            ["euneungjeongi", "galma_bistro", 12],
            ["sojedong", "galma_bistro", 11],
            ["sojedong", "daedong_sky", 10],
            ["warmtable", "hanbat", 10],
            ["warmtable", "galma_bistro", 7],
            ["galma_bistro", "dunsan_nangman", 9],
            ["daedong_sky", "dunsan_nangman", 15],
            ["hanbat", "expo_bridge", 8],
            ["hanbat", "dunsan_nangman", 11],
            ["dunsan_nangman", "expo_bridge", 10],
        ],
    },
    "서울 성수동": {
        "center_label": "서울 성수동 · 서울숲",
        "places": [
            {"id": "seoul_forest", "name": "서울숲 거울연못", "category": "산책", "status": "visited", "x": 16, "y": 46, "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "햇살이 스며드는 숲길과 커플 스냅 명소"},
            {"id": "atelier_street", "name": "서울숲 아틀리에길", "category": "카페", "status": "visited", "x": 34, "y": 26, "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "작은 소품샵과 로스터리 카페가 이어진 감성 골목"},
            {"id": "perfume_lab", "name": "성수 시그니처 향수 공방", "category": "공방", "status": "wishlist", "x": 36, "y": 70, "moods": ["로맨틱", "아늑한 실내"], "budget": "5~10만원", "indoor": True, "desc": "서로에게 어울리는 단 하나의 향수를 조향하는 공간"},
            {"id": "yeonmujang", "name": "연무장길 팝업 스팟", "category": "산책", "status": "visited", "x": 56, "y": 48, "moods": ["활동적인", "맛집 탐방"], "budget": "3만원 이하", "indoor": True, "desc": "트렌디한 전시와 감각적인 브랜드 팝업이 가득한 거리"},
            {"id": "seongsu_cafe", "name": "대림창고 갤러리 카페", "category": "카페", "status": "wishlist", "x": 74, "y": 26, "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "붉은 벽돌과 예술 작품이 어우러진 성수 대표 공간"},
            {"id": "seongsu_wine", "name": "성수 루프탑 와인바", "category": "맛집", "status": "wishlist", "x": 84, "y": 64, "moods": ["로맨틱", "맛집 탐방"], "budget": "특별한 날 플렉스", "indoor": True, "desc": "성수의 노을을 바라보며 즐기는 프라이빗 디너"},
        ],
        "edges": [
            ["seoul_forest", "atelier_street", 7],
            ["seoul_forest", "perfume_lab", 9],
            ["atelier_street", "yeonmujang", 8],
            ["perfume_lab", "yeonmujang", 7],
            ["atelier_street", "seongsu_cafe", 11],
            ["yeonmujang", "seongsu_cafe", 6],
            ["yeonmujang", "seongsu_wine", 9],
            ["perfume_lab", "seongsu_wine", 13],
            ["seongsu_cafe", "seongsu_wine", 8],
        ],
    },
    "부산 광안리": {
        "center_label": "부산 광안리 · 민락동",
        "places": [
            {"id": "gwangan_beach", "name": "광안리 해변 산책로", "category": "산책", "status": "visited", "x": 16, "y": 54, "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "파도 소리와 광안대교가 펼쳐지는 바다 데이트"},
            {"id": "ocean_cafe", "name": "광안 오션뷰 로스터리", "category": "카페", "status": "wishlist", "x": 36, "y": 28, "moods": ["아늑한 실내", "로맨틱"], "budget": "3만원 이하", "indoor": True, "desc": "통창 너머 윤슬을 바라보며 마시는 라떼"},
            {"id": "millak_market", "name": "밀락더마켓", "category": "맛집", "status": "visited", "x": 42, "y": 74, "moods": ["맛집 탐방", "활동적인"], "budget": "3만원 이하", "indoor": True, "desc": "바다 전망 계단 좌석과 감각적인 먹거리 마켓"},
            {"id": "namcheon_bakery", "name": "남천동 빵천동 골목", "category": "맛집", "status": "wishlist", "x": 62, "y": 46, "moods": ["맛집 탐방", "아늑한 실내"], "budget": "3만원 이하", "indoor": True, "desc": "달콤한 디저트와 감성 서점이 숨어 있는 골목"},
            {"id": "marine_dinner", "name": "광안대교 파인다이닝", "category": "맛집", "status": "wishlist", "x": 84, "y": 32, "moods": ["로맨틱", "맛집 탐방"], "budget": "특별한 날 플렉스", "indoor": True, "desc": "드론쇼와 야경을 감상하는 2인 전용 창가 테이블"},
            {"id": "minrak_park", "name": "민락수변공원 야경", "category": "야경", "status": "visited", "x": 82, "y": 72, "moods": ["로맨틱", "활동적인"], "budget": "무료/알뜰", "indoor": False, "desc": "시원한 바닷바람과 반짝이는 광안대교 야경 스팟"},
        ],
        "edges": [
            ["gwangan_beach", "ocean_cafe", 6],
            ["gwangan_beach", "millak_market", 8],
            ["ocean_cafe", "namcheon_bakery", 10],
            ["millak_market", "namcheon_bakery", 9],
            ["ocean_cafe", "marine_dinner", 12],
            ["namcheon_bakery", "marine_dinner", 8],
            ["namcheon_bakery", "minrak_park", 10],
            ["millak_market", "minrak_park", 7],
            ["marine_dinner", "minrak_park", 6],
        ],
    },
}


class RouteCompareRequest(BaseModel):
    region: str = Field(default="대전 둔산&갈마")
    start_id: str = Field(default="sungsimdang")
    goal_id: str = Field(default="expo_bridge")


class DateMakerRequest(BaseModel):
    mood: str = Field(default="로맨틱")
    budget: str = Field(default="5~10만원")
    weather: str = Field(default="화창한 맑음")
    location: str = Field(default="대전 둔산&갈마")
    algo_mode: Literal["bfs", "dfs", "both"] = "both"


def _get_region_graph(region_name: str) -> Tuple[str, Dict[str, Dict[str, object]], Dict[str, List[Tuple[str, int]]]]:
    key = region_name if region_name in REGIONS_DATA else "대전 둔산&갈마"
    raw = REGIONS_DATA[key]
    places_map: Dict[str, Dict[str, object]] = {p["id"]: p for p in raw["places"]}
    adj: Dict[str, List[Tuple[str, int]]] = {pid: [] for pid in places_map}
    for u, v, w in raw["edges"]:
        if u in adj and v in adj:
            adj[u].append((v, int(w)))
            adj[v].append((u, int(w)))
    return key, places_map, adj


def _edge_minutes(adj: Dict[str, List[Tuple[str, int]]], u: str, v: str) -> int:
    for nb, mins in adj.get(u, []):
        if nb == v:
            return mins
    return 10


def _path_total_minutes(adj: Dict[str, List[Tuple[str, int]]], path: List[str]) -> int:
    if len(path) < 2:
        return 0
    return sum(_edge_minutes(adj, path[i], path[i + 1]) for i in range(len(path) - 1))


def run_bfs_places(
    places_map: Dict[str, Dict[str, object]],
    adj: Dict[str, List[Tuple[str, int]]],
    start_id: str,
    goal_id: str,
) -> Dict[str, object]:
    t0 = time.perf_counter()
    visited = {start_id}
    parent: Dict[str, Optional[str]] = {start_id: None}
    distance: Dict[str, int] = {start_id: 0}
    q: deque[str] = deque([start_id])

    enqueue_ops = 1
    dequeue_ops = 0
    max_queue = 1
    reached = False
    depth_counts: Dict[int, int] = {}
    steps: List[Dict[str, object]] = []

    while q:
        curr = q.popleft()
        dequeue_ops += 1
        d = distance[curr]
        depth_counts[d] = depth_counts.get(d, 0) + 1

        if curr == goal_id:
            reached = True
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node_id": curr,
                    "node_name": places_map[curr]["name"],
                    "dist": d,
                    "parent_id": parent[curr],
                    "queue_snapshot": [
                        {"id": qid, "name": places_map[qid]["name"], "dist": distance[qid]}
                        for qid in list(q)[:6]
                    ],
                    "queue_size": len(q),
                    "enqueue_ops": enqueue_ops,
                    "dequeue_ops": dequeue_ops,
                    "status": "최단 데이트 코스 도착 ❤️",
                }
            )
            break

        for nb, _ in adj.get(curr, []):
            if nb not in visited:
                visited.add(nb)
                parent[nb] = curr
                distance[nb] = d + 1
                q.append(nb)
                enqueue_ops += 1

        if len(q) > max_queue:
            max_queue = len(q)

        steps.append(
            {
                "step": len(steps),
                "type": "explore",
                "node_id": curr,
                "node_name": places_map[curr]["name"],
                "dist": d,
                "parent_id": parent[curr],
                "queue_snapshot": [
                    {"id": qid, "name": places_map[qid]["name"], "dist": distance[qid]}
                    for qid in list(q)[:6]
                ],
                "queue_size": len(q),
                "enqueue_ops": enqueue_ops,
                "dequeue_ops": dequeue_ops,
                "status": f"인접 스팟 확장 중 (Wave #{dequeue_ops})",
            }
        )

    path: List[str] = []
    if reached:
        cur: Optional[str] = goal_id
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    total_minutes = _path_total_minutes(adj, path)
    depth_histogram = [
        {"label": f"Hop {d}", "depth": d, "count": cnt}
        for d, cnt in sorted(depth_counts.items())
    ]

    return {
        "steps": steps,
        "path": path,
        "path_names": [places_map[pid]["name"] for pid in path],
        "distances": distance,
        "depth_histogram": depth_histogram,
        "metadata": {
            "reached_goal": reached,
            "visited_count": dequeue_ops,
            "total_places": len(places_map),
            "path_stops": len(path),
            "path_hops": max(0, len(path) - 1),
            "total_minutes": total_minutes,
            "max_memory": max_queue,
            "enqueue_ops": enqueue_ops,
            "dequeue_ops": dequeue_ops,
            "operation_count": enqueue_ops + dequeue_ops,
            "elapsed_ms": elapsed_ms,
        },
    }


def run_dfs_places(
    places_map: Dict[str, Dict[str, object]],
    adj: Dict[str, List[Tuple[str, int]]],
    start_id: str,
    goal_id: str,
    optimal_hops: int,
) -> Dict[str, object]:
    t0 = time.perf_counter()
    visited = {start_id}
    parent: Dict[str, Optional[str]] = {start_id: None}
    stack: List[str] = [start_id]

    push_ops = 1
    pop_ops = 0
    max_stack = 1
    backtrack_count = 0
    depth_hist_counts: Dict[int, int] = {}
    reached = False
    steps: List[Dict[str, object]] = []

    while stack:
        curr = stack[-1]
        cur_depth = len(stack)

        if curr == goal_id:
            reached = True
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node_id": curr,
                    "node_name": places_map[curr]["name"],
                    "depth": cur_depth,
                    "parent_id": parent[curr],
                    "stack_snapshot": [
                        {"id": sid, "name": places_map[sid]["name"], "depth": idx + 1}
                        for idx, sid in reversed(list(enumerate(stack))[-6:])
                    ],
                    "stack_size": cur_depth,
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": False,
                    "backtrack_count": backtrack_count,
                    "status": "감성 탐험 코스 도착 ✨",
                }
            )
            break

        candidates = [nb for nb, _ in reversed(adj.get(curr, [])) if nb not in visited]
        if len(candidates) > 1 and goal_id in candidates:
            candidates = [nb for nb in candidates if nb != goal_id] + [goal_id]

        if candidates:
            nxt = candidates[0]
            visited.add(nxt)
            parent[nxt] = curr
            stack.append(nxt)
            push_ops += 1
            if len(stack) > max_stack:
                max_stack = len(stack)
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node_id": curr,
                    "node_name": places_map[curr]["name"],
                    "depth": cur_depth,
                    "parent_id": parent[curr],
                    "stack_snapshot": [
                        {"id": sid, "name": places_map[sid]["name"], "depth": idx + 1}
                        for idx, sid in reversed(list(enumerate(stack))[-6:])
                    ],
                    "stack_size": len(stack),
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": False,
                    "backtrack_count": backtrack_count,
                    "status": f"'{places_map[nxt]['name']}' 방향으로 깊이 탐색",
                }
            )
        else:
            popped = stack.pop()
            pop_ops += 1
            backtrack_count += 1
            depth_hist_counts[cur_depth] = depth_hist_counts.get(cur_depth, 0) + 1
            steps.append(
                {
                    "step": len(steps),
                    "type": "backtrack",
                    "node_id": popped,
                    "node_name": places_map[popped]["name"],
                    "depth": len(stack),
                    "parent_id": parent[popped],
                    "stack_snapshot": [
                        {"id": sid, "name": places_map[sid]["name"], "depth": idx + 1}
                        for idx, sid in reversed(list(enumerate(stack))[-6:])
                    ],
                    "stack_size": len(stack),
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": True,
                    "backtrack_count": backtrack_count,
                    "status": "막다른 골목 · 이전 스팟으로 되돌아감",
                }
            )

    path = list(stack) if reached else []
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    total_minutes = _path_total_minutes(adj, path)
    hops = max(0, len(path) - 1)
    overhead_pct = (
        round(((hops - optimal_hops) / optimal_hops) * 100, 1)
        if optimal_hops > 0 and hops >= optimal_hops
        else 0.0
    )

    max_d = max(depth_hist_counts.keys()) if depth_hist_counts else max(4, max_stack)
    backtrack_histogram = [
        {"label": f"Depth {d}", "depth": d, "count": depth_hist_counts.get(d, 0)}
        for d in range(1, max_d + 1)
    ]

    return {
        "steps": steps,
        "path": path,
        "path_names": [places_map[pid]["name"] for pid in path],
        "backtrack_histogram": backtrack_histogram,
        "metadata": {
            "reached_goal": reached,
            "visited_count": push_ops,
            "total_places": len(places_map),
            "path_stops": len(path),
            "path_hops": hops,
            "path_overhead_pct": overhead_pct,
            "total_minutes": total_minutes,
            "max_memory": max_stack,
            "push_ops": push_ops,
            "pop_ops": pop_ops,
            "backtrack_count": backtrack_count,
            "operation_count": push_ops + pop_ops,
            "elapsed_ms": elapsed_ms,
        },
    }


def _enrich_with_gemini(
    req: DateMakerRequest,
    stops: List[Dict[str, object]],
    algo_summary: str,
) -> Optional[Dict[str, str]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    stop_names = " -> ".join(str(s["name"]) for s in stops)
    prompt = (
        "당신은 감성적인 커플 데이트 플래너입니다. 아래 조건과 선택된 스팟을 바탕으로 "
        "한국어 JSON만 반환하세요(마크다운 코드블록 없이 순수 JSON).\n"
        f"- 지역: {req.location}\n- 분위기: {req.mood}\n- 예산: {req.budget}\n- 날씨: {req.weather}\n"
        f"- 선택된 코스: {stop_names}\n- 탐색 요약: {algo_summary}\n"
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
        "service": "bfs-dfs-couple",
        "app": "Our Little World Couple App",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/health")
def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": "bfs-dfs-couple",
        "app": "Our Little World Couple App",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/api/places")
def get_places(region: Optional[str] = Query(default=None)) -> Dict[str, object]:
    if region and region in REGIONS_DATA:
        return {"status": "ok", "region": region, "data": REGIONS_DATA[region]}
    return {"status": "ok", "regions": REGIONS_DATA}


@app.post("/api/route/compare")
def compare_route(req: RouteCompareRequest) -> Dict[str, object]:
    t_total = time.perf_counter()
    region_key, places_map, adj = _get_region_graph(req.region)
    place_ids = list(places_map.keys())
    start_id = req.start_id if req.start_id in places_map else place_ids[0]
    goal_id = req.goal_id if req.goal_id in places_map else place_ids[-1]
    if start_id == goal_id and len(place_ids) > 1:
        goal_id = place_ids[-1] if start_id != place_ids[-1] else place_ids[0]

    bfs_res = run_bfs_places(places_map, adj, start_id, goal_id)
    dfs_res = run_dfs_places(
        places_map, adj, start_id, goal_id, int(bfs_res["metadata"]["path_hops"])
    )
    max_steps = max(len(bfs_res["steps"]), len(dfs_res["steps"]), 1) - 1

    return {
        "status": "ok",
        "region": region_key,
        "start_id": start_id,
        "goal_id": goal_id,
        "places": list(places_map.values()),
        "edges": REGIONS_DATA[region_key]["edges"],
        "max_steps": max_steps,
        "total_elapsed_ms": round((time.perf_counter() - t_total) * 1000, 3),
        "bfs": bfs_res,
        "dfs": dfs_res,
    }


@app.post("/api/date-maker")
def date_maker(req: DateMakerRequest) -> Dict[str, object]:
    t0 = time.perf_counter()
    region_key, places_map, adj = _get_region_graph(req.location)
    places = list(places_map.values())

    def score_place(p: Dict[str, object]) -> int:
        score = 0
        if req.mood in p.get("moods", []):
            score += 4
        if req.budget == p.get("budget"):
            score += 3
        if "비" in req.weather and p.get("indoor"):
            score += 3
        if "맑음" in req.weather and not p.get("indoor"):
            score += 2
        if p.get("status") == "wishlist":
            score += 1
        return score

    ranked = sorted(places, key=score_place, reverse=True)
    start_place = ranked[0]
    goal_place = ranked[-1] if len(ranked) > 1 else ranked[0]
    for candidate in ranked[1:]:
        if candidate["category"] != start_place["category"]:
            goal_place = candidate
            break

    bfs_res = run_bfs_places(places_map, adj, str(start_place["id"]), str(goal_place["id"]))
    dfs_res = run_dfs_places(
        places_map,
        adj,
        str(start_place["id"]),
        str(goal_place["id"]),
        int(bfs_res["metadata"]["path_hops"]),
    )

    chosen_ids = list(dfs_res["path"] if req.algo_mode == "dfs" else bfs_res["path"])
    if len(chosen_ids) < 3:
        for extra in ranked:
            if extra["id"] not in chosen_ids:
                chosen_ids.append(str(extra["id"]))
            if len(chosen_ids) >= 3:
                break
    chosen_ids = chosen_ids[:4]

    time_slots = ["13:00", "15:30", "18:30", "20:30"]
    itinerary = []
    for idx, pid in enumerate(chosen_ids):
        p = places_map[pid]
        travel_min = _edge_minutes(adj, chosen_ids[idx - 1], pid) if idx > 0 else 0
        itinerary.append(
            {
                "time": time_slots[idx],
                "id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "budget": p["budget"],
                "desc": p["desc"],
                "travel_from_prev_min": travel_min,
            }
        )

    algo_summary = (
        f"BFS 최단 동선 {bfs_res['metadata']['path_stops']}곳({bfs_res['metadata']['total_minutes']}분) vs "
        f"DFS 깊이 탐험 {dfs_res['metadata']['path_stops']}곳({dfs_res['metadata']['total_minutes']}분)"
    )
    ai_copy = _enrich_with_gemini(req, itinerary, algo_summary)
    ai_powered = ai_copy is not None
    if not ai_copy:
        ai_copy = {
            "title": f"{req.weather} 날, {req.mood} 감성 가득한 {region_key} 데이트 코스",
            "summary": (
                f"{req.budget} 예산에 맞춰 {itinerary[0]['name']}에서 시작해 "
                f"{itinerary[-1]['name']}까지 이어지는 둘만의 맞춤 동선입니다."
            ),
            "love_tip": "이동 사이사이 폴라로이드나 스마트폰으로 오늘의 한 컷을 꼭 남겨보세요 ♥",
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
        "bfs": bfs_res,
        "dfs": dfs_res,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
    }


@app.post("/api/simulate")
def simulate_compat(req: Optional[RouteCompareRequest] = None) -> Dict[str, object]:
    return compare_route(req or RouteCompareRequest())


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
