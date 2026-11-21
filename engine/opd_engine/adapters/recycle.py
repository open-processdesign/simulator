"""Recycle handling for the sequential-modular reference engine (T08).

Two parts, both engine-independent:

1. **Solve plan.** Units are grouped into strongly connected components (Tarjan, 1972).
   The components are solved in topological order. A component with more than one unit
   (or a unit feeding itself) is a recycle loop: some of its streams are *torn* and
   converged iteratively. Tear streams are the back edges of a depth-first search that
   starts at the loop's entry units (those fed from outside the loop), which breaks every
   cycle (Westerberg, Hutchison, Motard and Winter, *Process Flowsheeting*, Cambridge
   University Press, 1979, ch. 3).

2. **Convergence.** Successive substitution x ← g(x), optionally accelerated with the
   bounded Wegstein method (J. H. Wegstein, "Accelerating convergence of iterative
   processes", *Communications of the ACM* 1(6):9–13, 1958), applied element-wise:

       s = (g_k − g_{k−1}) / (x_k − x_{k−1}),   q = s / (s − 1),   q ∈ [q_min, q_max]
       x_{k+1} = q·x_k + (1 − q)·g_k

   with q_min = −5, q_max = 0 as commonly used in process simulators (Seider, Seader,
   Lewin and Widagdo, *Product and Process Design Principles*, 3rd ed., Wiley, 2009,
   §5.4). The first two iterations are plain substitution.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------- solve plan

@dataclass
class Block:
    """Units solved together: one unit, or a recycle loop with its tear streams."""

    units: list[str]
    tears: list[str] = field(default_factory=list)

    @property
    def is_loop(self) -> bool:
        return bool(self.tears)


@dataclass(frozen=True)
class Edge:
    stream: str
    source: str
    target: str


def _strongly_connected(nodes: list[str], succ: dict[str, list[str]]) -> list[list[str]]:
    """Tarjan's algorithm (iterative). Returns components in reverse topological order."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[list[str]] = []
    counter = 0

    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(succ[root]))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(succ[nxt])))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                result.append(comp)
    return result


def _order_without(units: list[str], edges: list[Edge], removed: set[str]) -> list[str]:
    """Topological order of `units` using `edges` minus the `removed` streams (Kahn)."""
    inside = set(units)
    indeg = {u: 0 for u in units}
    succ: dict[str, list[str]] = {u: [] for u in units}
    for e in edges:
        if e.stream in removed or e.source not in inside or e.target not in inside:
            continue
        succ[e.source].append(e.target)
        indeg[e.target] += 1
    ready = [u for u in units if indeg[u] == 0]
    order: list[str] = []
    while ready:
        u = ready.pop(0)
        order.append(u)
        for v in succ[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    return order


def solve_plan(units: list[str], edges: list[Edge]) -> list[Block]:
    """Blocks in solve order. `units` keeps document order, used to break ties."""
    position = {u: k for k, u in enumerate(units)}
    succ: dict[str, list[str]] = {u: [] for u in units}
    for e in edges:
        if e.source in succ and e.target in succ:
            succ[e.source].append(e.target)

    blocks: list[Block] = []
    for comp in reversed(_strongly_connected(units, succ)):
        comp.sort(key=position.__getitem__)
        members = set(comp)
        internal = [e for e in edges if e.source in members and e.target in members]
        if len(comp) == 1 and not internal:
            blocks.append(Block(comp))
            continue
        tears = _tear_streams(comp, internal, edges)
        order = _order_without(comp, internal, set(tears))
        blocks.append(Block(order, tears))
    return blocks


def _tear_streams(comp: list[str], internal: list[Edge], edges: list[Edge]) -> list[str]:
    """Back edges of a DFS from the loop's entry units; removing them leaves no cycle."""
    members = set(comp)
    entries = [u for u in comp if any(e.target == u and e.source not in members for e in edges)]
    out: dict[str, list[Edge]] = {u: [] for u in comp}
    for e in internal:
        out[e.source].append(e)

    tears: list[str] = []
    state: dict[str, int] = {}  # 1 = on DFS path, 2 = done

    def visit(root: str) -> None:
        state[root] = 1
        work = [(root, iter(out[root]))]
        while work:
            node, it = work[-1]
            for e in it:
                s = state.get(e.target, 0)
                if s == 1:
                    tears.append(e.stream)
                elif s == 0:
                    state[e.target] = 1
                    work.append((e.target, iter(out[e.target])))
                    break
            else:
                state[node] = 2
                work.pop()

    for start in entries + comp:
        if state.get(start, 0) == 0:
            visit(start)
    return tears


# ---------------------------------------------------------------------- convergence

@dataclass
class Accelerator:
    """Successive substitution with optional bounded Wegstein acceleration."""

    method: str = "wegstein"  # or "direct"
    q_min: float = -5.0
    q_max: float = 0.0
    _x_prev: list[float] | None = None
    _g_prev: list[float] | None = None
    iterations: int = 0

    def next(self, x: list[float], g: list[float]) -> list[float]:
        self.iterations += 1
        if self.method != "wegstein" or self._x_prev is None or self.iterations <= 2:
            new = list(g)
        else:
            new = []
            for xk, gk, xp, gp in zip(x, g, self._x_prev, self._g_prev):  # type: ignore[arg-type]
                dx = xk - xp
                if abs(dx) <= 1e-14 * max(1.0, abs(xk)):
                    q = 0.0
                else:
                    s = (gk - gp) / dx
                    q = s / (s - 1.0) if s != 1.0 else self.q_min
                    q = min(self.q_max, max(self.q_min, q))
                new.append(q * xk + (1.0 - q) * gk)
        self._x_prev, self._g_prev = list(x), list(g)
        return new
