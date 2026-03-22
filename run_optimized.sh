#!/bin/bash
# 优化启动脚本
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 内存优化环境变量
export PYTHONOPTIMIZE=2
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export MALLOC_TRIM_THRESHOLD_=65536
export MALLOC_MMAP_THRESHOLD_=131072
export PYTHONMALLOC=malloc

echo "🚀 启动米哈游游戏自动化工具（优化模式）"
cd "$PROJECT_DIR"
python3 -OO main.py
