#!/usr/bin/env bash
# create_lab.sh — provision LXC lab containers on U01/U02
# Naming: u01-<role> / u02-<role>   e.g. u01-javam-ci, u02-tsx-acquire
set -euo pipefail
IMAGE="${IMAGE:-ubuntu:24.04}"
DRY="${DRY:-0}"

create() {
  local name="$1" mem="$2" disk_gb="$3" cpu="${4:-}"
  if lxc info "$name" >/dev/null 2>&1; then
    echo "exists $name"
    return 0
  fi
  if [ "$DRY" = "1" ]; then
    echo "DRY create $name mem=$mem disk=${disk_gb}G cpu=$cpu"
    return 0
  fi
  echo "==> $name  mem=$mem disk=${disk_gb}G cpu=$cpu"
  lxc launch "$IMAGE" "$name"
  lxc config set "$name" limits.memory "$mem"
  lxc config set "$name" limits.cpu "$cpu"
  # disk: LXD uses default pool; set root size when storage supports it
  lxc config device set "$name" root size "${disk_gb}GB" 2>/dev/null || true
}

echo "host=$(hostname)  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
case "$(hostname)" in
  utility-01|U01)
    # M-stack / CI / oracles
    create u01-javam-ci    2GB  8  4
    create u01-mjvm-bench  2GB  8  4
    create u01-rsm-oracle  1GB  4  2
    create u01-dafny-lsp   2GB  5  4
    create u01-dev         1GB  5  2
    ;;
  utility-02|U02)
    # tsx / data / agents
    create u02-tsx-acquire   512MB 20 2
    create u02-tsx-loaders   512MB 10 2
    create u02-news-acquire  256MB  2 1
    create u02-agents        256MB  2 1
    create u02-cold-agent    256MB 50 1
    ;;
  *)
    echo "unknown host $(hostname) — set hostname or edit script" >&2
    exit 2
    ;;
esac

echo "--- inventory ---"
lxc list --columns ns4t
