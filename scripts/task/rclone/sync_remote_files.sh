#!/usr/bin/env bash
set -euo pipefail

LOCK_DIR="/tmp/sync_remote_files.lock"

timestamp() { date +%Y%m%d_%H%M%S; }

need_rclone() {
  if ! command -v rclone >/dev/null 2>&1; then
    echo "ERROR: rclone no esta instalado o no esta en PATH." >&2
    exit 1
  fi
}

with_lock() {
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    trap "rm -rf '${LOCK_DIR}'" EXIT
  else
    echo "Ya hay una sincronizacion en curso. Sal." >&2
    exit 1
  fi
}

usage() {
  cat <<'EOF'
Uso:
  sync_remote_files.sh <modo> [opciones rclone...]

Modos:
  pull            Drive -> Local (con respaldo local)
  push            Local -> Drive (con respaldo en Drive)
  bisync          Bidireccional (recomendado para uso diario)
  bisync-resync   Inicializacion de bisync (solo la primera vez)
  --dry-run       Simula la operación sin copiar, borrar o mover ningún archivo.
  -v              Aumenta la verbosidad del log, mostrando más detalles sobre cada archivo que sería copiado, borrado o respaldado.
EOF
}

load_per_folder_config() {
  LOCAL_PATH="$(pwd)"
  REMOTE="${REMOTE:-gdrive}"
  REMOTE_PATH="${REMOTE_PATH:-$(basename "$LOCAL_PATH")}"
  LOCAL_BACKUP_ROOT="${LOCAL_BACKUP_ROOT:-.sync_bk}"
  REMOTE_BACKUP_ROOT="${REMOTE_BACKUP_ROOT:-Respaldos_Acelerografos/$(basename "$LOCAL_PATH")}"
  COMMON_EXTRA="${COMMON_EXTRA:- --fast-list }"

  DEFAULT_EXCLUDES=(
    '--exclude=/\.syncenv'
    '--exclude=/.sync_bk/**'
    '--exclude=**/sync_*.sh'
  )

  # Flags para sync (pull/push)
  COMMON_FLAGS_SYNC=(--update --create-empty-src-dirs)
  # Flags para bisync (sin --create-empty-src-dirs)
  COMMON_FLAGS_BISYNC=(--update)

  # Añadir extra del usuario
  # shellcheck disable=SC2206
  COMMON_FLAGS_SYNC+=(${COMMON_EXTRA})
  # shellcheck disable=SC2206
  COMMON_FLAGS_BISYNC+=(${COMMON_EXTRA})

  EXCLUDES_ARR=("${DEFAULT_EXCLUDES[@]}")
  if [[ -n "${EXCLUDES:-}" ]]; then
    # shellcheck disable=SC2206
    EXCLUDES_ARR+=(${EXCLUDES})
  fi

  EXCLUDES_FILE_FLAG=()
  if [[ -n "${EXCLUDES_FILE:-}" && -f "${EXCLUDES_FILE}" ]]; then
    EXCLUDES_FILE_FLAG=(--exclude-from="${EXCLUDES_FILE}")
  fi

  if rclone bisync -h 2>&1 | grep -q -- "--conflict-resolve"; then
    CONFLICT_FLAG=(--conflict-resolve newer)
  else
    CONFLICT_FLAG=()
  fi
}

safety_checks() {
  if [[ "${REMOTE_BACKUP_ROOT}" == "${REMOTE_PATH}" ]] || [[ "${REMOTE_BACKUP_ROOT}" == ${REMOTE_PATH}/* ]]; then
    echo "ERROR: REMOTE_BACKUP_ROOT no debe estar dentro de REMOTE_PATH."
    exit 1
  fi
}

do_pull() {
  local bk="${LOCAL_PATH%/}/${LOCAL_BACKUP_ROOT%/}/$(timestamp)"
  mkdir -p "${bk}"
  rclone sync "${REMOTE}:${REMOTE_PATH}" "${LOCAL_PATH}" \
    --backup-dir="${bk}" --suffix=".old" \
    "${COMMON_FLAGS_SYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

do_push() {
  local bk="${REMOTE_BACKUP_ROOT%/}/$(timestamp)"
  rclone sync "${LOCAL_PATH}" "${REMOTE}:${REMOTE_PATH}" \
    --backup-dir="${REMOTE}:${bk}" --suffix=".old" \
    "${COMMON_FLAGS_SYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

do_bisync() {
  rclone bisync "${LOCAL_PATH}" "${REMOTE}:${REMOTE_PATH}" \
    --backup-dir "${REMOTE}:${REMOTE_BACKUP_ROOT}" \
    --remove-empty-dirs \
    "${CONFLICT_FLAG[@]}" \
    "${COMMON_FLAGS_BISYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

do_bisync_resync() {
  rclone bisync "${LOCAL_PATH}" "${REMOTE}:${REMOTE_PATH}" \
    --backup-dir "${REMOTE}:${REMOTE_BACKUP_ROOT}" \
    --remove-empty-dirs --resync \
    "${CONFLICT_FLAG[@]}" \
    "${COMMON_FLAGS_BISYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

main() {
  need_rclone
  if [[ $# -lt 1 ]]; then usage; exit 1; fi
  local mode="$1"; shift || true
  if [[ -f ".syncenv" ]]; then
    source ".syncenv"
  fi
  load_per_folder_config
  safety_checks
  with_lock
  case "${mode}" in
    pull)            do_pull "$@" ;;
    push)            do_push "$@" ;;
    bisync)          do_bisync "$@" ;;
    bisync-resync)   do_bisync_resync "$@" ;;
    -h|--help|help)  usage ;;
    *)               usage; exit 1 ;;
  esac
}

main "$@"
