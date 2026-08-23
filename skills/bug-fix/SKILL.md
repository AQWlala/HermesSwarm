---
name: bug-fix
description: Analyze and fix reported bugs with root cause localization.
version: 1.0.0
author: HermesSwarm
license: Apache-2.0
platforms: [macos, linux, win32]
tags: [bug, fix, debug, root-cause]
category: development
metadata:
  hermes:
    tags: [bug, fix, debug, root-cause]
    category: development
    related_skills: [code-review]
---

# Bug Fix Skill

Analyze a reported bug, localize the root cause, and generate a minimal patch.

## When to Use

Use this skill when the user reports a bug or asks to fix an issue.

## How to Run

1. Parse the issue description to extract symptoms and expected behavior.
2. Reproduce the bug with a minimal test case.
3. Localize the root cause using static and dynamic analysis.
4. Generate a minimal patch that fixes the root cause.
5. Verify the fix with the reproduction test.

## Quick Reference

- Input: bug description + codebase path
- Output: patch + verification result
- Tools: `read_file`, `search_files`, `terminal`