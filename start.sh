#!/usr/bin/env bash
# Account 记账App 一键启动脚本
# 使用：在项目文件夹里运行 ./start.sh

cd "$(dirname "$0")"                        # 先切到项目所在文件夹
source "$HOME/anaconda3/etc/profile.d/conda.sh"  # 激活 conda
conda activate vibe_coding_learning
python main.py
