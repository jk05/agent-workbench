---
name: docker-expert
description: Use when investigating Dockerfile or container build/runtime failures, including native Node.js addons, node-gyp, ERR_DLOPEN_FAILED, missing native modules, or architecture/libc mismatches.
---

# Docker Expert

Use alongside systematic debugging, not as a replacement for it.
Consult relevant sections of [upstream guidance](references/upstream.md).
Workspace policy and approvals govern every command; examples grant no
permission to build, run, publish images, or change Docker configuration.

## Native-addon failures

Before rebuilding or changing images:

1. Capture the full error, failing application operation, and deployed
   revision. Distinguish an installation failure from a runtime failure.
2. Trace the package path resolved by the application in its final output.
   Check its wrapper, manifest and native binary, not just the build-stage
   dependency. Inspect install-script policy, pruning and stage COPY steps
   when files are absent.
3. If the binary exists but cannot load, compare build and runtime image
   digests, CPU architecture, Node version/module ABI, libc and required
   shared libraries. Inspect binary headers and dependencies with available
   tools. MODULE_NOT_FOUND and ERR_DLOPEN_FAILED are not interchangeable
   diagnoses; neither establishes a cause without the complete error.
4. Choose the smallest probe that separates the remaining hypotheses.
   When execution is authorized, load through the application's resolved
   package and perform a minimal operation in the target runtime.
5. Separate emulator failures from application failures. Report which
   platform and build stages a test actually covers; use a native target
   runner when emulation cannot establish the result.
6. Make the smallest evidenced correction. Preparing a compatible locked
   dependency or fixing an omitted copy may preserve existing images;
   installing compatibility libraries or switching images is not the default.

Report the hypothesis, supporting evidence, discriminating test and result,
and any unresolved compatibility gap.
