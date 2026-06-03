# SEO Blog Cron

Generate 2-4 Vietnamese SEO blog posts per day into `frontend/content/blog`.

## Manual dry run

```bash
cd /path/to/cv-fit-app/backend
../.venv/bin/python3 scripts/generate_seo_blog_posts.py --dry-run --count 1
```

## Manual publish run

```bash
cd /path/to/cv-fit-app/backend
../.venv/bin/python3 scripts/generate_seo_blog_posts.py --min 2 --max 4
```

## Manual publish + redeploy run

Use this when production redeploys from GitHub. It generates posts, commits only
the generated MDX files, and pushes the current branch.

```bash
cd /path/to/cv-fit-app/backend
../.venv/bin/python3 scripts/publish_seo_blog_posts.py --min 2 --max 4
```

The publish wrapper stores retry state in `backend/logs/seo-blog-publish-state.json`.
That directory is gitignored, so OpenClaw retries should skip after a successful
publish instead of creating duplicate posts.

The script uses the backend LLM provider waterfall from `app.core.config`, so the server needs one of these configured:

- `QWEN_ENDPOINT` and `QWEN_API_KEY` for the local Qwen endpoint
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`

## Cron example

Run every day at 08:10 Asia/Ho_Chi_Minh server time:

```cron
10 8 * * * cd /path/to/cv-fit-app/backend && /path/to/cv-fit-app/.venv/bin/python3 scripts/generate_seo_blog_posts.py --min 2 --max 4 >> logs/seo-blog-cron.log 2>&1
```

If production is deployed from git, add the deploy step used by your server after generation, for example:

```cron
10 8 * * * cd /path/to/cv-fit-app/backend && /path/to/cv-fit-app/.venv/bin/python3 scripts/publish_seo_blog_posts.py --min 2 --max 4 >> logs/seo-blog-cron.log 2>&1
```

If production is deployed by Vercel from the repository, the `git push` is what triggers the rebuild. If production is deployed directly on the server, replace the git commands with the project’s normal frontend build/restart command.

## OpenClaw scheduler

If OpenClaw Gateway is running locally, use OpenClaw as the scheduler instead of system cron:

```bash
openclaw cron add \
  --name "daucv-daily-seo-blog" \
  --description "Generate 2-4 Vietnamese SEO MDX blog posts for daucv.com/blog" \
  --cron "10 8 * * *" \
  --tz "Asia/Ho_Chi_Minh" \
  --session isolated \
  --timeout-seconds 7200 \
  --no-deliver \
  --message "Run the daily DauCV SEO blog publish job. Work in /Users/rzy/Desktop/ProjectWithTien/cv-helper/cv-fit-app/backend. Execute exactly: ../.venv/bin/python3 scripts/publish_seo_blog_posts.py --min 2 --max 4. This should generate 2-4 MDX posts, commit only those generated blog files, and push the current branch to GitHub for redeploy. Report the generated slugs, commit hash, push result, and any errors. Do not modify unrelated files."
```

Useful checks:

```bash
openclaw cron list
openclaw cron status
openclaw cron run daucv-daily-seo-blog
openclaw cron runs --id daucv-daily-seo-blog --limit 10
```

If `openclaw cron status` returns a Gateway connection error, start the Gateway first:

```bash
openclaw gateway start
```

OpenClaw runs an agent turn on the schedule, so the job can inspect failures and summarize output. The Python script is still the source of truth for article generation; OpenClaw only schedules and supervises it.
