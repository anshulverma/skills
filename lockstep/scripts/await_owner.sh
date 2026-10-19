#!/bin/bash
# Block until a human comment or reply lands on any of the given docs, print it and exit 0.
# Usage: await_owner.sh DOC_ID [DOC_ID ...]   (one await per doc in parallel; the first human event wins)
set -u
[ $# -ge 1 ] || { echo "usage: await_owner.sh DOC_ID [DOC_ID ...]" >&2; exit 2; }
RETRY=${AWAIT_RETRY_SECS:-15}

first_human() {  # print the first event body that is not ours, flattened to one line
  python3 -c 'import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("{\"seq\""):
        continue
    try:
        body = json.loads(line).get("payload", {}).get("gdrive", {}).get("comment_body", "") or ""
    except ValueError:
        continue
    if body and not body.startswith("[🤖") and not body.startswith("(cont'"'"'d"):
        print(" ".join(body.split())[:300]); break'
}

wait_one() {
  local doc=$1 out rc body
  while true; do
    out=$(meta google.docs await --id "$doc" --event-types comment.created,reply.created --auto-resume --timeout 3600 2>&1)
    rc=$?
    body=$(printf '%s\n' "$out" | first_human)
    if [ -n "$body" ]; then
      echo "HUMAN_EVENT doc=$doc body=$body"
      return 0
    fi
    if [ $rc -ne 0 ]; then  # auth lapse, ACL, network: back off instead of spinning
      echo "await_owner: meta await failed for $doc (exit $rc): $(printf '%s' "$out" | head -1)" >&2
      sleep "$RETRY"
    fi
  done
}

set -m  # each watcher gets its own process group, so cleanup also reaches its in-flight meta
pids=()
for d in "$@"; do wait_one "$d" & pids+=($!); done
cleanup() { for p in "${pids[@]}"; do kill -- "-$p" 2>/dev/null; done; }
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
wait -n
exit 0
