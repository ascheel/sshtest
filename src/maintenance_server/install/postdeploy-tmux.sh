#!/usr/bin/env bash

if command -v tmux >/dev/null 2>&1; then
    echo "tmux already installed."
    exit 0
fi

# For TMUX compilation
sudo yum install -y git automake make glibc-devel gcc patch libevent-devel ncurses-devel byacc

tmuxdir="${HOME}/tmp/tmux"
[[ ! -d "$tmuxdir" ]] && mkdir -p "${tmuxdir}"

git clone https://github.com/tmux/tmux "${tmuxdir}"

pushd "$tmuxdir"

./autogen.sh
./configure
make
sudo make install

popd
