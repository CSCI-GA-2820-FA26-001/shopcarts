#!/bin/sh
# Run from the repository root. All generated files stay outside the source tree.
set -eu

case "${BASE_URL:-}" in
    http://?*|https://?*) ;;
    *) echo "BASE_URL must be the HTTP or HTTPS URL of the test deployment." >&2; exit 2 ;;
esac

if [ ! -f Pipfile ] || [ ! -f Pipfile.lock ]; then
    echo "Run this script from the cloned repository containing Pipfile and Pipfile.lock." >&2
    exit 2
fi

bdd_tmp=$(mktemp -d "${TMPDIR:-/tmp}/shopcarts-bdd.XXXXXX")
export XDG_CACHE_HOME="$bdd_tmp/cache"
export XDG_CONFIG_HOME="$bdd_tmp/config"
export PIP_CACHE_DIR="$bdd_tmp/pip-cache"
export PIPENV_CACHE_DIR="$bdd_tmp/pipenv-cache"
export PYTHONDONTWRITEBYTECODE=1
export PIPENV_DONT_LOAD_ENV=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$PIP_CACHE_DIR" "$PIPENV_CACHE_DIR"

# Use the image's Pipenv to verify/export the committed lock; never regenerate it.
python -m pipenv verify
python -m pipenv requirements --dev --hash > "$bdd_tmp/requirements.txt"
python -m venv "$bdd_tmp/venv"
"$bdd_tmp/venv/bin/python" -m pip install --require-hashes --no-deps -r "$bdd_tmp/requirements.txt"

# Preserve Behave's exit status so any failed scenario fails the Task/Pipeline.
exec "$bdd_tmp/venv/bin/python" -m behave
