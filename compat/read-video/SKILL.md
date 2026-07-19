---
name: read-video
description: >-
  Legacy compatibility entry point for Voidscape. Use it when an existing automation or user invokes
  /read-video; new conversations should use /voidscape for the guided inspect, preview, read,
  customize, and doctor workflow.
---

# read-video compatibility

This compatibility skill keeps existing `/read-video` automations working. Its engine forwards to
the canonical Voidscape installation while preserving a legacy `workspace.json` when one exists.

For new work, prefer `/voidscape <file-or-url>` or ask an agent to inspect, preview, and read the
media. The underlying `video.py` command contract remains available for scripts and agents that
need JSON, envelopes, or explicit flags.
