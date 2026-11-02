# Sourced from ~/.bashrc (on-create.sh adds the line). Puts booley-demo-claim
# on PATH and, in sponsored mode only, offers the demo sign-in once: in the
# first interactive terminal after the Codespace starts without a token.
#
# Sponsored mode means Booley's BOOLEY_AGENT_APP=auto found no Claude or Codex
# credential of the visitor's own and chose the demo gateway; it records that
# choice in ~/.booley-agent-app.json.

case $- in *i*) ;; *) return 0 ;; esac

_booley_demo_bin="$(dirname "${BASH_SOURCE[0]}")/bin"
case ":$PATH:" in *":$_booley_demo_bin:"*) ;; *) PATH="$_booley_demo_bin:$PATH" ;; esac
unset _booley_demo_bin

_booley_demo_offer() {
  local offered="$HOME/.config/booley-demo/offered"
  # Only a terminal someone is typing in. VS Code also starts interactive
  # shells without one (to read the container's environment); those must not
  # use up the one offer.
  [[ -t 0 && -t 1 ]] || return 0
  [[ -e $offered ]] && return 0
  grep -Eqs '"policy": *"gateway"' "$HOME/.booley-agent-app.json" || return 0
  # A saved token means the visitor already signed in.
  "${BOOLEY_GATEWAY_TOKEN_COMMAND:-false}" >/dev/null 2>&1 && return 0
  # Offer once: a visitor who declines or closes the terminal is not asked again.
  mkdir -p "${offered%/*}" && : >"$offered"
  printf '\nWelcome to the free Booley demo. Sign in with GitHub to get a demo token.\n\n'
  booley-demo-claim ||
    printf '\nNo token yet. Run booley-demo-claim any time to try again.\n'
}
_booley_demo_offer
unset -f _booley_demo_offer
