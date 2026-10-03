#!/bin/bash
# Chạy tự động khi Ona tạo môi trường (postCreateCommand). Có thể chạy lại an toàn.
set -e
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  git-core gnupg flex bison build-essential zip unzip curl zlib1g-dev libc6-dev-i386 \
  x11proto-core-dev libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils xsltproc \
  fontconfig python3 python-is-python3 rsync cpio ccache tmux bc libssl-dev lz4 \
  android-sdk-libsparse-utils openjdk-11-jdk-headless
mkdir -p "$HOME/.bin"
if [ ! -x "$HOME/.bin/repo" ]; then
  curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo -o "$HOME/.bin/repo"
  chmod +x "$HOME/.bin/repo"
fi
grep -q '.bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.bin:$PATH"' >> "$HOME/.bashrc"
git config --global user.name  >/dev/null 2>&1 || git config --global user.name  "twrp-builder"
git config --global user.email >/dev/null 2>&1 || git config --global user.email "builder@localhost"
git config --global color.ui false
echo "Setup xong. Chạy:  tmux new -s build  rồi  ./build-twrp.sh"
