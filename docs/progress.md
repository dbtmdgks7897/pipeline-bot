# Progress

## Where things stand (2026-10-10)
Dormant, but further along than this file previously claimed. The bot is a
Telegram remote control for the local Claude Code pipeline: topic (thread_id)
→ project mapping, `/send` writes md into `<project>/mymd/todo/`, `/run`
executes one Claude Code CLI command, `/pipeline` chains the configured steps
with auto/required/batch trust levels, `/status` reports state. FastAPI
webhook mode behind a Cloudflare Tunnel (`bot.ki-garu.com`), launchd plists
for bot + tunnel.

Verified on 2026-10-10 (venv Python 3.14.3):
- `pytest tests/` → **89 passed** (this file said 78; the number was stale —
  86 at commit `9175e8a`, plus 3 `start_from` tests in the uncommitted diff).
- `mypy src/` → clean. `ruff check src/` → clean; `ruff check tests/` → 12
  F401 unused imports, all auto-fixable.
- Not running today: no `com.pipeline-bot` / `com.cloudflared-tunnel` in
  `~/Library/LaunchAgents`, nothing in `launchctl list`, no process alive.
  It *was* running in production under launchd: `logs/pipeline-bot.log.*`
  covers 2026-09-07 → 2026-09-22 with the 08:00 APScheduler job firing
  (succeeded 09-11 and 09-22, "missed by …" warnings after sleep/wake).
  Those logs contain no Telegram traffic, so the service was up but idle in
  that window; older logs were dropped by `backupCount=7`.

Last commit 2026-09-25 (`8278332`, merge of `docs/dev-command-post`) — docs
only. Last feature commit is 2026-03-13 (`9175e8a`, batch scheduler). No
note anywhere explains why work stopped.

Known half-finished (code read, not just assumed):
- **Batch morning alert never reaches Telegram.** `run.py::_flush_callback`
  flushes the queue and logs the summary; there is no send. Also moot in
  practice because `config.yaml` has `trust_levels.batch: []` and every batch
  step was switched to `auto`.
- **`/run` buttons are decorative.** approve/reject only reply with text;
  `feedback` prompts for input but no handler captures the next message.
  `pending_runs` entries are never consumed (slow leak).
- **No rollback on reject**, which spec.md Feature 3 requires;
  `pipeline_reject` just drops the session.
- `active_sessions` is in-process memory — a restart loses any pipeline
  paused at a `required` step.
- Only one topic is configured (`kigaru`); the multi-project story
  (imysh, atsumaro) is config-only.

In flight, uncommitted since March 2026 (7 files, +200/-194): `CLAUDE.md`
and `prompt_plan.md` condensed, `claude_runner.run_claude` timeout
300s → `None` plus `--dangerously-skip-permissions`, per-step `timeout` in
`config.yaml`/`PipelineStep`, `required` steps changed to execute-then-ask,
`/pipeline <step> <args>` (`start_from`), httpx transport retries(3) +
`keepalive_expiry=20s`, `_safe_answer()` for expired callback queries,
NetworkError/BadRequest downgraded to warnings. This work is coherent and
tested (89 pass) — it should be committed, not discarded.

## Next
- [ ] Review and commit the 7-file in-flight diff (tests pass, mypy clean);
      decide separately on `.coverage` (should be gitignored) and
      `prompt_plan.archived.md` (keep).
- [ ] Wire the 08:00 batch flush to actually send the summary to Telegram,
      or delete the batch trust level and say so in spec.md.
- [ ] Finish or remove the `/run` approve/reject/feedback buttons.
- [ ] Re-register the launchd agents (symlink `launchd/*.plist` into
      `~/Library/LaunchAgents`, `launchctl load`) if the bot is to run again.
- [ ] Remaining from prompt_plan.md: `/pipeline` Bot E2E and full E2E
      (the one success criterion never ticked: a full cycle
      plan-sync → plan → tdd → commit without sitting at the laptop).

## Log
- 2026-10-10: Full repo scan for a SecondBrain vault record (purpose, state, results, stack, decisions); ran tests/mypy/ruff and checked launchd + logs; corrected this file (78 → 89 tests, "dormant since 2026-03-13" → ran in production under launchd through 2026-09-22) and listed the half-finished features found by reading the code.

| Date | Stage | Status | Summary |
|------|-------|--------|---------|
| 2026-03-13 01:45 | /plan Phase 1 | completed | 5개 태스크 계획, 리스크 1개 식별 |
| 2026-03-13 01:50 | Phase 1 구현 | completed | 6개 파일 생성, 테스트 13개 통과 |
| 2026-03-13 | Phase 2 /tdd | completed | claude_runner+result_parser+bot /run+webhook, 테스트 36/36 통과 |
| 2026-03-13 | /code-review | completed | 이슈 2M/3L, CRITICAL/HIGH 없음, FastAPI lifespan 수정 완료 |
| 2026-03-13 | /handoff-verify | completed | 린트 PASS, mypy PASS, 테스트 36/36 PASS, 커버리지 61% (핵심 모듈 100%) |
| 2026-03-13 09:45 | Phase 3 /tdd | completed | pipeline.py+batch_review.py+bot.py /pipeline, 테스트 58/58 통과, 커버리지 미측정 |
| 2026-03-13 09:50 | /code-review | completed | 5개 이슈 (0C/1H/2M/2L), batch_queue 유실 버그 수정, send_fn 중복 제거, 테스트 60/60 통과 |
| 2026-03-13 09:52 | /handoff-verify | completed | 린트 PASS, mypy PASS, 테스트 60/60 PASS |
| 2026-03-13 09:51 | /commit-push-pr | completed | 커밋 da31eaf, main 직접 push, 보안 PASS |
| 2026-03-13 10:03 | Phase 4 /tdd | completed | error_handler+task_queue+logger+/status+launchd, 테스트 78/78 통과, 커버리지 미측정 |
| 2026-03-13 10:06 | /code-review | completed | 이슈 없음 (0C/0H/1M/1L), 리뷰 통과 |
| 2026-03-13 10:07 | /commit-push-pr | completed | 커밋 c6c39c1, main 직접 push, 보안 PASS |
| 2026-03-13 10:20 | /tdd 배치 스케줄러 | completed | batch_scheduler.py+bot.py+run.py 통합, 테스트 86/86 통과, 커버리지 미측정 |
| 2026-03-13 10:20 | /code-review | completed | 이슈 없음 (0C/0H/1M/1L), 리뷰 통과 |
| 2026-03-13 10:21 | /handoff-verify | completed | 린트 PASS, mypy PASS, 테스트 86/86 PASS |
| 2026-03-13 10:22 | /commit-push-pr | completed | 커밋 9175e8a, main 직접 push, 보안 PASS |
