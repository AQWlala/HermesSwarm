---
name: code-review
description: Review code for bugs, style, and security issues.
version: 1.0.0
author: HermesSwarm
license: Apache-2.0
platforms: [macos, linux, win32]
tags: [code, review, quality, security]
category: development
metadata:
  hermes:
    tags: [code, review, quality, security]
    category: development
    related_skills: [bug-fix, doc-writing]
---

# Code Review Skill

Review source code for bugs, style violations, and security issues.

## When to Use

Use this skill when the user asks to review code, check quality, or audit a file for issues.

## How to Run

1. Read the target file with `read_file`.
2. Check for common bug patterns (null dereference, resource leak, race condition).
3. Check style against project conventions.
4. Check for security issues (SQL injection, XSS, hardcoded secrets).
5. Report findings with severity and location.

## Quick Reference

- Input: file path or code snippet
- Output: list of findings with severity (critical/warning/info)
- Tools: `read_file`, `search_files`