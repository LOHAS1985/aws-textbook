#!/bin/sh
# worktree の変更を main に取り込み、ビルドして公開する(GitHub Pages)
# 使い方: sh tools/wt-publish.sh 名前 "修正内容"
# 流れ: 1. main を origin に合わせる 2. worktree の変更を commit し main にリベース
#       3. main に squash でまとめ、ビルドして book/ を含めて commit 4. push(main と gh-pages)
#       5. worktree とブランチを削除
# 作業ブランチには book/(生成物)を含めない。直接編集するCSS・JS・アイコン等は保持する。
# コミットメッセージは「YYYY-MM-DD 修正内容」(日付は自動)
set -e
name="$1"
msg="$2"
[ -n "$name" ] && [ -n "$msg" ] || { echo '使い方: sh tools/wt-publish.sh 名前 "修正内容"' >&2; exit 1; }
primary="$(cd "$(dirname "$0")/.." && cd "$(git rev-parse --git-common-dir)/.." && pwd)"
wt="$primary/../aws-textbook-wt/$name"
[ -d "$wt" ] || { echo "worktree がありません: $wt" >&2; exit 1; }
subject="$(date +%Y-%m-%d) $msg"
trailer="Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
if ! python -c "" 2>/dev/null; then
  echo "Python が見つからないためビルドできません(公開を中止します)" >&2
  exit 1
fi

# build.py が生成するページだけを戻し、手作業で編集するアセットは残す
restore_generated_book() {
  git checkout -- book/checklist.html book/exercises book/index.html book/links.html book/news book/print \
    book/services book/terms book/usecases book/js/glossary.js book/sw.js
}

# 1. main を origin に合わせる(main 側に未コミットの変更があれば中止する)
cd "$primary"
restore_generated_book
if [ -n "$(git status --porcelain)" ]; then
  echo "main に未コミットの変更があります。先にコミットか退避をしてください" >&2
  git status --short >&2
  exit 1
fi
git pull --ff-only origin main

# 2. worktree の変更を commit し、最新の main にリベースする
cd "$wt"
restore_generated_book
git add -A -- . ':!book'
git add -A -- book/css/style.css book/icons book/js/quiz.js book/js/sim.js book/js/site.js book/manifest.webmanifest
git diff --cached --quiet || git commit -q -m "$subject" -m "$trailer"
if ! git rebase main; then
  echo "リベースで衝突しました。$wt で解消して git rebase --continue を実行してから、もう一度このスクリプトを実行してください" >&2
  exit 1
fi

# 3. main にまとめて取り込み、ビルドして book/ を含めて commit
cd "$primary"
git merge --squash "$name" >/dev/null
python build.py
git add -A
if git diff --cached --quiet; then
  echo "公開する変更がありません"
else
  git commit -q -m "$subject" -m "$trailer"
  # 4. push(deploy.sh と同じ。gh-pages は book/ の中身だけの履歴)
  git push origin HEAD:main
  git push origin "$(git subtree split --prefix book HEAD)":refs/heads/gh-pages --force
  published=1
fi

# 5. 後始末(Python のジャンクションは rmdir で外してから消す。中身の Python を消さないため)
# 公開は済んでいるので、後始末に失敗しても止めずに手動の手順を案内する
if [ -L "$wt/Python" ]; then
  cmd.exe //c rmdir "$(cygpath -w "$wt/Python")" || true
fi
if git worktree remove --force "$wt" && git branch -D "$name" >/dev/null; then
  rmdir "$primary/../aws-textbook-wt" 2>/dev/null || true
else
  echo "後始末に失敗しました。次を手動で行ってください: git worktree remove --force \"$wt\" ; git branch -D $name" >&2
fi
[ -z "$published" ] || echo "公開しました: $subject"
