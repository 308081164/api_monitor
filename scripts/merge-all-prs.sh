#!/usr/bin/env bash
# 由仓库所有者 (308081164) 在本地执行，依次合并 PR #1 → #2 → #3 到 main
set -euo pipefail

REPO="${GITHUB_REPO:-308081164/api_monitor}"
cd "$(dirname "$0")/.."

echo "==> 合并 PR #1 (Phase 1 MVP)"
gh pr merge 1 --repo "$REPO" --merge --delete-branch

echo "==> 更新 main"
git fetch origin main
git checkout main
git pull origin main

echo "==> 合并 PR #2 (Phase 2)"
gh pr merge 2 --repo "$REPO" --merge --delete-branch
git pull origin main

echo "==> 合并 PR #3 (Phase 3)"
gh pr merge 3 --repo "$REPO" --merge --delete-branch
git pull origin main

echo "==> 完成。当前 main:"
git log --oneline -5
