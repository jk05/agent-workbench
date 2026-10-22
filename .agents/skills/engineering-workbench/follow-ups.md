# Follow-up work without expanding scope

Read this when investigation, implementation, or review finds useful work
outside the approved scope.

- State the observation and evidence, its impact, a bounded follow-up, and why
  it is deferred. A blocker for the current acceptance criteria (for example,
  required authorization) is not optional follow-up work: resolve it now.
- Look for an existing ticket before proposing a new one.
- Show the proposed destination and text, and confirm with the user at the
  point of creating a ticket or commenting on the original ticket. Delivery
  approval alone is not consent to publish follow-ups.
- After approval, use the configured tracker: link the follow-up to the
  original ticket and the affected PR, then add the approved comment using the
  link the tracker returned. Check for duplicates before writes or retries.
- Add a code comment only for a relevant non-obvious limitation, with the
  confirmed ticket link. Avoid scattered TODOs.
- In the PR description (or local draft), link the original ticket and any
  created or existing follow-ups. Never invent ticket IDs or imply a pending
  proposal was posted.
- If the user declines, acknowledge once, keep the unposted proposal in the
  report or handoff, and return to the approved work. Do not offer it again
  unless the user reopens it.
- If the tracker is unavailable, keep the proposal and continue approved work.
