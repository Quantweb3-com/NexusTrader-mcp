# Changelog

## v0.1.2 - 2026-04-15

This release finalizes the documentation and release packaging for Read the Docs and public distribution.

- Bumped package version from `0.1.1` to `0.1.2`.
- Added root-level `.readthedocs.yaml` so Read the Docs can detect the project configuration.
- Added a minimal `docs/` publishing stack with `conf.py`, `requirements.txt`, and index navigation.
- Reworked `README.md` into a commercial-facing project page with clearer product positioning.
- Corrected the setup documentation so `.keys/.secrets.toml` is documented as living in the current project directory.
- Clarified that `NexusTrader` is an ecosystem-related project, not a required local dependency for running this repository.
- Expanded OpenClaw troubleshooting and deployment guidance for end users and support teams.

## v0.1.1 - 2026-04-15

This was the first documentation-focused release for external sharing and deployment guidance.

- Introduced deployment and test documentation.
- Consolidated trading, OpenClaw, Codex, and SSE integration guidance.
- Packaged the `0.1.1` release baseline for external usage.
