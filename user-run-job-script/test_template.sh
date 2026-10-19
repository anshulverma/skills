#!/usr/bin/env bash
# Exercises run_jobs.template.sh end to end with stub steps and a stub tmux; launches nothing.
# Run after editing the template: bash test_template.sh
set -u
T=$(mktemp -d)
python3 - "$T" "$(dirname "$(readlink -f "$0")")/run_jobs.template.sh" <<'PY'
import re,sys
T=sys.argv[1]
s=open(sys.argv[2]).read()
s=s.replace('__SESSION__','tmpltest_sess').replace('__LOG_PATH__',T+'/run.log').replace('__SCRIPT_PATH__',T+'/run.sh').replace('__PURPOSE__','test')
s=re.sub(r'STEPS=\(  # STEPS-BEGIN\n.*?\n\)  # STEPS-END', 'STEPS=(  # STEPS-BEGIN\n  "a|echo ran-a; exit ${FAIL:-0}"\n  "b|echo ran-b; ls /proc/self/fd/8 2>&1 | tail -1; sleep ${SLEEP_B:-0}"\n)  # STEPS-END', s, flags=re.S)
s=s.replace(': __PREFLIGHT__','[[ -z ${FAIL_PRE:-} ]] || false; echo preflight-ok')
open(T+'/run.sh','w').write(s)
PY
bash -n $T/run.sh && echo syntax_ok; grep -c '__[A-Z0-9_]*__' $T/run.sh
mkdir $T/stub; printf '#!/bin/bash\necho "tmux $*" >> %s/tmux.calls\n[[ $1 == has-session ]] && exit ${STUB_HAS:-1}\nexit 0\n' $T > $T/stub/tmux; chmod +x $T/stub/tmux
run_outer() { env -u CLAUDECODE PATH=$T/stub:$PATH "$@" bash $T/run.sh; echo "exit=$?"; }
echo "--- leftover session, lock free:"; : > $T/tmux.calls; run_outer STUB_HAS=0; cat $T/tmux.calls
echo "--- session exists, lock held:"; : > $T/tmux.calls; ( exec 9>$T/run.log.lock; flock 9; sleep 5 ) & sleep 0.5; run_outer STUB_HAS=0; cat $T/tmux.calls; wait
echo "--- outer preflight failure:"; : > $T/tmux.calls; run_outer STUB_HAS=1 FAIL_PRE=1; grep -c new-session $T/tmux.calls; tail -1 $T/run.log
echo "--- inner fail at a (b must not run):"; FAIL=3 IN_RUNNER_TMUX=1 bash $T/run.sh >/dev/null; echo "exit=$?"; grep -c ran-b $T/run.log
echo "--- inner full run (fd 8 must not reach step b):"; IN_RUNNER_TMUX=1 bash $T/run.sh | grep -E 'ran-b|fd/8|No such'; echo "exit=${PIPESTATUS[0]}"
echo "--- HUP:"; SLEEP_B=30 IN_RUNNER_TMUX=1 setsid bash $T/run.sh >/dev/null & P=$!; sleep 2; kill -HUP -- -$P; wait $P; echo "exit=$?"; sleep 1
echo "--- RESULT lines:"; grep -o 'RESULT: [^=]*' $T/run.log
command rm -rf $T
