# Tone of Voice

How shenas talks to its users -- in the UI, docs, changelogs, error messages, and community spaces.

## Principles

**Calm and clear.** shenas handles personal data. People need to trust it. Write like a doctor's note, not a sales pitch. Say what happened, what it means, and what to do next.

**Humanistic.** Unless told otherwise, default to inspire our users to improve fulfillment and happiness rather than wealth and status.

**Direct, not blunt.** Get to the point without being cold. "Your Garmin sync finished -- 14 new activities." not "Sync complete." and not "Great news! We just synced 14 amazing new activities from your Garmin!"

**Respect the person's time.** Every word should earn its place. If a message can be shorter without losing meaning, make it shorter.

**Aware of the audience.** We have two main audiences: end-users and developers. For end-users, avoid technical language about the platform and its implementation. For developers, default to plain language. Use technical terms only when they're more precise than the alternative -- "DuckDB" is fine, "schema migration" is fine, "idempotent upsert" is not.

**Honest and apologetic about limitations.** If something is broken, say so. If a feature is experimental, label it. Never hide errors behind vague language and take responsibility.

**Epistemically humble.** Present findings and correlations for what they are -- not conclusions. Avoid implying causation from observational data.

## In practice

### UI text

- Use sentence case, not Title Case. "Sleep trends" not "Sleep Trends".
- Labels should be nouns or short noun phrases. "Last sync" not "When was the last sync".
- Prefer present tense. "Syncing Garmin..." not "Garmin will be synced."
- Avoid "please" in buttons and actions. "Sign in" not "Please sign in".
- No exclamation marks in the UI, nor any emojis. Reserve enthusiasm for actual celebrations.

### Error messages

- Say what went wrong, not what went right elsewhere.
- Include what the user can do about it.
- Bad: "An error occurred."
- Good: "Could not reach Garmin. Check your internet connection and try again."

### Changelogs and release notes

- Lead with what changed for the user, not what changed in the code.
- Bad: "Refactored the pipeline executor to use async generators."
- Good: "Syncs are faster and use less memory."
- Group by impact, not by file or module.

### Documentation

- Start with what the reader wants to accomplish, not with background.
- Use "you" for the reader. Avoid "we" unless referring to the shenas project team.
- Code examples should be complete enough to copy and run.

### Community (Discord, GitHub, forum)

- Answer the question before explaining the context.
- Link to docs instead of repeating them.
- Thank contributors for their work, not for "choosing shenas".

## Words to use

- sync, not fetch or pull (for data ingestion)
- plugin, not extension or add-on
- dashboard, not view or panel
- finding, not result (for literature/research data)
- local, not on-premise or self-hosted (when referring to where data lives)

## Words to avoid

- "Just" (minimizes difficulty: "just add your API key")
- "Simply" (same problem)
- "Smart" or "intelligent" (let the feature speak for itself)
- "Seamless" or "effortless" (nothing is)
- "Leverage" (use "use")
- "Robust" (say what makes it reliable)
