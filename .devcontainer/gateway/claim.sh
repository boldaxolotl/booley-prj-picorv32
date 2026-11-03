#!/usr/bin/env bash
#
# Claim a Booley demo gateway token by signing in with GitHub.
#
# Shows the notice and asks you to type "yes". Then runs GitHub's device flow
# with the "Booley demo" OAuth app, which asks for no scopes (public profile
# only). The GitHub token is sent once to the gateway's /claim, which reads
# your account id and age and revokes the token right away. The gateway token
# is saved to ~/.config/booley-demo/token (mode 0600) and its expiry next to
# it (token.expires_at); token.sh prints the token.
#
# Usage: claim.sh [--force]     (--force replaces a token that has not expired)
# Needs only bash, curl and python3.
set -euo pipefail

NOTICE_VERSION=1 # bump on any notice change; the gateway lists the versions it accepts
GATEWAY_URL="${BOOLEY_GATEWAY_URL:-https://gw.booley.dev}"
GITHUB_URL="${BOOLEY_DEMO_GITHUB_URL:-https://github.com}"
CLIENT_ID="${BOOLEY_DEMO_CLIENT_ID:-Ov23liVr6AAfHA9qPDI7}" # public OAuth app id
TOKEN_FILE="${BOOLEY_DEMO_TOKEN_FILE:-$HOME/.config/booley-demo/token}"
BYO_URL="https://booley.dev/demo#bring-your-own-key"
MAX_EXPIRES_IN=1800 # GitHub device codes last 900 s; refuse anything far longer
MAX_INTERVAL=60     # seconds between polls, upper bound
MIN_INTERVAL="${BOOLEY_DEMO_MIN_POLL_S:-5}" # GitHub's minimum; tests lower it
MAX_POLLS=1000      # hard bound on top of the code's expiry deadline
STAMP_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' # UTC, sorts as text
EXPIRED="the sign-in code expired before it was approved. If github.com said there \
were too many attempts, wait a few minutes. Then run claim.sh again."

die() {
  printf 'claim.sh: %s\n' "$*" >&2
  exit 1
}

print_notice() {
  cat <<EOF
Booley demo notice (version $NOTICE_VERSION)

- This free demo is sponsored by the Booley maintainer.
- The agent is OpenAI GPT-6 Luna.
- Prompts and code go through our gateway to OpenAI. We log usage numbers,
  not content. OpenAI keeps API data up to 30 days and doesn't train on it.
- You sign in with GitHub; we read only your public profile (id and account
  age), and the GitHub token is revoked right after.
- Demo use only, with caps. You must be 18+ and in a supported country, and
  follow OpenAI's usage policies. Check outputs before relying on them.
- To use your own key instead, see: $BYO_URL

EOF
}

# json_field JSON KEY...: print the string or integer at that key path, with
# control characters removed (the text may end up on the terminal), or nothing.
# JSON goes through printf (a builtin) and a pipe, so it never shows in argv.
json_field() {
  printf '%s' "$1" | python3 -I -c '
import json, sys
try:
    value = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
for key in sys.argv[1:]:
    value = value.get(key) if isinstance(value, dict) else None
if isinstance(value, (str, int)) and not isinstance(value, bool):
    print("".join(c for c in str(value) if c.isprintable()))
' "${@:2}"
}

# http_post URL CURL_ARGS...: print the body, a newline, then the HTTP status
# (000 when there was no answer). Use split_reply on the result.
http_post() {
  local url=$1
  shift
  curl -sS --max-time 30 -X POST -H 'Accept: application/json' -w '\n%{http_code}' \
    "$@" "$url" 2>/dev/null || printf '\n000'
}

split_reply() {
  REPLY_STATUS="${1##*$'\n'}"
  REPLY_BODY="${1%$'\n'*}"
}

# Sets DEVICE_CODE, INTERVAL and EXPIRES_IN, and shows the visitor the code.
start_device_flow() {
  split_reply "$(http_post "$GITHUB_URL/login/device/code" --data-urlencode "client_id=$CLIENT_ID")"
  if [[ $REPLY_STATUS == 403 || $REPLY_STATUS == 429 ]]; then
    die "GitHub is limiting demo sign-ins right now. Try again in a few minutes, or bring \
your own key: $BYO_URL"
  fi
  DEVICE_CODE="$(json_field "$REPLY_BODY" device_code)"
  local user_code uri
  user_code="$(json_field "$REPLY_BODY" user_code)"
  uri="$(json_field "$REPLY_BODY" verification_uri)"
  EXPIRES_IN="$(json_field "$REPLY_BODY" expires_in)"
  INTERVAL="$(json_field "$REPLY_BODY" interval)"
  if [[ $REPLY_STATUS != 200 || -z $DEVICE_CODE || -z $user_code || $uri != https://* ]] ||
    [[ ! $EXPIRES_IN =~ ^[0-9]+$ || ! $INTERVAL =~ ^[0-9]+$ ]] ||
    ((EXPIRES_IN < 1 || EXPIRES_IN > MAX_EXPIRES_IN || INTERVAL > MAX_INTERVAL)); then
    local reason
    reason="$(json_field "$REPLY_BODY" error_description)"
    die "could not start GitHub sign-in (HTTP $REPLY_STATUS${reason:+: $reason}). Try again \
in a few minutes."
  fi
  ((INTERVAL >= MIN_INTERVAL)) || INTERVAL=$MIN_INTERVAL
  # Spell the steps out and make the link and code stand out: visitors missed
  # the one-line prompt and sat at "Waiting for approval..." without knowing
  # GitHub was waiting on them. Color only on a terminal, and never with NO_COLOR.
  local hi="" off="" rule
  if [[ -t 1 && -z ${NO_COLOR:-} ]]; then
    hi=$'\e[1;30;43m ' off=$' \e[0m'
  fi
  rule="$(printf '%*s' 64 '' | tr ' ' '=')"
  printf '\n%s\n' "$rule"
  printf '  Sign in with GitHub to get your token:\n\n'
  printf '  1. Open      %s%s%s\n' "$hi" "$uri" "$off"
  printf '  2. Enter     %s%s%s\n' "$hi" "$user_code" "$off"
  printf '  3. Click Authorize (GitHub shares only your public profile)\n'
  printf '%s\n\n' "$rule"
  printf 'Waiting for you to authorize on GitHub (Ctrl+C to cancel)...\n'
}

# The next poll interval after slow_down: GitHub's new value, else +5 s.
next_interval() {
  local current=$1 suggested
  suggested="$(json_field "$REPLY_BODY" interval)"
  if [[ $suggested =~ ^[0-9]+$ ]] && ((suggested > current && suggested <= MAX_INTERVAL)); then
    echo "$suggested"
  else
    echo $((current + 5 > MAX_INTERVAL ? MAX_INTERVAL : current + 5))
  fi
}

# Poll until the visitor approves; print the GitHub token on stdout. Bounded
# by the code's expiry and by MAX_POLLS.
poll_for_token() {
  local interval=$INTERVAL deadline polls token error
  deadline=$(($(date +%s) + EXPIRES_IN))
  for ((polls = 0; polls < MAX_POLLS; polls++)); do
    sleep "$interval"
    (($(date +%s) < deadline)) || die "$EXPIRED"
    split_reply "$(http_post "$GITHUB_URL/login/oauth/access_token" \
      --data-urlencode "client_id=$CLIENT_ID" --data-urlencode "device_code=$DEVICE_CODE" \
      --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:device_code")"
    token="$(json_field "$REPLY_BODY" access_token)"
    if [[ -n $token ]]; then
      printf '%s\n' "$token"
      return 0
    fi
    error="$(json_field "$REPLY_BODY" error)"
    case "$error" in
      authorization_pending) ;;
      slow_down) interval="$(next_interval "$interval")" ;;
      expired_token) die "$EXPIRED" ;;
      access_denied) die "sign-in was cancelled on GitHub. Run claim.sh again to retry." ;;
      "") [[ $REPLY_STATUS == 000 || $REPLY_STATUS == 5* ]] ||
        die "unexpected answer from GitHub (HTTP $REPLY_STATUS)." ;; # 000/5xx: retry
      *) die "GitHub sign-in failed: $error." ;;
    esac
  done
  die "$EXPIRED"
}

# Trade the GitHub token for a gateway token; print "TOKEN EXPIRES_AT". The GitHub
# token travels on pipes only: printf → python3 (builds the JSON) → curl.
claim_gateway_token() {
  local reply token expires message
  reply="$(printf '%s' "$1" | python3 -I -c '
import json, sys
print(json.dumps({"github_token": sys.stdin.read().strip(), "notice_version": sys.argv[1]}))
' "$NOTICE_VERSION" | http_post "$GATEWAY_URL/claim" -H 'Content-Type: application/json' \
    --data-binary @-)"
  split_reply "$reply"
  [[ $REPLY_STATUS != 000 ]] ||
    die "could not reach the Booley demo gateway ($GATEWAY_URL). Try again in a minute."
  if [[ $REPLY_STATUS != 200 ]]; then
    message="$(json_field "$REPLY_BODY" error message)"
    die "${message:-the gateway answered HTTP $REPLY_STATUS. Try again in a minute.}"
  fi
  token="$(json_field "$REPLY_BODY" token)"
  expires="$(json_field "$REPLY_BODY" expires_at)"
  [[ $token =~ ^bgw_[A-Za-z0-9_-]{20,}$ && $expires =~ $STAMP_RE ]] ||
    die "the gateway sent an unexpected answer."
  printf '%s %s\n' "$token" "$expires"
}

# Has the saved token not expired yet? (No expiry file: treat as expired.)
token_still_valid() {
  local expires=""
  [[ -s $TOKEN_FILE && -r "$TOKEN_FILE.expires_at" ]] || return 1
  IFS= read -r expires <"$TOKEN_FILE.expires_at" || true
  [[ $expires =~ $STAMP_RE && $expires > $(date -u +%Y-%m-%dT%H:%M:%SZ) ]]
}

# save_token TOKEN EXPIRES_AT: write both atomically, readable only by you.
save_token() {
  write_private "$TOKEN_FILE" "$1"
  write_private "$TOKEN_FILE.expires_at" "$2"
}

# write_private FILE LINE: atomic write, mode 0600, directory 0700 if we create it.
write_private() {
  local file=$1 dir tmp
  dir="$(dirname "$file")"
  # Only the token's own directory needs 0700; parents (e.g. ~/.config) keep the umask.
  # shellcheck disable=SC2174
  [[ -d $dir ]] || mkdir -p -m 700 "$dir"
  tmp="$(mktemp "$dir/.token.XXXXXX")" # created 0600
  if ! { printf '%s\n' "$2" >"$tmp" && chmod 600 "$tmp" && mv -f "$tmp" "$file"; }; then
    rm -f "$tmp"
    die "could not save $file."
  fi
}

main() {
  local force=0 answer="" github_token claimed
  case "${1:-}" in
    --force) force=1 ;;
    "") ;;
    *) die "usage: claim.sh [--force]" ;;
  esac
  for tool in curl python3; do
    command -v "$tool" >/dev/null || die "needs $tool."
  done
  if ((force == 0)) && token_still_valid; then
    echo "You already have a Booley demo token in $TOKEN_FILE (it has not expired)."
    echo "Run 'claim.sh --force' to replace it."
    return 0
  fi
  print_notice
  printf 'Type yes to agree and continue: '
  IFS= read -r answer || true
  [[ $answer == yes ]] || die "nothing claimed: you did not type yes."
  start_device_flow
  github_token="$(poll_for_token)"
  claimed="$(claim_gateway_token "$github_token")"
  unset github_token
  save_token "${claimed% *}" "${claimed#* }"
  echo "Done. Your Booley demo token is saved in $TOKEN_FILE."
}

main "$@"
