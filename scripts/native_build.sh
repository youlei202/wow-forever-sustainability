#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
export WOWFS_ENGINE_ROOT="${WOWFS_ENGINE_ROOT:-$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2}"
export PATH="$WOWFS_WORK_ROOT/envs/r2-go/go/bin:$WOWFS_WORK_ROOT/envs/r2-go/protoc/bin:$WOWFS_WORK_ROOT/cache/r2-discovery/go-path/bin:$PATH"
export GOPATH="$WOWFS_WORK_ROOT/cache/r2-discovery/go-path"
export GOCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-build"
export GOMODCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-mod"
export GOTOOLCHAIN=local
expected=17d75ccc8c67d027ae0088243ea3ee806d406847
actual="$(git -C "$WOWFS_ENGINE_ROOT" rev-parse HEAD)"
test "$actual" = "$expected" || { printf 'Unexpected engine commit: %s\n' "$actual" >&2; exit 2; }
mkdir -p "$WOWFS_ENGINE_ROOT/cmd/wowfs-r2" "$WOWFS_WORK_ROOT/envs/r2-go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_ablation.go" "$WOWFS_ENGINE_ROOT/sim/core/wowfs_r2_ablation.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_main.go" "$WOWFS_ENGINE_ROOT/cmd/wowfs-r2/main.go"
cd "$WOWFS_ENGINE_ROOT"
protoc -I=./proto --go_out=./sim/core ./proto/*.proto
go build -tags=with_db -o "$WOWFS_WORK_ROOT/envs/r2-go/wowfs-native" ./cmd/wowfs-r2
printf '%s\n' "$WOWFS_WORK_ROOT/envs/r2-go/wowfs-native"
