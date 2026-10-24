from __future__ import annotations

import math


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        if abs(m[col][col]) < 1e-12:
            continue
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] if abs(m[i][i]) > 1e-12 else 0.0 for i in range(n)]


def least_squares(xs: list[list[float]], ys: list[float], ridge: float = 1e-3) -> tuple[list[float], float]:
    """Return weights and R^2 for y ~ x."""
    k = len(xs[0])
    xtx = [[sum(x[i] * x[j] for x in xs) + (ridge if i == j else 0.0) for j in range(k)] for i in range(k)]
    xty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(k)]
    w = solve(xtx, xty)
    mean = sum(ys) / len(ys)
    ss_tot = sum((y - mean) ** 2 for y in ys) or 1e-12
    ss_res = sum((y - sum(wi * xi for wi, xi in zip(w, x))) ** 2 for x, y in zip(xs, ys))
    return w, max(0.0, 1 - ss_res / ss_tot)


def nnls_box(b_cols: list[tuple[float, float]], target: tuple[float, float], iters: int = 60) -> list[float]:
    """Non-negative actuator commands in [0, 1] whose combined effect approximates target."""
    n = len(b_cols)
    norm2 = sum(c[0] ** 2 + c[1] ** 2 for c in b_cols) or 1.0
    eta = 1.0 / norm2
    a = [0.0] * n
    for _ in range(iters):
        rx = sum(a[i] * b_cols[i][0] for i in range(n)) - target[0]
        ry = sum(a[i] * b_cols[i][1] for i in range(n)) - target[1]
        for i in range(n):
            g = b_cols[i][0] * rx + b_cols[i][1] * ry
            a[i] = min(1.0, max(0.0, a[i] - eta * g))
    return a


def apply(b_cols: list[tuple[float, float]], a: list[float]) -> tuple[float, float]:
    return (sum(ai * c[0] for ai, c in zip(a, b_cols)), sum(ai * c[1] for ai, c in zip(a, b_cols)))


def rotate(v: tuple[float, float], angle: float) -> tuple[float, float]:
    c, s = math.cos(angle), math.sin(angle)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])
