# Booley in GitHub Codespaces

This Codespace is a complete Booley setup for [PicoRV32](https://github.com/YosysHQ/picorv32),
a small open-source RISC-V CPU. Simulation, synthesis and waveform tools are
already installed. All you bring is a Claude or Codex account.

The folder open on the left is the PicoRV32 source. Its `.booley` folder is
your copy of the Booley demo configuration.

## 1. Connect an agent

Booley picks the agent from the credentials it finds when the Codespace
starts:

1. A Claude credential (`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`)
   selects Claude Code.
2. Otherwise, an `OPENAI_API_KEY` selects Codex.
3. With neither, Booley uses Claude Code, and you sign in once (below).

**No secret set?** Sign in to Claude Code from a terminal (`` Ctrl+` ``):

```bash
claude auth login
```

Open the link it prints after "If the browser didn't open, visit:", sign in,
then copy the code the page shows and paste it at the
`Paste code here if prompted >` prompt. A tab may also open by itself and fail
to load a `localhost` address; close it, because the printed link is the one
that works in a browser Codespace.

**Want to use an API key, or Codex?** Add `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` as a [Codespaces secret](https://github.com/settings/codespaces)
for this repository, then rebuild the Codespace: press `F1` and run
**Codespaces: Rebuild Container**. Your PicoRV32 edits are kept. Codex needs
the `OPENAI_API_KEY` secret; this demo doesn't support a Codex terminal
sign-in.

## 2. Check the setup

In the terminal:

```bash
booley doctor
```

No check should fail. Until you connect an agent, Doctor warns that it has no
credential. A few Codespaces-specific warnings are waived on purpose;
`.booley/doctor-waivers.toml` says why.

## 3. Ask the agent to run things

Start a chat with `booley` and try these, one at a time:

> Check the project status and explain the available Targets.

> Run the sim_core simulation and tell me whether it passed.

> Open the sim_core waveform and show me the first few instruction fetches
> on the memory interface.

> Synthesize synth_core and report its area and maximum clock frequency.

The agent runs Booley Flows for each request, so the answers come from real
tool runs rather than guesses. Waveforms open in the VaporView viewer, and the
Booley Dashboard tab shows runs as they happen.

## 4. Optional: let an agent carry a change

Goal Mode hands an agent a change with Goals that only real Flow results can
meet, such as "add this feature and keep every test passing". Try it with:

```bash
booley worktree new my-change
```

Then ask the agent:

> Use the booley-goal skill in the my-change worktree to add a small, opt-in
> PicoRV32 feature and verify its disabled behavior.

See the [demo README](README.md#then-try-goal-mode) for how Goal Mode works.

## Good to know

- This Codespace runs on your own Codespaces quota and your own agent
  account. Stop it from [github.com/codespaces](https://github.com/codespaces)
  when you're done.
- Your PicoRV32 edits live in `/workspaces/picorv32` and survive a rebuild.
- To run Booley on your own machine instead, see the
  [demo README](README.md#quick-start).
