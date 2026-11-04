# Booley in GitHub Codespaces

This Codespace is a complete Booley setup for [PicoRV32](https://github.com/YosysHQ/picorv32),
a small open-source RISC-V CPU. Simulation, synthesis and waveform tools are
already installed, and the agent can run free on a demo token (step 1). You
only need a GitHub account.

The Codespace itself runs on your GitHub account's free Codespaces quota:
about 30 hours a month of this 4-core Codespace. See
[GitHub's Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces).

The folder open on the left is the PicoRV32 source. Its `.booley` folder is
your copy of the Booley demo configuration.

## Trust the folder first

When the Codespace opens, VS Code asks **Do you trust the authors of the files
in this folder?** Choose **Trust Folder & Continue**. Until you do, VS Code
runs in Restricted Mode: you can read this page, but no terminal or Booley
Dashboard starts.

If you chose **Cancel**, click **Restricted Mode** at the left end of the
status bar (or **Manage** in the banner at the top), then click **Trust**.

## 1. Choose how the agent runs

Pick one:

- **Free demo token.** No account to bring: the agent runs OpenAI's GPT-6
  Luna on the Booley maintainer's account. Each GitHub account gets $1 of demo
  usage per month. GPT-6 Luna is cheap, so that's about 1.5 hours of the agent
  working nonstop, or about three runs of the Zbb Goal (about $0.35 each).
  Normal back-and-forth use lasts longer. Luna is a small model: capable
  enough for this demo, but not as strong as Claude or the larger GPT models.
- **Your own Claude or ChatGPT account.** A stronger model, within your own
  plan's limits instead of the demo allowance.

If you set up both, Booley uses your own account. Both start in a terminal:
press **Ctrl+Shift+`** (the backtick key, left of **1**), or use the menu
(☰) → **Terminal** → **New Terminal**.

### Option A: Free demo token

In a terminal, run:

```bash
booley-demo-claim
```

Type `yes` to accept the notice. It then prints a GitHub link and a code
like `ABCD-1234`: open the link, enter the code, and click **Authorize**.
The terminal waits until you do, then prints **Done**. Your GitHub
account must be at least 30 days old. If it fails or the code expires, run it
again.

A token lasts 30 days, and one GitHub account can hold 3 at a time.

### Option B: Your own Claude or ChatGPT account

Sign in with one of the two.

**Claude Code.** In a terminal, run:

```bash
BROWSER=none claude auth login
```

Open the link it prints, sign in, and copy the code the page it lands on
shows. Paste the whole code at the `Paste code here if prompted >` prompt and
press Enter. Use each link once: if sign-in fails, run the command again for a
fresh link. (`BROWSER=none` stops Claude Code from also opening a tab that
returns to a `localhost` address, which a browser Codespace can't reach.)

**Codex.** In a terminal, run:

```bash
codex login --device-auth
```

Open the link it prints, sign in with your ChatGPT account, and enter the
one-time code it shows.

Then switch Booley to your account (if both are signed in, it picks Claude
Code):

```bash
python -m booley.harness.incontainer_register
```

Either sign-in lasts until the Codespace's container is rebuilt; stopping and
restarting the Codespace keeps it.

## 2. Check the setup

In the terminal:

```bash
booley doctor
```

No check should fail. Until you have a demo token or have signed in, Doctor
warns that the agent credential is missing; the warning goes away once you
do.

## 3. Try the demo

Now follow [Try the demo](README.md#try-the-demo) in the README: run Flows
one at a time, hand the agent the prepared Zbb Goal, then build whatever you
want.

Long runs can use up the demo allowance quickly;
[sign in with your own account](#option-b-your-own-claude-or-chatgpt-account)
for more room.

## Good to know

- A running Codespace uses your quota (see the top of this page). Stop it from
  [github.com/codespaces](https://github.com/codespaces) when you're done. A
  stopped Codespace still uses storage; delete it when you no longer need it.
- The demo token's allowance resets each month. Rebuilding the container
  deletes the token; run `booley-demo-claim` to get a new one.
- Your PicoRV32 edits live in `/workspaces/picorv32` and survive a rebuild.
- To run Booley on your own machine instead, see the
  [demo README](README.md#quick-start-local-install).
