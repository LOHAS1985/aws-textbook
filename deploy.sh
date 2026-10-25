#!/bin/sh
# ビルドして main を push し、book/ の中身を gh-pages ブランチに公開する(GitHub Pages)
# 使い方: sh deploy.sh "修正内容"
# コミットメッセージは「YYYY-MM-DD 修正内容」になる(日付は自動で付く)
set -e
cd "$(dirname "$0")"
# 定期エージェントが毎日ニュースを push するので、先に取り込む。
# 生成物(book/ のページと sw.js)は取り込み後にビルドし直すので、手元の変更を捨てて衝突を避ける
for p in book/services book/terms book/usecases book/news book/index.html book/links.html book/sw.js; do
  git checkout -- "$p" 2>/dev/null || true
done
git pull --rebase --autostash origin main
if python -c "" 2>/dev/null; then
  PYTHONIOENCODING=utf-8 python build.py
else
  echo "WARNING: Python が見つからないためビルドを省略します(book/ は更新されません)" >&2
fi
git add -A
git diff --cached --quiet || git commit -m "$(date +%Y-%m-%d) ${1:-教科書を更新}"
git push origin main
git push origin "$(git subtree split --prefix book main)":refs/heads/gh-pages --force
