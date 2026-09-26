#!/usr/bin/env bash
# systemd-user-sandbox.sh — run a command under a private systemd user manager.
#
# Linux fixture supervision (scripts/analysis/fixture_process_supervisor.py)
# runs each suite as a transient `systemd-run --user` unit and needs cgroup v2
# plus a user manager under /user.slice. Containers and VMs often have neither:
# PID 1 is not systemd, cgroups are v1 or hybrid, and `systemctl --user` has no
# manager to reach. This tool supplies one for the duration of one command, so
# the preflight and the fixture registry can be run and debugged on such hosts
# (it is how the systemd anchor timeout defect was reproduced and fixed).
#
# Usage (as root, from the package root or anywhere):
#
#   scripts/analysis/systemd-user-sandbox.sh python3 scripts/analysis/fixture_infrastructure_check.py
#   scripts/analysis/systemd-user-sandbox.sh python3 scripts/analysis/fixture_runner.py --no-write
#
# What it does, all inside a private mount namespace so the host is untouched:
#   - mounts cgroup v2 over /sys/fs/cgroup;
#   - mounts a tmpfs over /run/systemd holding the /run/systemd/system marker
#     systemd checks before it will run as a user instance;
#   - mounts a tmpfs over /run/user (no stale manager sockets) and sets
#     XDG_RUNTIME_DIR=/run/user/<uid>;
#   - starts `systemd --user` inside /user.slice/user-<uid>.slice/user@<uid>.service,
#     where a login session would place it (the supervisor refuses units outside
#     /user.slice);
#   - runs the command, then stops the manager and exits with the command's status.
#
# On a host whose user manager already works, the command runs directly.
# The manager's own log goes to $SYSTEMD_USER_SANDBOX_LOG (default: a temp file,
# printed on failure).
#
# Requires root (mount namespaces and cgroup mounts), util-linux `unshare`, and
# systemd >= 250 installed but not necessarily running. This is a development
# tool: CI's hosted runners have a real user manager and do not use it.

set -euo pipefail

# "degraded" (some unit failed) still has a working manager; only its exit
# status differs from "running".
manager_ready() {
    case "$(systemctl --user is-system-running 2>/dev/null || true)" in
        running|degraded) return 0 ;;
        *) return 1 ;;
    esac
}

if [[ -z "${SYSTEMD_USER_SANDBOX_INNER:-}" ]]; then
    if [[ $# -eq 0 ]]; then
        echo "usage: $0 <command> [args...]" >&2
        exit 2
    fi
    if [[ -f /sys/fs/cgroup/cgroup.controllers ]] && manager_ready; then
        echo "systemd-user-sandbox: this host's user manager already works; running directly" >&2
        exec "$@"
    fi
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "systemd-user-sandbox: must run as root (it mounts cgroup v2 in a private namespace)" >&2
        exit 2
    fi
    command -v unshare >/dev/null || { echo "systemd-user-sandbox: util-linux unshare is required" >&2; exit 2; }
    export SYSTEMD_USER_SANDBOX_INNER=1
    exec unshare --mount --propagation private "$BASH" "$0" "$@"
fi

unset SYSTEMD_USER_SANDBOX_INNER   # the command must not inherit the marker

systemd_bin=""
for candidate in /usr/lib/systemd/systemd /lib/systemd/systemd; do
    if [[ -x "$candidate" ]]; then systemd_bin="$candidate"; break; fi
done
if [[ -z "$systemd_bin" ]]; then
    echo "systemd-user-sandbox: systemd is not installed" >&2
    exit 2
fi

uid="$(id -u)"
log="${SYSTEMD_USER_SANDBOX_LOG:-$(mktemp -t systemd-user-sandbox.XXXXXX.log)}"

mount -t cgroup2 none /sys/fs/cgroup
mount -t tmpfs tmpfs /run/systemd
mkdir -p /run/systemd/system
mkdir -p /run/user
mount -t tmpfs tmpfs /run/user
export XDG_RUNTIME_DIR="/run/user/$uid"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
unset DBUS_SESSION_BUS_ADDRESS

manager_cgroup="/sys/fs/cgroup/user.slice/user-$uid.slice/user@$uid.service"
mkdir -p "$manager_cgroup"
# The subshell joins the manager cgroup before exec so systemd starts there;
# this shell stays in the root cgroup, which is exempt from the
# no-internal-processes rule.
( echo "$BASHPID" > "$manager_cgroup/cgroup.procs"
  exec "$systemd_bin" --user --log-target=console --log-level=warning ) >"$log" 2>&1 &
manager=$!

stop_manager() {
    kill "$manager" 2>/dev/null || true
    wait "$manager" 2>/dev/null || true
}
trap stop_manager EXIT

for _ in $(seq 1 100); do
    manager_ready && break
    sleep 0.1
done
if ! manager_ready; then
    echo "systemd-user-sandbox: the user manager did not start; its log ($log):" >&2
    cat "$log" >&2 || true
    exit 97
fi

set +e
"$@"
status=$?
set -e
exit "$status"
