/**
 * Fails fast with an actionable message if the dev stack isn't up, instead
 * of letting every test in the suite time out separately waiting on
 * selectors that can never appear. This project has no docker-compose/CI
 * yet (RECOVERY_MANIFEST.md) — the full stack (Postgres + backend +
 * frontend) is started manually; see
 * .claude/skills/run-ali-trading-dashboard/SKILL.md for the exact commands.
 */
async function checkUp(url: string, label: string): Promise<void> {
  try {
    const res = await fetch(url)
    if (!res.ok) {
      throw new Error(`${label} responded ${res.status} ${res.statusText}`)
    }
  } catch (err) {
    throw new Error(
      `${label} is not reachable at ${url} (${(err as Error).message}). ` +
        'Start the full dev stack first — see ' +
        '.claude/skills/run-ali-trading-dashboard/SKILL.md.',
    )
  }
}

export default async function globalSetup(): Promise<void> {
  await checkUp('http://127.0.0.1:8000/health/ready', 'Backend')
  await checkUp('http://localhost:5173/', 'Frontend dev server')
}
