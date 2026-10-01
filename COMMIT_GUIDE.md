# Publishing compact2binary v0.3.0 with a real commit history

This ships four new feature commits on top of your existing v0.2.0 history —
each a real, self-contained change that builds and passes its tests. Unlike the
v0.2.0 push, **this is a normal push, not a force-push**: your repo is already
at the correct root-level structure, so we're just adding commits on top.

> **On honesty:** the new commits will be dated *now*. That's fine — an early
> project moving 0.1 → 0.2 → 0.3 over a short span is completely normal. Don't
> backdate to fake a longer timeline.

You need `survey-compact-to-binary-v0.3.0.zip` (this zip). Cloning fresh is the
cleanest route because it guarantees you're building on exactly what's on
GitHub.

---

## Step 1 — clone your repo fresh

In a Git Bash terminal in VSCode (Terminal -> New Terminal -> dropdown ->
Git Bash), in a folder where you want the project:

```bash
git clone https://github.com/esiihle/survey-compact-to-binary.git
cd survey-compact-to-binary
```

Then open this folder in VSCode (File -> Open Folder).

Confirm the v0.2.0 history is there:

```bash
git log --oneline      # should show 7 commits, ending at "docs: release v0.2.0"
```

If your name/email aren't set globally, set them so the new commits attribute
to you:

```bash
git config user.name  "Sicelwesihle Myeza"
git config user.email "your-github-email@example.com"
```

## Step 2 — overlay the v0.3.0 files

Extract `survey-compact-to-binary-v0.3.0.zip`, drill into its inner folder (the
one that directly contains `src/`), select everything (Ctrl+A), copy (Ctrl+C),
and paste into your cloned folder, choosing **"Replace the files in the
destination."** This overwrites the changed files and adds the new ones
(`nets.py`, `decode.py`, tests, `build_history_v3.sh`, this guide).

## Step 3 — build the four feature commits

```bash
bash build_history_v3.sh
```

You should see four commits created and an 11-line history printed.

## Step 4 — push (normal, no force)

```bash
git push
```

## Step 5 — clean up

```bash
rm build_history_v3.sh COMMIT_GUIDE.md
```

Refresh GitHub — 11 commits, ending at "docs: release v0.3.0".

---

## If you'd rather use your existing local clone

Skip Step 1's clone. In your existing repo folder, first make sure it's current
and clean:

```bash
git pull
git status      # should be clean before you start
```

Then do Steps 2-5 as above.

## What the new history looks like

```
docs: release v0.3.0
feat: decode — inverse binary to compact transform
feat: Excel (.xlsx) table I/O
feat: net/combination variables
docs: release v0.2.0
... (the six v0.2.0 commits) ...
feat: initial release v0.1.0
```

Each new feature commit ships its own tests, so the suite grows
29 -> 35 -> 37 -> 40. CI runs on every push.

## Quick checklist

- [ ] Commit email is verified on your `esiihle` account (for contribution credit).
- [ ] `LICENSE` has your full legal name (only matters if you haven't already fixed it).
- [ ] Manager sign-off still covers this (generalised, synthetic-data only) — unchanged.
