#!/usr/bin/env bash
# Build the Lambda deployment zip — without Docker.
#
# The reason this needs care: psycopg ships compiled wheels, and the wheel that
# works on this Mac (macOS/arm64) is not the wheel Lambda needs
# (manylinux/aarch64). uv resolves for a *target* platform with
# --python-platform, which is what makes a Docker-free cross-build possible.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build/lambda"
ZIP="$ROOT/build/lambda.zip"

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD"

uv export --frozen --no-dev --no-emit-project --quiet -o "$BUILD/requirements.txt"

# manylinux_2_28, not manylinux2014: the Python 3.12 Lambda runtime is Amazon
# Linux 2023 (glibc 2.34), and greenlet no longer ships 2014-tagged aarch64
# wheels. arm64 because Graviton Lambda is cheaper per ms.
uv pip install \
  --target "$BUILD" \
  --python-platform aarch64-manylinux_2_28 \
  --python-version 3.12 \
  --only-binary=:all: \
  --quiet \
  -r "$BUILD/requirements.txt"

rm "$BUILD/requirements.txt"

# Application code + the seed CSVs the one-off seed handler reads.
cp -R "$ROOT/app" "$BUILD/app"
cp -R "$ROOT/scripts" "$BUILD/scripts"
cp -R "$ROOT/data" "$BUILD/data"
rm -f "$BUILD/scripts/build_lambda.sh"

find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

# Do NOT strip *.dist-info. psycopg reads its own version through
# importlib.metadata, so without the metadata it reports 0.0.0.0 and
# SQLAlchemy refuses it with "psycopg version 3.0.2 or higher is required".

(cd "$BUILD" && zip -qr "$ZIP" .)
printf 'built %s (%s)\n' "$ZIP" "$(du -h "$ZIP" | cut -f1)"
