#!/usr/bin/env bash
# Build the committed source distribution; runtime files require no pip packages.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
version="$(cat VERSION)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || { echo 'Commit all changes before packaging.' >&2; exit 1; }
mkdir -p dist
git archive --format=tar --prefix="shm-$version/" HEAD | gzip -n > "dist/shm-$version.tar.gz"
(cd dist && sha256sum "shm-$version.tar.gz" > SHA256SUMS)
printf 'Built dist/shm-%s.tar.gz and dist/SHA256SUMS\n' "$version"
