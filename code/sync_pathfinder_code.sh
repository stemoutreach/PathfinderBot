#!/bin/bash

REPO_URL="https://github.com/stemoutreach/PathfinderBot.git"
CLONE_DIR="/home/robot/PathfinderBot"
TARGET_DIR="/home/robot/code"

echo "🔄 Syncing 'code/' folder from PathfinderBot into $TARGET_DIR"

# First-time setup: clone with sparse-checkout
if [ ! -d "$CLONE_DIR" ]; then
  echo "📥 First-time clone..."
  git clone --filter=blob:none --no-checkout "$REPO_URL" "$CLONE_DIR"
  cd "$CLONE_DIR" || exit 1

  git sparse-checkout init --cone
  git sparse-checkout set code
  git checkout
else
  echo "🔁 Pulling latest changes from GitHub..."
  cd "$CLONE_DIR" || exit 1
  git reset --hard
  git pull
fi

# Rsync to update target directory
echo "📂 Syncing code to $TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Use --delete if you want to remove files GitHub has deleted
rsync -av "$CLONE_DIR/code/" "$TARGET_DIR/"

echo "✅ Resync complete!"

