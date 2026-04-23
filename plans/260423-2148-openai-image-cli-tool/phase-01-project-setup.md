---
phase: 1
title: Project Setup & Scaffolding
status: done
priority: high
effort: S
---

# Phase 1: Project Setup & Scaffolding

## Overview

Tạo file config & folder structure. Chưa code logic.

## Files to Create

| File | Content |
|---|---|
| `requirements.txt` | `openai>=1.0.0` |
| `.env.example` | `OPENAI_API_KEY=sk-your-key-here` |
| `.gitignore` | `.env`, `output/`, `__pycache__/`, `*.pyc`, `.venv/`, `prompts/*.local.txt` |
| `prompts/.gitkeep` | empty (giữ folder) |
| `output/.gitkeep` | empty (giữ folder) |

## Implementation Steps

1. Tạo `requirements.txt` với `openai>=1.0.0`
2. Tạo `.env.example` với placeholder API key
3. Tạo `.gitignore` exclude: secrets, output, cache
4. Tạo folder `prompts/` và `output/` với `.gitkeep`

## Todo

- [x] `requirements.txt` tạo xong
- [x] `.env.example` tạo xong
- [x] `.gitignore` cover hết: `.env`, `output/`, `__pycache__/`, `.venv/`
- [x] Folder `prompts/` + `.gitkeep`
- [x] Folder `output/` + `.gitkeep`

## Success Criteria

- `pip install -r requirements.txt` chạy OK trong venv
- `git status` không leak `.env` hay ảnh trong `output/`

## Next

→ Phase 2: Core implementation
