# Gnani API verification

## What a successful test means

- **Prisma v2.5:** A successful `POST /api/voice` returns `gnani_stt: true`, HTTP status 200, a `gnani_stt_request_id`, model and transcript.
- **Timbre v2.5:** The Settings > Test Timbre action returns `gnani_tts: true`, HTTP 200 and a non-zero audio byte count.
- Browser speech synthesis is only a fallback. It is not a Gnani API call and does not consume Gnani credits.
- A configured key is not proof that the API accepted it.

## Dashboard/account check

Create the key in the Gnani APIs dashboard (`app.gnani.ai/voice`) while signed into the same account/email used for the competition registration. The competition instructions say API keys and credit usage are managed from that dashboard.

## Command-line test

```powershell
python scripts/test_gnani_api.py --language kn
```

To test Prisma too:

```powershell
python scripts/test_gnani_api.py --language kn --audio "C:\path\to\short-recording.wav"
```

Do not post the `.env` file, API key or screenshots showing the key. The test script only prints whether a key was loaded and safe API response metadata.
