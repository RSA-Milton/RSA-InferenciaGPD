#!/usr/bin/env bash
# sync_remote_files.sh
# Sincronización unidireccional con rclone:
#   - pull: Drive -> Local
#   - push: Local -> Drive
# Configuración por carpeta en ./.syncenv (incluye COMMAND=pull|push para modo por defecto)

set -euo pipefail

LOCK_DIR="/tmp/sync_remote_files.lock"

timestamp() { date +%Y%m%d_%H%M%S; }

need_rclone() {
  if ! command -v rclone >/dev/null 2>&1; then
    echo "ERROR: rclone no está instalado o no está en PATH." >&2
    exit 1
  fi
}

with_lock() {
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    trap "rm -rf '${LOCK_DIR}'" EXIT
  else
    echo "Ya hay una sincronización en curso. Sal." >&2
    exit 1
  fi
}

usage() {
  cat <<'EOF'
Uso:
  sync_remote_files.sh [pull|push] [opciones rclone...]

Si no indicas modo, se usará COMMAND del .syncenv del directorio actual.

Modos:
  pull         Drive -> Local
  push         Local -> Drive
  --dry-run    Simula la operación sin copiar, borrar o mover ningún archivo.
  -v           Aumenta la verbosidad del log, mostrando más detalles sobre cada archivo que sería copiado, borrado o respaldado.

Ejemplos:
  sync_remote_files.sh --dry-run -v
  sync_remote_files.sh pull -v
EOF
}

load_per_folder_config() {
  LOCAL_PATH="$(pwd)"
  REMOTE="${REMOTE:-gdrive}"
  REMOTE_PATH="${REMOTE_PATH:-$(basename "$LOCAL_PATH")}"
  LOCAL_BACKUP_ROOT="${LOCAL_BACKUP_ROOT:-.sync_bk}"
  REMOTE_BACKUP_ROOT="${REMOTE_BACKUP_ROOT:-Respaldos_$(basename "$LOCAL_PATH")}"
  COMMON_EXTRA="${COMMON_EXTRA:- --fast-list }"

  DEFAULT_EXCLUDES=(
    '--exclude=/\.syncenv'
    '--exclude=/.sync_bk/**'
    '--exclude=**/sync_*.sh'
  )

  COMMON_FLAGS_SYNC=(--update --create-empty-src-dirs)
  # shellcheck disable=SC2206
  COMMON_FLAGS_SYNC+=(${COMMON_EXTRA})

  EXCLUDES_ARR=("${DEFAULT_EXCLUDES[@]}")
  if [[ -n "${EXCLUDES:-}" ]]; then
    # shellcheck disable=SC2206
    EXCLUDES_ARR+=(${EXCLUDES})
  fi

  EXCLUDES_FILE_FLAG=()
  if [[ -n "${EXCLUDES_FILE:-}" && -f "${EXCLUDES_FILE}" ]]; then
    EXCLUDES_FILE_FLAG=(--exclude-from="${EXCLUDES_FILE}")
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
  echo "Modo: PULL (Drive -> Local)"
  rclone sync "${REMOTE}:${REMOTE_PATH}" "${LOCAL_PATH}" \
    --backup-dir="${bk}" --suffix=".old" \
    "${COMMON_FLAGS_SYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

do_push() {
  local bk="${REMOTE_BACKUP_ROOT%/}/$(timestamp)"
  echo "Modo: PUSH (Local -> Drive)"
  rclone sync "${LOCAL_PATH}" "${REMOTE}:${REMOTE_PATH}" \
    --backup-dir="${REMOTE}:${bk}" --suffix=".old" \
    "${COMMON_FLAGS_SYNC[@]}" "${EXCLUDES_ARR[@]}" "${EXCLUDES_FILE_FLAG[@]}" "$@"
}

resolve_mode() {
  local cli_mode="${1:-}"

  # Mostrar ayuda si el primer argumento es help/-h/--help
  if [[ "${cli_mode}" == "help" || "${cli_mode}" == "-h" || "${cli_mode}" == "--help" ]]; then
    usage
    exit 0
  fi

  if [[ "${cli_mode:-}" == "pull" || "${cli_mode:-}" == "push" ]]; then
    MODE="${cli_mode}"
    shift || true
    REMAINING_ARGS=("$@")
    return 0
  fi

  if [[ ! -f ".syncenv" ]]; then
    echo "ERROR: No se indicó modo y no existe .syncenv en el directorio actual." >&2
    usage
    exit 1
  fi

  if [[ -z "${COMMAND:-}" ]]; then
    echo "ERROR: No se indicó modo y .syncenv no define COMMAND." >&2
    usage
    exit 1
  fi

  if [[ "${COMMAND}" != "pull" && "${COMMAND}" != "push" ]]; then
    echo "ERROR: COMMAND en .syncenv debe ser 'pull' o 'push' (valor actual: '${COMMAND}')." >&2
    exit 1
  fi

  MODE="${COMMAND}"
  REMAINING_ARGS=("$@")
}


main() {
  need_rclone

  # Cargar .syncenv si existe
  if [[ -f ".syncenv" ]]; then
    # shellcheck disable=SC1091
    source ".syncenv"
  fi

  resolve_mode "$@"
  load_per_folder_config
  safety_checks
  with_lock

  case "${MODE}" in
    pull) do_pull "${REMAINING_ARGS[@]}" ;;
    push) do_push "${REMAINING_ARGS[@]}" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
