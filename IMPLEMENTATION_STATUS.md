# NammaVaani Farm Companion — implementation status

Updated: 9 November 2026

## Working modules in the code

- Farmer home with one primary voice input, language control, service examples and recent conversations.
- Ten configured Gnani speech locales: Bengali, English (India), Gujarati, Hindi, Kannada, Malayalam, Marathi, Punjabi, Tamil and Telugu.
- Timbre v2.5 preferred voice configuration for all ten locales.
- Built-in full NammaVaani conversation workflows in Kannada, Telugu and English.
- Optional multilingual language bridge for the other seven locales through an OpenAI-compatible chat-completions endpoint. The endpoint must be configured separately; it is not bundled.
- Optional Prisma v3.0 Auto Detect mode (`indic-auto` + `codemix`), only when the user's Gnani account has access. Prisma v2.5 remains the default and requires a selected spoken language.
- Unicode-script transcript fallback, clearly labelled as a script estimate rather than acoustic language detection.
- My Farm profile persisted in SQLite, with state → district → taluk/mandal → hobli/revenue circle → village fields.
- Optional GPS capture is explicitly opt-in in the browser and saved only when the farmer checks consent and presses the location button; saved coordinates can be used for weather lookup.
- Additional Romanised Kannada/Telugu and English-mixed phrase matches for common repair, market, weather, commodity and soil/water expressions; unclear requests receive a short clarification instead of an assumed answer.
- Gnani Prisma v2.5 speech recognition and Timbre v2.5 response audio adapters (require `GNANI_API_KEY`; real API calls require the user's credentials and available account access).
- Conversation intent routing for crops, weather, mandi prices, crop-health information and repairs.
- Crop Planner based on UAS Bengaluru Zone V crop groups and cautious guidance.
- Five-day weather retrieval from Open-Meteo using the entered farm location, or GPS coordinates only when the farmer opted in.
- Agmarknet mandi-price lookup through the official data.gov.in resource API as the primary source when `DATA_GOV_IN_API_KEY` is configured; saved/uploaded CSV is the automatic fallback. Results include source, actual arrival date, freshness and retrieval time.
- Existing farm repair tickets, operator updates and CSV export.
- Localised farmer-friendly service errors for weather and mandi retrieval.

## Multilingual support boundary

- All ten listed locales are configured for Prisma speech input and Timbre v2.5 voice output, subject to account access and successful live API tests.
- Built-in complete task replies are localised in Kannada, Telugu and English.
- Bengali, Gujarati, Hindi, Malayalam, Marathi, Punjabi and Tamil receive a native-language beta notice unless the optional translation endpoint is configured.
- With the optional bridge, the request is translated to English, processed by NammaVaani's existing service workflows/data adapters, then translated back. Numeric-token changes are rejected. This is not a substitute for native-speaker review and does not prove translation perfection.
- Prisma v3.0 auto-detection is optional and account-dependent. Default remains Prisma v2.5. Script fallback is not acoustic language detection.
- Do not claim that every dialect or every three-language combination has equal accuracy.

## Agmarknet API and CSV fallback

- Resource: `9ef84268-d588-465a-a308-a864a43d0070` (Current Daily Price of Various Commodities from Various Markets (Mandi)).
- The API key is loaded from the server-side `.env` file and never returned to the frontend.
- The API is attempted first. A network/API problem or no matching record falls back to the saved/uploaded official CSV.
- The market API path is covered by mocked tests; it has not been live-verified in this environment because no data.gov.in key was supplied.

## Mandi CSV behaviour

- The default saved CSV path is `data/mandi_prices.csv` (configurable with `NAMMAVAANI_MANDI_CSV`).
- The Mandi Prices page accepts an uploaded official Agmarknet CSV or reads the previously saved local file.
- Uploaded files are size-limited and schema-checked before they can replace the saved file.
- The parser supports common Agmarknet headings and date formats. It filters to the selected state, district and commodity.
- Results include arrival date, source file and a freshness label. Old records are not represented as today's prices.
- `data/mandi_prices_template.csv` is header-only and contains no sample market values.

## Deliberately not claimed as complete

- A personalised crop ranking or yield/profit prediction. Crop Planner displays a local Zone V crop basket and directs users to current UAS/KVK practice guidance.
- Direct IMD weather API integration. The current weather adapter uses Open-Meteo and warns that forecasts are not guarantees.
- Guaranteed real-time mandi prices. The official source publishes daily observations; the app displays the reported arrival date. CSV observations are only as current as the last downloaded file.
- Automatic validation of village/taluk/hobli names against the live Local Government Directory (LGD). The current profile captures these hierarchy names as entered by the farmer.
- Full task localisation for all ten languages without an external translation endpoint and local-speaker validation.
- Automatic acoustic language detection under the default Prisma v2.5 mode.
- Crop photograph diagnosis, pesticide recommendations, a crop-stage calendar, offline STT, live technician dispatch or production multi-user authentication.
- Live Gnani API verification in this build environment; real calls need the user's private API key and account access.

## Local verification

- `pytest -q` — 45 tests passing after the local-intelligence upgrade.
- `python -m compileall -q app.py web_app.py namma tests` — passed.
- `node --check static/app.js` — passed.
- FastAPI TestClient smoke checks: `/`, `/api/health`, `/api/profile` (read/save), and `/api/text` return HTTP 200 on valid requests.

## Recommended laptop validation

1. Keep the existing private `.env`; do not overwrite it with `.env.example`.
2. Run `uvicorn web_app:app --reload` and open `http://127.0.0.1:8000`.
3. Test separate short recordings in Kannada, Telugu and English first.
4. Test the other seven selected speech locales and the configured Timbre voice only if the Gnani account enables them; have fluent speakers judge the audio.
5. For complete task conversations in the seven extended languages, configure and test an OpenAI-compatible multilingual translation endpoint.
6. Enable Prisma v3.0 Auto Detect only if the account has access, then test `indic-auto` and code-mixed speech. Otherwise keep manual language selection.
7. Check that unclear speech asks for repetition and that important numbers, market prices and places are confirmed.
