# Sourced from ~/.bashrc (on-create.sh adds the line). Puts booley-demo-claim
# on PATH in interactive shells.
#
# The visitor runs booley-demo-claim themselves (CODESPACES.md step 1). It is
# not offered automatically in the first terminal: clicking Trust opens that
# terminal, and the Booley Dashboard terminal opens over it at the same moment,
# hiding the notice the visitor has to read.

case $- in *i*) ;; *) return 0 ;; esac

_booley_demo_bin="$(dirname "${BASH_SOURCE[0]}")/bin"
case ":$PATH:" in *":$_booley_demo_bin:"*) ;; *) PATH="$_booley_demo_bin:$PATH" ;; esac
unset _booley_demo_bin
