---
name: webp
description: "Use demoon84/webp-maker to convert image files to WebP or build animated WebP assets from folders of frames."
---

# Webp

Use this skill when the job should run through [demoon84/webp-maker](https://github.com/demoon84/webp-maker), a Node CLI for converting source images into `.webp` files and building animated `.webp` assets from frame folders.

## When to use

- Trigger this skill when the user asks to convert `png`, `jpg`, or `jpeg` files into `.webp`, generate animated `.webp` files from frame folders, or run the `webp-maker` pipeline.
- Use it when the user mentions `webp-maker`, `cwebp`, `awebp`, `pipeline`, batch WebP conversion, or animated WebP creation.

## Workflow

1. Prefer the bundled wrapper `scripts/webp_maker.py`.
2. On first run, let the wrapper clone `https://github.com/demoon84/webp-maker.git` into its cache and install dependencies.
3. Use `cwebp` for directory or single-file conversion into `.webp`.
4. Use `awebp` when the input is already a folder of `.webp` frames and the user wants one animated `.webp`.
5. Use `pipeline` when the user wants both steps in one run: convert source frames first, then build the animated `.webp`.
6. Prefer `--json` when the result will be consumed or summarized by another tool or by the assistant.
7. After running the command, verify the output path exists and report the generated file locations.

## Commands

Bootstrap or refresh the cached repo:

```bash
python3 scripts/webp_maker.py bootstrap --update
```

Convert images to `.webp`:

```bash
python3 scripts/webp_maker.py cwebp --from ./origin --to ./webp --quality 90 --concurrency 4 --json
```

Build an animated `.webp` from a directory of `.webp` frames:

```bash
python3 scripts/webp_maker.py awebp --from ./webp --to ./awebp/ani.webp --fps 10 --repeat 0 --json
```

Run the full pipeline:

```bash
python3 scripts/webp_maker.py pipeline --from ./origin --webp-dir ./webp --to ./awebp/ani.webp --quality 90 --concurrency 4 --fps 10 --json
```

Use an existing local clone instead of the cache:

```bash
python3 scripts/webp_maker.py cwebp --repo-dir /path/to/webp-maker --from ./origin --to ./webp
```

## Wrapper behavior

- `bootstrap` ensures the GitHub repo exists locally and that `npm ci` has been run.
- `cwebp`, `awebp`, and `pipeline` forward their flags directly to `webp-maker`.
- Use `--update` when you want the wrapper to refresh the git checkout and reinstall dependencies before running.
- Use `--repo-dir` when the user already has a local checkout and wants that exact copy used.

## Practical defaults

- Start photo conversion around `--quality 80-90`.
- Use `--concurrency 4` or let the CLI choose automatically when the machine is busy.
- Use `--repeat 0` for looping animated WebP unless the user requests a fixed repeat count.
- Use `pipeline` when the source frames are `png` or `jpg` and the final target is one animated `.webp`.

## Notes

- This skill intentionally uses the upstream CLI from `demoon84/webp-maker` instead of a custom Pillow workflow.
- The upstream README documents three main commands: `cwebp`, `awebp`, and `pipeline`.
- The wrapper writes status messages to `stderr`, so JSON output from upstream stays clean on `stdout`.
- If the repo or dependency install fails, report the failing `git` or `npm` step and stop before claiming conversion succeeded.
