#!/bin/sh
# ビルドして main を push し、book/ の中身を gh-pages ブランチに公開する(GitHub Pages)
# 使い方: sh deploy.sh "コミットメッセージ"
set -e
cd "$(dirname "$0")"
PYTHONIOENCODING=utf-8 python build.py
git add -A
git diff --cached --quiet || git commit -m "${1:-教科書を更新}"
git push origin main
git push origin "$(git subtree split --prefix book main)":refs/heads/gh-pages --force
