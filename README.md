# rir
Random Internet Readings digested and sent to inbox

## Usage
Reads the RIR Notion database, picks 3-5 random articles and emails links to them,
encouraging re-reading, commentary and tag review.

```bash
cp .env.example .env   # fill in values
docker build -t rir .
docker run --rm --env-file .env rir          # set RIR_DRY_RUN=1 to print instead of send
```

Weekly crontab (Mondays 08:00):
```
0 8 * * 1 docker run --rm --env-file /path/to/.env rir
```

Tests: `pip install pytest && pytest`

## Configuration
Secrets live in a local `.env` file (git-ignored), read automatically from the working
directory (override with `RIR_ENV_FILE`). Real environment variables take precedence.
When running in Docker, mount it: `docker run --rm -v $PWD/.env:/app/.env rir`
(or keep using `--env-file .env`).

For SMTP, a dev mailbox is enough: e.g. a Gmail account with an
[app password](https://myaccount.google.com/apppasswords) (`SMTP_HOST=smtp.gmail.com`,
`SMTP_PORT=587`), or a local catcher like MailHog/Mailpit. Use `RIR_DRY_RUN=1` to test
the Notion side without sending anything.
