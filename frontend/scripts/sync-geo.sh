#!/usr/bin/env bash
# engine/out 의 GeoJSON 을 frontend/public/geo 로 복사한다.
# 시설 지도(facilities_*.geojson)는 아직 origin/hyunjun 브랜치에만 있어 git show 로 꺼낸다.
# 사용: frontend/ 에서  bash scripts/sync-geo.sh   (저장소 어디서든 동작)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/engine/out"
DEST="$ROOT/frontend/public/geo"
FACILITY_REF="${FACILITY_REF:-origin/hyunjun}"

mkdir -p "$DEST"

echo "[sync-geo] engine/out -> public/geo"
for f in "$SRC"/types_*.geojson "$SRC"/candidates_*.geojson "$SRC"/sim_*.geojson; do
  [ -e "$f" ] || continue
  cp "$f" "$DEST/$(basename "$f")"
  echo "  copied $(basename "$f")"
done

# 작업 트리에 시설 파일이 있으면 그것을, 없으면 지정 브랜치에서 꺼낸다
for region in 강남 춘천; do
  name="facilities_${region}.geojson"
  if [ -e "$SRC/$name" ]; then
    cp "$SRC/$name" "$DEST/$name"; echo "  copied $name"
  elif git -C "$ROOT" cat-file -e "$FACILITY_REF:engine/out/$name" 2>/dev/null; then
    git -C "$ROOT" show "$FACILITY_REF:engine/out/$name" > "$DEST/$name"; echo "  extracted $name from $FACILITY_REF"
  else
    echo "  !! $name 없음 (engine/out 에도, $FACILITY_REF 에도)" >&2
  fi
done

echo "[sync-geo] done:"; ls -la "$DEST"
