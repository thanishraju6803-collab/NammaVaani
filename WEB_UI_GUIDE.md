# NammaVaani redesigned web UI

The new web UI is based on the user's BoloNote reference: warm cream canvas, a friendly gradient welcome card, a language selector, a large glowing central microphone, "Farmers are asking" examples, recent conversations and bottom navigation.

## Start

```powershell
uvicorn web_app:app --reload
```

Then open http://127.0.0.1:8000.

## Main screen behaviour

- Tap the mic once to start recording; tap again to stop and submit.
- The browser records WAV audio and posts it to `/api/voice`.
- Prisma v2.5 transcribes the audio using the selected language.
- NammaVaani routes the transcript to weather, mandi prices, crop information, repair ticket or letter drafting.
- Timbre v2.5 speaks the reply when the Gnani key is available.
- The user can inspect the transcript and answer, copy the answer, or download a generated letter.
- "Type instead" is a test fallback, clearly marked as not Prisma transcription.

## Other screens

- **My Farm:** simple local farmer profile editor.
- **Activity:** recent conversation list and repair-ticket list.
- **Settings:** language preference, Agmarknet CSV upload and Gnani key status.

## API endpoints

- `GET /api/health`
- `GET /api/profile`
- `POST /api/profile`
- `POST /api/voice` (multipart WAV, selected language, session ID)
- `POST /api/text` (typed test)
- `GET /api/history?session_id=...`
- `POST /api/mandi-upload`
- `GET /api/tickets`
- `POST /api/reset`

The browser microphone requires permission and localhost/HTTPS. The server stores conversation state in memory for this local prototype and stores the farmer profile/tickets in SQLite. A production deployment must use authenticated users and persistent per-user conversation storage.
