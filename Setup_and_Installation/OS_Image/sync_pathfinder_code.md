# `sync_pathfinder_code.md`

# Sync PathfinderBot `code/` Folder to Raspberry Pi

This document details how to **set up** and **resync** only the `code/` folder from the `PathfinderBot` GitHub repository into `/home/robot/code` on your Raspberry Pi, preserving any local files.

---

## 🎯 Overview

- Uses **Git sparse‑checkout** to clone just the `code/` directory.
- Employs **`rsync`** to sync updates while **preserving extra local files**.
- Automatically handles first-run setup and ongoing updates.

---

## 🛠️ Setup Script: `sync_pathfinder_code.sh`

\`\`\`bash
#!/bin/bash

REPO_URL="https://github.com/stemoutreach/PathfinderBot.git"
CLONE_DIR="/home/robot/PathfinderBot"
TARGET_DIR="/home/robot/code"

echo "🔄 Syncing 'code/' folder from PathfinderBot into $TARGET_DIR"

# First‑time setup: clone with sparse‑checkout
if [ ! -d "$CLONE_DIR" ]; then
  echo "📥 First‑time clone..."
  git clone --filter=blob:none --no‑checkout "$REPO_URL" "$CLONE_DIR"
  cd "$CLONE_DIR" || exit 1

  git sparse‑checkout init --cone
  git sparse‑checkout set code
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
\`\`\`

---

## 🚀 How to Install

1. On your Raspberry Pi (as user with sudo privileges), create the script:

   \`\`\`bash
   nano ~/sync_pathfinder_code.sh
   \`\`\`

2. Paste the script content above.
3. Save and exit: \`Ctrl+O\` → \`Enter\`, then \`Ctrl+X\`.
4. Make it executable:

   \`\`\`bash
   chmod +x ~/sync_pathfinder_code.sh
   \`\`\`

---

## ▶️ Usage

Run the script anytime to sync the `code/` folder:

\`\`\`bash
sudo ~/sync_pathfinder_code.sh
\`\`\`

Note: Use \`sudo\` if \`robot\` owns the target path and your current user is different.

---

## 📌 Notes

- ⚙️ **First run:** A sparse clone is created in `/home/robot/PathfinderBot` with only the `code` subdirectory.
- 🔄 **Subsequent runs:** Updates are pulled from GitHub and merged.
- 🗂️ **Rsync behavior:**  
  - Updates changed files  
  - **Preserves** files in `/home/robot/code/` that aren’t in GitHub  
  - Defaults to **not deleting** files GitHub has removed (unless you add `--delete` to the `rsync` flags)

---

## ⚙️ Optional Customization

- To **remove files** from the target that GitHub has deleted, modify the `rsync` command to:

  \`\`\`bash
  rsync -av --delete "$CLONE_DIR/code/" "$TARGET_DIR/"
  \`\`\`

- To **run automatically**, you can schedule it in `crontab`. Example:

  \`\`\`bash
  crontab -e
  \`\`\`

  Then add a line:

  \`\`\`
  0 * * * * /home/<user>/sync_pathfinder_code.sh
  \`\`\`

  This runs the script hourly.

---

## ✅ Summary

| Feature                          | Behavior                          |
|----------------------------------|-----------------------------------|
| Only clone the `code/` folder    | ✅ via sparse‑checkout             |
| Preserve extra local files       | ✅ with `rsync` (no `--delete`)   |
| Remove files deleted in GitHub   | ⚠️ Only if using `--delete`       |
| Easy first-time and resync setup | ✅ handled by the script           |

chmod +x ~/sync_pathfinder_code.sh

sudo ~/sync_pathfinder_code.sh

