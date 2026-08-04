// SessionStart hook: injects the full i-have-adhd ruleset when the user has
// opted in by creating $CLAUDE_CONFIG_DIR/.i-have-adhd-always (default ~/.claude).
// Never blocks session start: any failure exits 0.

const fs = require('fs');
const os = require('os');
const path = require('path');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const flagPath = path.join(claudeDir, '.i-have-adhd-always');

try {
  if (!fs.existsSync(flagPath)) process.exit(0);

  const skillPath = path.join(__dirname, '..', 'SKILL.md');
  const body = fs
    .readFileSync(skillPath, 'utf8')
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, ''); // strip YAML frontmatter

  console.log(
    'ADHD MODE ACTIVE (always-on). The ruleset below applies to every response. ' +
      '"stop adhd mode" turns it off for this session; ' +
      `delete ${flagPath} to turn always-on off for good.\n\n${body}`
  );
} catch {}
