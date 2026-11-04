# -*- coding: utf-8 -*-
"""引力透镜查找表（LUT）—— 与源 HTML 的 traceGeodesic/lutSolve/buildLensLUT 完全一致
的纯 Python 移植，零第三方依赖，可在无 GL 上下文的环境里离线烘焙。

表结构（128 行 × 4 通道 RGBA-float）：
  每行对应一个 |beta| 采样点：
    x = theta_primary（主像偏角，单位弧度）
    y = mu_r_primary（径向放大率）
    z = theta_secondary（次像偏角；<0 表示次像不存在，缩入阴影）
    w = mu_r_secondary（次像径向放大率）
采样按 beta 绝对值均匀分布：beta_abs = i * PI / (LUT_N - 1)。

运行 `python3 lenslut.py` 会把默认 ratio 对应的表烘焙到 lens_lut.bin，
供 stars.py 作为浮点纹理上传。
"""
import math
import struct
import os

LUT_N = 128


def trace_geodesic(th, rs, r0):
    """后向追踪一条零测地线：u = 1/r, u'' = -u + 1.5*rs*u^2。
    返回源相对透镜轴的带符号角 beta；None 表示落入视界。"""
    u = 1.0 / r0
    du = u / math.tan(th)
    phi = 0.0
    uMax = 1.0 / (1.0001 * rs)
    for i in range(20000):
        r = 1.0 / u
        h = min(max(0.02 * (1.0 + 0.6 * math.exp(-r / (8.0 * rs))), 0.0006), 0.05)
        a1 = du
        b1 = -u + 1.5 * rs * u * u
        u2 = u + 0.5 * h * a1
        d2 = du + 0.5 * h * b1
        a2 = d2
        b2 = -u2 + 1.5 * rs * u2 * u2
        u3 = u + 0.5 * h * a2
        d3 = du + 0.5 * h * b2
        a3 = d3
        b3 = -u3 + 1.5 * rs * u3 * u3
        u4 = u + h * a3
        d4 = du + h * b3
        a4 = d4
        b4 = -u4 + 1.5 * rs * u4 * u4
        u += (h / 6.0) * (a1 + 2.0 * a2 + 2.0 * a3 + a4)
        du += (h / 6.0) * (b1 + 2.0 * b2 + 2.0 * b3 + b4)
        phi += h
        if u <= 1e-9:
            break
        if u > uMax:
            return None
    psi = math.atan2(u, du)
    phInf = phi + math.pi - psi
    return math.atan2(math.sin(phInf), -math.cos(phInf))


def lut_solve(ths, betas, target):
    """在单调段 (ths, betas)（beta 递减）中反解：给定 beta 返回对应 theta，-1 无解。"""
    n = len(betas)
    if n < 2 or target > betas[0] or target < betas[n - 1]:
        return -1.0
    lo = 0
    hi = n - 1
    while hi - lo > 1:
        m = (lo + hi) >> 1
        if betas[m] > target:
            lo = m
        else:
            hi = m
    db = betas[lo] - betas[hi]
    f = 0.0 if abs(db) < 1e-12 else (betas[lo] - target) / db
    return ths[lo] + f * (ths[hi] - ths[lo])


def build_lens_lut(ratio, r0=12.0):
    """建表：对每个 beta_abs 采样点，存 (theta_primary, mu_r_primary,
    theta_secondary, mu_r_secondary)。"""
    rs = max(ratio * r0, 1e-6)
    # 1) 二分找阴影边界
    lo = 1e-5
    hi = math.pi / 2.0
    for k in range(50):
        m = (lo + hi) / 2.0
        if trace_geodesic(m, rs, r0) is None:
            lo = m
        else:
            hi = m
    thSh = hi
    # 2) 从 theta = PI 往回扫；beta 随 theta 单调递减，一旦回头即进入光子环高阶像区
    NS = 700
    ths = [math.pi]
    betas = [math.pi]
    prevB = math.pi
    for i in range(1, NS):
        th = math.pi - (math.pi - thSh * 1.0002) * (i / (NS - 1))
        b = trace_geodesic(th, rs, r0)
        if b is None:
            break
        while b - prevB > math.pi:
            b -= 2.0 * math.pi
        while prevB - b > math.pi:
            b += 2.0 * math.pi
        if b > prevB + 1e-9:
            break
        if b < -math.pi:
            break
        ths.append(th)
        betas.append(b)
        prevB = b
    if len(ths) < 2:
        return None
    # 3) 按 beta_abs 均匀采样反解
    data = [0.0] * (LUT_N * 4)
    dStep = math.pi / (LUT_N - 1)
    for i in range(LUT_N):
        bAbs = i * dStep
        tp = lut_solve(ths, betas, bAbs)
        ts = lut_solve(ths, betas, -bAbs)
        tpA = lut_solve(ths, betas, bAbs + dStep * 0.5)
        tpB = lut_solve(ths, betas, bAbs - dStep * 0.5)
        mrP = 1.0
        if tpA >= 0 and tpB >= 0:
            mrP = abs((tpA - tpB) / dStep)
        mrS = 0.5
        tsA = lut_solve(ths, betas, -(bAbs + dStep * 0.5))
        tsB = lut_solve(ths, betas, -(bAbs - dStep * 0.5))
        if ts >= 0 and tsA >= 0 and tsB >= 0:
            mrS = abs((tsA - tsB) / dStep)
        data[i * 4 + 0] = tp if tp >= 0 else math.pi
        data[i * 4 + 1] = max(mrP, 0.02)
        data[i * 4 + 2] = ts if ts >= 0 else -1.0
        data[i * 4 + 3] = max(mrS, 0.02)
    return data


def default_ratio(ring_in=3.05, distance=30.0):
    """与网页 v2.155 一致：rs = ringIn/2.598076, r0 = |相机-黑洞| = distance。
    ringIn=3.05 -> uRs=1.173946, ratio = rs/r0 = 0.0391315。"""
    return (ring_in / 2.598076) / abs(distance)


def bake(path="lens_lut.bin", ratio=None):
    if ratio is None:
        ratio = default_ratio()
    data = build_lens_lut(ratio)
    if data is None:
        raise RuntimeError("build_lens_lut 返回 None（阴影扫描为空），请检查 ratio")
    with open(path, "wb") as f:
        f.write(struct.pack("<%df" % (LUT_N * 4), *data))
    return path, len(data)


def load(path="lens_lut.bin"):
    with open(path, "rb") as f:
        raw = f.read()
    n = len(raw) // 4
    return list(struct.unpack("<%df" % n, raw))


if __name__ == "__main__":
    p, n = bake()
    print("baked", p, "floats", n, "(bytes", n * 4, ")")
