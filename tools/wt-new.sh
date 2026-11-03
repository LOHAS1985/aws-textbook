#!/bin/sh
# 作業用の worktree を作る(ブランチは origin/main から分岐する)
# 使い方: sh tools/wt-new.sh 名前
# 作業フォルダは ../aws-textbook-wt/名前 。編集が終わったら sh tools/wt-publish.sh 名前 "修正内容"
set -e
name="$1"
[ -n "$name" ] || { echo '使い方: sh tools/wt-new.sh 名前' >&2; exit 1; }
primary="$(cd "$(dirname "$0")/.." && cd "$(git rev-parse --git-common-dir)/.." && pwd)"
cd "$primary"
git fetch origin main
git worktree add -b "$name" "$primary/../aws-textbook-wt/$name" origin/main
wt="$primary/../aws-textbook-wt/$name"
# Windows の Python ランチャーは実行したフォルダに約165MBの Python を作るので、本体の Python/ をジャンクションで共有する
if [ -d "$primary/Python" ] && [ ! -e "$wt/Python" ]; then
  cmd.exe //c mklink //J "$(cygpath -w "$wt/Python")" "$(cygpath -w "$primary/Python")" >/dev/null
fi
echo "作成しました: $wt"
