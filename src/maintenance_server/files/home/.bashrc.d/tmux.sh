# This is meant to be sourced by .bashrc

tmuxname="maintenance"

function t () {
    tmux has-session -t $tmuxname >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        tmux new-session -t $tmuxname
    else
        tmux attach-session -d -t $tmuxname
    fi
}
