import os
import random
import time
from collections import deque
from typing import Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="BFS vs DFS Maze Visualizer API",
    version="1.0.0",
    description="Dual BFS/DFS maze generation and step-by-step telemetry engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unified 4-way exploration order matching Stitch architecture spec: [N, E, S, W]
DIRECTIONS: List[Tuple[int, int, str]] = [
    (-1, 0, "North"),
    (0, 1, "East"),
    (1, 0, "South"),
    (0, -1, "West"),
]
DIRECTION_LABELS: List[str] = ["N", "E", "S", "W"]


class SimulateRequest(BaseModel):
    grid_size: int = Field(default=21, ge=7, le=41)
    maze_type: Literal["backtracker", "prims", "sparse"] = "backtracker"
    seed: int = Field(default=4092, ge=0, le=999999)
    custom_maze: Optional[List[List[int]]] = None


def _normalize_odd_size(size: int) -> int:
    return size if size % 2 == 1 else max(7, size - 1)


def _generate_backtracker_maze(size: int, rng: random.Random) -> List[List[int]]:
    grid = [[1 for _ in range(size)] for _ in range(size)]
    grid[0][0] = 0
    stack: List[Tuple[int, int]] = [(0, 0)]

    while stack:
        r, c = stack[-1]
        neighbors: List[Tuple[int, int, int, int]] = []
        for dr, dc, _ in DIRECTIONS:
            nr, nc = r + dr * 2, c + dc * 2
            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 1:
                neighbors.append((nr, nc, r + dr, c + dc))
        if neighbors:
            nr, nc, wr, wc = rng.choice(neighbors)
            grid[wr][wc] = 0
            grid[nr][nc] = 0
            stack.append((nr, nc))
        else:
            stack.pop()

    grid[0][0] = 0
    grid[size - 1][size - 1] = 0
    return grid


def _generate_prims_maze(size: int, rng: random.Random) -> List[List[int]]:
    grid = [[1 for _ in range(size)] for _ in range(size)]
    grid[0][0] = 0
    frontiers: List[Tuple[int, int, int, int]] = []

    def add_frontiers(r: int, c: int) -> None:
        for dr, dc, _ in DIRECTIONS:
            nr, nc = r + dr * 2, c + dc * 2
            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 1:
                frontiers.append((nr, nc, r + dr, c + dc))

    add_frontiers(0, 0)
    while frontiers:
        idx = rng.randrange(len(frontiers))
        nr, nc, wr, wc = frontiers.pop(idx)
        if grid[nr][nc] == 1:
            grid[wr][wc] = 0
            grid[nr][nc] = 0
            add_frontiers(nr, nc)

    grid[0][0] = 0
    grid[size - 1][size - 1] = 0
    return grid


def _is_solvable(grid: List[List[int]]) -> bool:
    size = len(grid)
    if grid[0][0] != 0 or grid[size - 1][size - 1] != 0:
        return False
    visited = [[False] * size for _ in range(size)]
    q: deque[Tuple[int, int]] = deque([(0, 0)])
    visited[0][0] = True
    while q:
        r, c = q.popleft()
        if r == size - 1 and c == size - 1:
            return True
        for dr, dc, _ in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 0 and not visited[nr][nc]:
                visited[nr][nc] = True
                q.append((nr, nc))
    return False


def _generate_sparse_maze(size: int, rng: random.Random) -> List[List[int]]:
    for _ in range(20):
        grid = [[1 if rng.random() < 0.28 else 0 for _ in range(size)] for _ in range(size)]
        grid[0][0] = 0
        grid[size - 1][size - 1] = 0
        if _is_solvable(grid):
            return grid
    return _generate_backtracker_maze(size, rng)


def generate_maze(size: int, maze_type: str, seed: int) -> List[List[int]]:
    rng = random.Random(seed)
    if maze_type == "prims":
        return _generate_prims_maze(size, rng)
    if maze_type == "sparse":
        return _generate_sparse_maze(size, rng)
    return _generate_backtracker_maze(size, rng)


def _build_bfs_histogram(depth_counts: Dict[int, int], bins: int = 10) -> Tuple[List[Dict[str, object]], int]:
    if not depth_counts:
        return [], 0
    max_depth = max(depth_counts.keys())
    peak_depth = max(depth_counts.items(), key=lambda item: item[1])[0]
    bucket_size = max(1, (max_depth + bins) // bins)

    histogram: List[Dict[str, object]] = []
    for i in range(bins):
        start_d = i * bucket_size
        end_d = start_d + bucket_size - 1
        count = sum(cnt for d, cnt in depth_counts.items() if start_d <= d <= end_d)
        label = f"d={start_d}" if start_d == end_d else f"d={start_d}-{end_d}"
        histogram.append(
            {
                "label": label,
                "min_depth": start_d,
                "max_depth": end_d,
                "count": count,
            }
        )
    return histogram, peak_depth


def _build_dfs_backtrack_histogram(backtrack_depths: List[int], bins: int = 8) -> List[Dict[str, object]]:
    max_depth = max(backtrack_depths) if backtrack_depths else 32
    bucket_size = max(4, (max_depth + bins) // bins)
    histogram: List[Dict[str, object]] = []
    for i in range(bins):
        start_d = i * bucket_size
        end_d = start_d + bucket_size - 1
        if i == bins - 1:
            count = sum(1 for d in backtrack_depths if d >= start_d)
            label = f"Depth {start_d}+"
        else:
            count = sum(1 for d in backtrack_depths if start_d <= d <= end_d)
            label = f"Depth {start_d}-{end_d}"
        histogram.append(
            {
                "label": label,
                "min_depth": start_d,
                "max_depth": end_d,
                "count": count,
            }
        )
    return histogram


def run_bfs(maze: List[List[int]]) -> Dict[str, object]:
    size = len(maze)
    start = (0, 0)
    goal = (size - 1, size - 1)
    open_cells = sum(cell == 0 for row in maze for cell in row)

    t0 = time.perf_counter()
    visited = [[False] * size for _ in range(size)]
    parent: List[List[Optional[Tuple[int, int]]]] = [[None] * size for _ in range(size)]
    distance: List[List[int]] = [[-1] * size for _ in range(size)]
    visit_order: List[List[int]] = [[-1] * size for _ in range(size)]

    q: deque[Tuple[int, int]] = deque([start])
    visited[0][0] = True
    distance[0][0] = 0

    enqueue_ops = 1
    dequeue_ops = 0
    max_queue_size = 1
    reached_goal = False
    depth_counts: Dict[int, int] = {}
    steps: List[Dict[str, object]] = []

    while q:
        r, c = q.popleft()
        dequeue_ops += 1
        d = distance[r][c]
        visit_order[r][c] = dequeue_ops
        depth_counts[d] = depth_counts.get(d, 0) + 1

        if (r, c) == goal:
            reached_goal = True
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node": [r, c],
                    "dist": d,
                    "parent": list(parent[r][c]) if parent[r][c] else None,
                    "queue_snapshot": [[qr, qc, distance[qr][qc]] for qr, qc in list(q)[:8]],
                    "queue_size": len(q),
                    "enqueue_ops": enqueue_ops,
                    "dequeue_ops": dequeue_ops,
                    "status": "Goal Reached",
                }
            )
            break

        for dr, dc, _ in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and maze[nr][nc] == 0 and not visited[nr][nc]:
                visited[nr][nc] = True
                parent[nr][nc] = (r, c)
                distance[nr][nc] = d + 1
                q.append((nr, nc))
                enqueue_ops += 1

        if len(q) > max_queue_size:
            max_queue_size = len(q)

        steps.append(
            {
                "step": len(steps),
                "type": "explore",
                "node": [r, c],
                "dist": d,
                "parent": list(parent[r][c]) if parent[r][c] else None,
                "queue_snapshot": [[qr, qc, distance[qr][qc]] for qr, qc in list(q)[:8]],
                "queue_size": len(q),
                "enqueue_ops": enqueue_ops,
                "dequeue_ops": dequeue_ops,
                "status": f"Visited Wave #{dequeue_ops}",
            }
        )

    path: List[List[int]] = []
    if reached_goal:
        curr: Optional[Tuple[int, int]] = goal
        while curr is not None:
            path.append([curr[0], curr[1]])
            curr = parent[curr[0]][curr[1]]
        path.reverse()

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    depth_histogram, wave_peak_depth = _build_bfs_histogram(depth_counts)
    visited_count = dequeue_ops
    visited_ratio = round((visited_count / open_cells) * 100, 1) if open_cells else 0.0

    parent_grid = [
        [list(parent[r][c]) if parent[r][c] else None for c in range(size)]
        for r in range(size)
    ]

    return {
        "steps": steps,
        "path": path,
        "distances": distance,
        "parents": parent_grid,
        "visit_order": visit_order,
        "depth_histogram": depth_histogram,
        "wave_peak_depth": wave_peak_depth,
        "metadata": {
            "reached_goal": reached_goal,
            "visited_count": visited_count,
            "visited_ratio": visited_ratio,
            "path_length": max(0, len(path) - 1) if path else 0,
            "max_memory": max_queue_size,
            "enqueue_ops": enqueue_ops,
            "dequeue_ops": dequeue_ops,
            "operation_count": enqueue_ops + dequeue_ops,
            "elapsed_ms": elapsed_ms,
        },
    }


def run_dfs(maze: List[List[int]], optimal_path_length: int) -> Dict[str, object]:
    size = len(maze)
    start = (0, 0)
    goal = (size - 1, size - 1)
    open_cells = sum(cell == 0 for row in maze for cell in row)

    t0 = time.perf_counter()
    visited = [[False] * size for _ in range(size)]
    parent: List[List[Optional[Tuple[int, int]]]] = [[None] * size for _ in range(size)]
    depth_grid: List[List[int]] = [[-1] * size for _ in range(size)]

    stack: List[Tuple[int, int]] = [start]
    visited[0][0] = True
    depth_grid[0][0] = 1

    push_ops = 1
    pop_ops = 0
    max_stack_depth = 1
    backtrack_count = 0
    backtrack_depths: List[int] = []
    reached_goal = False
    steps: List[Dict[str, object]] = []

    while stack:
        r, c = stack[-1]
        cur_depth = len(stack)

        if (r, c) == goal:
            reached_goal = True
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node": [r, c],
                    "depth": cur_depth,
                    "parent": list(parent[r][c]) if parent[r][c] else None,
                    "stack_snapshot": [
                        [sr, sc, idx + 1]
                        for idx, (sr, sc) in reversed(list(enumerate(stack))[-8:])
                    ],
                    "stack_size": cur_depth,
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": False,
                    "backtrack_count": backtrack_count,
                    "status": "Goal Reached",
                }
            )
            break

        found_next = False
        chosen_dir = "Path"
        for dr, dc, dir_name in DIRECTIONS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and maze[nr][nc] == 0 and not visited[nr][nc]:
                visited[nr][nc] = True
                parent[nr][nc] = (r, c)
                depth_grid[nr][nc] = cur_depth + 1
                stack.append((nr, nc))
                push_ops += 1
                if len(stack) > max_stack_depth:
                    max_stack_depth = len(stack)
                found_next = True
                chosen_dir = dir_name
                break

        if found_next:
            steps.append(
                {
                    "step": len(steps),
                    "type": "explore",
                    "node": [r, c],
                    "depth": cur_depth,
                    "parent": list(parent[r][c]) if parent[r][c] else None,
                    "stack_snapshot": [
                        [sr, sc, idx + 1]
                        for idx, (sr, sc) in reversed(list(enumerate(stack))[-8:])
                    ],
                    "stack_size": len(stack),
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": False,
                    "backtrack_count": backtrack_count,
                    "status": f"Probing {chosen_dir} Path",
                }
            )
        else:
            popped = stack.pop()
            pop_ops += 1
            backtrack_count += 1
            backtrack_depths.append(cur_depth)
            steps.append(
                {
                    "step": len(steps),
                    "type": "backtrack",
                    "node": [popped[0], popped[1]],
                    "depth": len(stack),
                    "parent": list(parent[popped[0]][popped[1]])
                    if parent[popped[0]][popped[1]]
                    else None,
                    "stack_snapshot": [
                        [sr, sc, idx + 1]
                        for idx, (sr, sc) in reversed(list(enumerate(stack))[-8:])
                    ],
                    "stack_size": len(stack),
                    "push_ops": push_ops,
                    "pop_ops": pop_ops,
                    "is_backtrack": True,
                    "backtrack_count": backtrack_count,
                    "status": "Backtracking (Dead-end)",
                }
            )

    path = [[r, c] for r, c in stack] if reached_goal else []
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    backtrack_histogram = _build_dfs_backtrack_histogram(backtrack_depths)
    visited_count = push_ops
    visited_ratio = round((visited_count / open_cells) * 100, 1) if open_cells else 0.0
    path_length = max(0, len(path) - 1) if path else 0
    overhead_pct = (
        round(((path_length - optimal_path_length) / optimal_path_length) * 100, 1)
        if optimal_path_length > 0 and path_length >= optimal_path_length
        else 0.0
    )

    parent_grid = [
        [list(parent[r][c]) if parent[r][c] else None for c in range(size)]
        for r in range(size)
    ]

    return {
        "steps": steps,
        "path": path,
        "depths": depth_grid,
        "parents": parent_grid,
        "backtrack_histogram": backtrack_histogram,
        "metadata": {
            "reached_goal": reached_goal,
            "visited_count": visited_count,
            "visited_ratio": visited_ratio,
            "path_length": path_length,
            "path_overhead_pct": overhead_pct,
            "max_memory": max_stack_depth,
            "push_ops": push_ops,
            "pop_ops": pop_ops,
            "backtrack_count": backtrack_count,
            "operation_count": push_ops + pop_ops,
            "elapsed_ms": elapsed_ms,
        },
    }


@app.get("/")
def root() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": "bfs-dfs-couple",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/health")
def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": "bfs-dfs-couple",
        "gemini_api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/simulate")
def simulate(req: SimulateRequest) -> Dict[str, object]:
    t_total = time.perf_counter()
    if req.custom_maze is not None:
        size = len(req.custom_maze)
        if size < 5 or any(len(row) != size for row in req.custom_maze):
            raise HTTPException(status_code=400, detail="custom_maze must be a square 2D grid (>= 5x5).")
        maze = [[1 if cell else 0 for cell in row] for row in req.custom_maze]
        maze[0][0] = 0
        maze[size - 1][size - 1] = 0
    else:
        size = _normalize_odd_size(req.grid_size)
        maze = generate_maze(size, req.maze_type, req.seed)

    open_cells = sum(cell == 0 for row in maze for cell in row)
    bfs_result = run_bfs(maze)
    optimal_len = int(bfs_result["metadata"]["path_length"])
    dfs_result = run_dfs(maze, optimal_len)

    max_steps = max(len(bfs_result["steps"]), len(dfs_result["steps"]), 1) - 1
    total_elapsed_ms = round((time.perf_counter() - t_total) * 1000, 3)

    return {
        "status": "ok",
        "grid_size": size,
        "maze_type": req.maze_type,
        "seed": req.seed,
        "open_cells": open_cells,
        "start": [0, 0],
        "goal": [size - 1, size - 1],
        "direction_order": DIRECTION_LABELS,
        "maze": maze,
        "max_steps": max_steps,
        "total_elapsed_ms": total_elapsed_ms,
        "bfs": bfs_result,
        "dfs": dfs_result,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
