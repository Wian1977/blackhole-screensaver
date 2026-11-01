#!/usr/bin/env bash
# 生成上架用 tarball：blackhole-screensaver/store/blackhole-screensaver-YYYYMMDD.tar.gz
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(basename "$ROOT")"
OUT="$ROOT/store/$NAME-$(date +%Y%m%d).tar.gz"
cd "$(dirname "$ROOT")"
tar --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' -czf "$OUT" "$NAME"
echo "created $OUT"
