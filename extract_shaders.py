#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从源 HTML 中精确抽黑洞着色器，转换为桌面 GLSL 3.30 core，生成 shaders.py。

纯机械转换：复用盘面公共实现与 bhMat 的 fragmentShader 主体；
把 varying / gl_FragColor（GLSL ES）改为 in / out（桌面 330 core）；
用相机基向量 + NDC 重建世界射线 rd；逃逸光线用程序化星空上色（starLens:false 默认）。
不依赖任何第三方包，纯标准库。
"""
import io
import re

BQ = chr(96)
TOK = "DISK_" + "COMMON_" + "GLSL"
DL = chr(36) + "{" + TOK + "}"
NL = chr(10)

SRC = "/home/u/blackhole/v2155/黑洞模拟_v2155.html"
OUT = "/home/u/blackhole/blackhole-screensaver/shaders.py"


def extract_common(html):
    key = "const " + TOK + " = " + BQ
    s = html.index(key) + len(key)
    e = html.index(BQ + ";" + NL, s)
    return html[s:e]


def extract_frag(html):
    bidx = html.index("bhMat = new THREE.ShaderMaterial({")
    fidx = html.index("fragmentShader: " + BQ, bidx)
    s = fidx + len("fragmentShader: " + BQ)
    e = html.index(BQ, s)
    return html[s:e]


COMMON = None
FRAG_INNER = None


def collect_prefix_consts(prefix):
    """v2155 把部分 const（如 EDGE_GAIN）声明在 varying 之前；抽取时前缀被整体裁掉
    会导致这些常量在 main 里 undeclared。这里只把前缀里的 `const float X = ...;`
    抽出来回填到 body 开头，且不与 body 内（DISK_COMMON_GLSL 等）重复声明。"""
    out = []
    seen = set()
    for ln in prefix.split("\n"):
        s = ln.strip()
        m = re.match(r"const\s+float\s+(\w+)\s*=", s)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(ln.rstrip())
    return "\n".join(out)


def build_frag():
    global COMMON, FRAG_INNER
    vi = FRAG_INNER.index("varying vec3 vWorldPos;")
    prefix = FRAG_INNER[:vi]
    body = FRAG_INNER[vi + len("varying vec3 vWorldPos;"):]
    consts = collect_prefix_consts(prefix)
    if consts:
        body = consts + NL + body

    body = body.replace(
        "vec3 rd = normalize(vWorldPos - uCamPos);",
        "vec3 rd = normalize(uCamFwd + vNdc.x * uTanFov * uAspect * uCamRight + vNdc.y * uTanFov * uCamUp);",
    )
    body = body.replace("vec3 ro = uCamPos - uBH;", "vec3 ro = uCamPos;")

    body = body.replace(
        "gl_FragColor = vec4(acc, 1.0);",
        "fragColor = vec4(acc, 1.0);",
    )
    # v2155 的 alpha = max(clamp(1.0 - T, 0.0, 1.0), occ) 即盘面不透明度；
    # 保留它，让 COMPOSITE_FS 的 s.rgb*(1-d.a) 在盘面透明处透出星空层
    # （StarLayer：主像背景星 + 镜向爱因斯坦环），与网页版一致。
    # 不再把程序化 starField 注入盘着色器（星空统一由 StarLayer 负责）。
    body = body.replace(
        "gl_FragColor = vec4(acc + ring, max(clamp(1.0 - T, 0.0, 1.0), occ));",
        "fragColor = vec4(acc + ring, max(clamp(1.0 - T, 0.0, 1.0), occ));",
    )

    si = body.index("void main()")
    frag = HEADER + body
    return frag


HEADER = """#version 330 core
out vec4 fragColor;
in vec2 vNdc;
uniform float uTime;
uniform vec3  uCamPos;
uniform vec3  uCamFwd;
uniform vec3  uCamRight;
uniform vec3  uCamUp;
uniform float uTanFov;
uniform float uAspect;
uniform vec3  uDiskN;
uniform vec3  uDiskAx;
uniform vec3  uDiskAy;
uniform float uInner;
uniform float uOuter;
uniform float uBrightness;
uniform float uRotSpeed;
uniform float uRs;
uniform float uArc;
uniform float uTempK;
uniform float uMaxSteps;
uniform float uRefine;
"""


STARFIELD = """// ===================== 程序化星空（对应 starLens:false 默认） =====================
float hash13(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.yzx + 33.33);
  return fract((p.x + p.y) * p.z);
}
vec3 starField(vec3 dir) {
  vec3 col = vec3(0.0);
  for (int L = 0; L < 3; L++) {
    float scale = 70.0 * pow(2.0, float(L));
    vec3 p  = dir * scale;
    vec3 ip = floor(p);
    vec3 fp = fract(p);
    float h = hash13(ip + float(L) * 17.0);
    float thr = 0.985;
    if (h > thr) {
      vec3 sp = vec3(hash13(ip + 1.7), hash13(ip + 4.3), hash13(ip + 9.1));
      float d = length(fp - sp);
      float b = smoothstep(0.10, 0.0, d) * (h - thr) / (1.0 - thr);
      float t = hash13(ip + 12.3);
      vec3 sc = mix(vec3(0.75, 0.83, 1.0), vec3(1.0, 0.92, 0.78), t);
      col += sc * b * (0.5 + 0.5 * (1.0 - float(L) * 0.30));
    }
  }
  float band = pow(max(0.0, 1.0 - abs(dir.y) * 1.6), 3.0);
  col += vec3(0.02, 0.03, 0.05) * band;
  return col;
}
"""

VERT = """#version 330 core
in vec2 aPos;
out vec2 vNdc;
void main() {
  vNdc = aPos;
  gl_Position = vec4(aPos, 0.0, 1.0);
}
"""


def main():
    global COMMON, FRAG_INNER
    with io.open(SRC, "r", encoding="utf-8") as f:
        html = f.read()
    COMMON = extract_common(html)
    FRAG_INNER = extract_frag(html).replace(DL, COMMON)
    frag = build_frag()

    out = (
        "# -*- coding: utf-8 -*-" + NL
        + "# 本文件由 extract_shaders.py 自动生成，请勿手改；改源 HTML 后重新运行抽取脚本。" + NL + NL
        + "VERT = " + repr(VERT) + NL + NL
        + "FRAG = " + repr(frag) + NL
    )
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", OUT)
    print("VERT lines:", VERT.count(NL), "FRAG lines:", frag.count(NL))


if __name__ == "__main__":
    main()
