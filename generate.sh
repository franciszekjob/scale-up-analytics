#!/bin/bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/net/pr2/projects/plgrid/plggmpr2025}"
DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data}"
DBGEN_DIR="${DBGEN_DIR:-$PROJECT_ROOT/tpch-dbgen}"
DBGEN_BIN="${DBGEN_BIN:-$DBGEN_DIR/dbgen}"
DSS_PATH="${DSS_PATH:-$DBGEN_DIR}"
DISTS_FILE="${DISTS_FILE:-$DBGEN_DIR/dists.dss}"
SCALE="${SCALE:-100}"
CHUNKS="${CHUNKS:-8}"

usage() {
    cat <<EOF
Usage:
  ./generate.sh smoke
  ./generate.sh full
  ./generate.sh

Environment overrides:
  PROJECT_ROOT  Default: $PROJECT_ROOT
  DATA_DIR      Default: $DATA_DIR
  DBGEN_DIR     Default: $DBGEN_DIR
  DBGEN_BIN     Default: $DBGEN_BIN
  DSS_PATH      Default: $DSS_PATH
  DISTS_FILE    Default: $DISTS_FILE
  SCALE         Default: $SCALE
  CHUNKS        Default: $CHUNKS

Examples:
  ./generate.sh smoke
  ./generate.sh
  SCALE=100 CHUNKS=8 ./generate.sh full
EOF
}

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

warn_if_login_node() {
    local host
    host="$(hostname)"
    if [[ "$host" == login* ]]; then
        echo "WARNING: wyglada na to, ze jestes na login node ($host)." >&2
        echo "Pelne generowanie uruchamiaj przez srun lub sbatch na wezle obliczeniowym." >&2
    fi
}

check_prerequisites() {
    [[ -x "$DBGEN_BIN" ]] || fail "Nie znaleziono wykonywalnego dbgen: $DBGEN_BIN"
    [[ -f "$DISTS_FILE" ]] || fail "Nie znaleziono pliku dists.dss: $DISTS_FILE"
    mkdir -p "$DATA_DIR"
    touch "$DATA_DIR/.write_test"
    rm -f "$DATA_DIR/.write_test"
}

show_config() {
    cat <<EOF
PROJECT_ROOT=$PROJECT_ROOT
DATA_DIR=$DATA_DIR
DBGEN_DIR=$DBGEN_DIR
DBGEN_BIN=$DBGEN_BIN
DSS_PATH=$DSS_PATH
DISTS_FILE=$DISTS_FILE
SCALE=$SCALE
CHUNKS=$CHUNKS
EOF
}

run_smoke() {
    cd "$DATA_DIR"
    export DSS_PATH

    rm -f nation.tbl nation.tbl.* dbgen_smoke.log

    echo "Uruchamiam smoke test (SF=1, tylko nation)..."
    "$DBGEN_BIN" -vf -b "$DISTS_FILE" -s 1 -T n > dbgen_smoke.log 2>&1 || {
        tail -50 dbgen_smoke.log >&2 || true
        fail "Smoke test nie powiodl sie."
    }

    if compgen -G "nation.tbl*" > /dev/null; then
        echo "Smoke test OK. Wygenerowane pliki:"
        ls -lh nation.tbl*
    else
        tail -50 dbgen_smoke.log >&2 || true
        fail "Smoke test zakonczyl sie bez wygenerowania nation.tbl."
    fi
}

run_full() {
    local chunk
    local pid
    local -a pids=()
    local failed=0

    cd "$DATA_DIR"
    export DSS_PATH

    warn_if_login_node

    echo "Czyszcze stare logi dbgen..."
    rm -f dbgen_*.log

    echo "Uruchamiam generowanie TPC-H SF=$SCALE w $CHUNKS chunkach..."
    if compgen -G "*.tbl*" > /dev/null; then
        echo "WARNING: w $DATA_DIR sa juz pliki *.tbl*." >&2
        echo "Jesli to pozostalosc po poprzedniej probie lub smoke tescie, rozwaz ich usuniecie przed pelnym runem." >&2
    fi

    for chunk in $(seq 1 "$CHUNKS"); do
        "$DBGEN_BIN" -vf -b "$DISTS_FILE" -s "$SCALE" -S "$chunk" -C "$CHUNKS" \
            > "dbgen_${chunk}.log" 2>&1 &
        pids+=("$!")
        echo "  chunk $chunk -> pid ${pids[-1]}, log: $DATA_DIR/dbgen_${chunk}.log"
    done

    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            failed=1
        fi
    done

    echo
    echo "Skan logow pod katem bledow:"
    grep -Hni "error\|cannot\|failed\|unknown" dbgen_*.log || true

    echo
    echo "Przykladowe wygenerowane pliki:"
    if compgen -G "*.tbl*" > /dev/null; then
        ls -lh *.tbl* | head -20
    else
        fail "Nie znaleziono zadnych plikow *.tbl* w $DATA_DIR."
    fi

    if [[ "$failed" -ne 0 ]]; then
        fail "Co najmniej jeden proces dbgen zakonczyl sie bledem. Sprawdz dbgen_*.log."
    fi

    echo
    echo "Generowanie zakonczone poprawnie."
}

main() {
    local mode="${1:-full}"

    check_prerequisites
    show_config
    echo

    case "$mode" in
        smoke)
            run_smoke
            ;;
        full)
            run_full
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            usage
            fail "Nieznany tryb: $mode"
            ;;
    esac
}

main "$@"
