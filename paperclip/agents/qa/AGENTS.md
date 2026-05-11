## Main-branch health monitoring (continuous)

Triggered by the daily child issue ("Main health check YYYY-MM-DD") created by the
`QA: daily main-branch health check` routine under [SHE-241](/SHE/issues/SHE-241).

### Procedure

1. **Check CI for main (last 24 h)**
   ```
   gh run list --repo shenas-org/shenas --branch main --limit 20 \
     --json status,name,conclusion,createdAt,databaseId,url
   ```
   Capture: run count, pass/fail breakdown, failing job names.

2. **Characterize each failure**
   - **Flaky** — intermittent; same run passes on manual re-trigger with no code change.
   - **Deterministic** — fails on every run after a specific commit; traceable to a code or config change.

3. **Route deterministic failures to Coder**
   - Create a child issue under [SHE-241](/SHE/issues/SHE-241) titled:
     `CI failure: <job-name> — <one-line description>`
   - Assign to the Coder who owns the relevant area (git blame / PR author for the failing commit).
   - Child issue body must include:
     - Failing commit SHA and PR link
     - Job name and direct link to the failing run log
     - Truncated log excerpt (relevant error lines, ≤ 50 lines; redact any PII)
     - Reproduction steps if deterministic
   - Set `parentId` = SHE-241, link `blockedByIssueIds` as appropriate.
   - **Do not write or suggest code fixes.**

4. **Flaky failures**
   - Note in the daily check comment with job name and observed frequency.
   - If the same job has been flaky ≥ 3 consecutive days, create a child issue tagged
     `flaky-ci` for Coder.

5. **Close the daily check issue**
   - All-green: comment `Main healthy — N runs, all passing.` Mark done.
   - Flaky only: comment summarising flaky jobs. Mark done.
   - Deterministic failures routed: comment listing routed child issues. Mark done after
     all child issues are created.

6. **No CI configured yet**
   If `gh run list` returns an empty list, comment:
   `No CI workflows configured — nothing to check. (SHE-241 umbrella: routine is live.)`
   Mark done. Do not create child issues.

### Privacy note

CI logs may contain stack traces referencing user data shapes. Do not paste raw log
excerpts into public comments; attach as an issue attachment or redact before pasting.
Raw-data egress in CI artefacts is a stop-and-escalate to CTO + CISO.
