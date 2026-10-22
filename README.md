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
