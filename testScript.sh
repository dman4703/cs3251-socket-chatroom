#!/usr/bin/env bash
# testScript.sh — CS3251 PA1 functional tests for server.py/client.py
# Requires: bash, python3, grep, mktemp

set -euo pipefail

# You may override these via environment variables: PORT, PASS_OK, PASS_BAD, PYTHON
PORT="${PORT:-$((20000 + RANDOM % 20000))}"
PASS_OK="${PASS_OK:-abc12}"
PASS_BAD="${PASS_BAD:-wrong}"   # intentionally incorrect
PY="${PYTHON:-python3}"

# Sanity checks
[[ -f server.py && -f client.py ]] || { echo "Place testScript.sh beside server.py and client.py."; exit 1; }

TMPDIR="$(mktemp -d -t cs3251tests.XXXXXX)"
LOGS="$TMPDIR/logs"
mkdir -p "$LOGS"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && ps -p "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    sleep 0.1 || true
    kill -9 "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  # Uncomment to auto-remove logs:
  # rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "=== Starting server on 127.0.0.1:$PORT with passcode '$PASS_OK' ==="
$PY server.py -start -port "$PORT" -passcode "$PASS_OK" >"$LOGS/server.log" 2>&1 &
SERVER_PID=$!

# Wait for server banner "Server started on port <port>. Accepting connections"
for i in {1..50}; do
  grep -q "Server started on port $PORT\. Accepting connections" "$LOGS/server.log" && break
  sleep 0.1
done
if ! grep -q "Server started on port $PORT\. Accepting connections" "$LOGS/server.log"; then
  echo "Server failed to start. See $LOGS/server.log"
  exit 1
fi

# Wrong passcode attempt (client should print "Incorrect passcode")
echo "=== Launching wrong-passcode client (Eve) ==="
timeout 10s $PY client.py -join -host 127.0.0.1 -port "$PORT" -username Eve -passcode "$PASS_BAD" >"$LOGS/eve.log" 2>&1 || true

# Alice script: broadcast, emoji, time, :Users, :Msg Bob, exit
echo "=== Launching Alice and Bob clients ==="
(
  sleep 0.2
  echo "Hello Room"
  sleep 0.2
  echo ":)"
  sleep 1.0
  echo ":mytime"
  sleep 0.4
  echo ":Users"
  sleep 1.0
  echo ":Msg Bob CS3251 is awesome"
  sleep 0.2
  echo ":Exit"
) | timeout 15s $PY client.py -join -host 127.0.0.1 -port "$PORT" -username Alice -passcode "$PASS_OK" >"$LOGS/alice.log" 2>&1 &
ALICE_PID=$!

# Bob script: send +1hr after Alice is in, then exit
sleep 0.5
(
  sleep 0.8
  echo ":+1hr"
  sleep 1.8
  echo ":Exit"
) | timeout 15s $PY client.py -join -host 127.0.0.1 -port "$PORT" -username Bob -passcode "$PASS_OK" >"$LOGS/bob.log" 2>&1 &
BOB_PID=$!

wait "$ALICE_PID" "$BOB_PID" || true
sleep 0.4

# ---------- Assertions ----------
pass=0; fail=0
ok()   { echo "✅ $*"; ((++pass)); }
bad()  { echo "❌ $*"; ((++fail)); }
assert(){ if eval "$1"; then ok "$2"; else bad "$2"; fi }

echo "=== Checking results ==="

# Connection banners (README: connection establishment). 
assert "grep -q 'Connected to 127.0.0.1 on port $PORT' '$LOGS/alice.log'" "Alice sees connection success"
assert "grep -q 'Connected to 127.0.0.1 on port $PORT' '$LOGS/bob.log'"   "Bob sees connection success"
assert "grep -q '^Incorrect passcode$' '$LOGS/eve.log'"                   "Wrong passcode rejected by server"

# Join notifications (server + other clients)
assert "grep -q '^Alice joined the chatroom$' '$LOGS/server.log'"         "Server logs Alice join"
assert "grep -q '^Bob joined the chatroom$'   '$LOGS/server.log'"         "Server logs Bob join"
assert "grep -q '^Bob joined the chatroom$'   '$LOGS/alice.log'"          "Alice sees Bob join"

# Broadcast message (sender excluded on clients, delivered to others)
assert "grep -q '^Alice: Hello Room$' '$LOGS/server.log'"                 "Server logs Alice broadcast"
assert "grep -q '^Alice: Hello Room$' '$LOGS/bob.log'"                    "Bob receives Alice broadcast"
assert "! grep -q '^Alice: Hello Room$' '$LOGS/alice.log'"                "Sender does not see own broadcast"

# Emoji shortcuts :) -> [feeling happy] (sender excluded)
assert "grep -q '^Alice: \\[feeling happy\\]$' '$LOGS/server.log'"        "Server translates :) to [feeling happy]"
assert "grep -q '^Alice: \\[feeling happy\\]$' '$LOGS/bob.log'"           "Bob sees [feeling happy]"
assert "! grep -q '\\[feeling happy\\]' '$LOGS/alice.log'"                "Sender does not see own emoji"

# Time shortcuts (sender included)
assert "grep -E -q '^Alice: (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/server.log'" ":mytime printed on server"
assert "grep -E -q '^Alice: (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/alice.log'"  "Sender sees :mytime"
assert "grep -E -q '^Alice: (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/bob.log'"    "Others see :mytime"
assert "grep -E -q '^Bob:   (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/alice.log' || grep -E -q '^Bob: (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/alice.log'" "Alice sees Bob's :+1hr"
assert "grep -E -q '^Bob:   (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/bob.log'   || grep -E -q '^Bob: (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' '$LOGS/bob.log'"   "Bob sees own :+1hr"

# :Users format and server log line
assert "grep -q '^Alice: searched up active users$' '$LOGS/server.log'"   "Server logs :Users lookup line"
assert "grep -q '^Active Users:' '$LOGS/alice.log'"                       "Client shows Active Users list"
assert "grep -q 'Active Users: .*Alice' '$LOGS/alice.log'"                ":Users includes Alice"
assert "grep -q 'Active Users: .*Bob'   '$LOGS/alice.log'"                ":Users includes Bob"

# :Msg delivery + server log
assert "grep -q '^\\[Message from Alice\\]: CS3251 is awesome$' '$LOGS/bob.log'"  "Bob receives private message"
assert "grep -q '^Alice: send message to Bob$' '$LOGS/server.log'"                "Server logs :Msg event"

# :Exit leave notifications
assert "grep -q '^Alice left the chatroom$' '$LOGS/server.log'"           "Server logs Alice exit"
assert "grep -q '^Bob left the chatroom$'   '$LOGS/server.log'"           "Server logs Bob exit"
assert "grep -q '^Alice left the chatroom$' '$LOGS/bob.log'"              "Bob sees Alice leave"

echo
echo "=== Summary ==="
echo "Passed: $pass  Failed: $fail"
echo "Logs:   $LOGS"
exit $(( fail > 0 ))
