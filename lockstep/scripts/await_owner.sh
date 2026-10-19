#!/bin/bash
# Block until a human comment or reply lands on any of the given docs, print it and exit 0.
# Usage: await_owner.sh DOC_ID [DOC_ID ...]   (one await per doc in parallel; the first human event wins)
set -u
wait_one() {
  local doc=$1 out body
  while true; do
    out=$(meta google.docs await --id "$doc" --event-types comment.created,reply.created --auto-resume --timeout 3600 2>&1)
    body=$(printf '%s' "$out" | python3 -c 'import sys, json
for line in sys.stdin:
    line = line.strip()
    if line.startswith("{\"seq\""):
        print(json.loads(line)["payload"]["gdrive"].get("comment_body", "")[:300]); break')
    [ -z "$body" ] && continue                 # timeout or no event: keep waiting
    case "$body" in "[🤖"*) continue ;; esac     # our own reply
    case "$body" in *"(cont'd"*) continue ;; esac  # continuation fragment of our own reply
    echo "HUMAN_EVENT doc=$doc body=$body"
    return 0
  done
}
trap 'kill $(jobs -p) 2>/dev/null' EXIT
for d in "$@"; do wait_one "$d" & done
wait -n
exit 0
