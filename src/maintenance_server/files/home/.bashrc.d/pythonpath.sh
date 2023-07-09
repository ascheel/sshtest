_path="${HOME}/pythonlibs"

if [[ -z "${PYTHONPATH}" ]]; then
    export PYTHONPATH="$_path"
else
    export PYTHONPATH="${PYTHONPATH}:${HOME}/pythonlibs"
fi
