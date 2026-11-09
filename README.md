# NammaVaani – Voice-first farmer companion

**Speak naturally. NammaVaani listens, understands, checks trusted information and answers aloud.**

This project includes a redesigned responsive web interface inspired by the simple voice-note layout shared by the user: a warm background, language control, one large central microphone, example farmer questions, recent conversations and a small bottom navigation. The original Streamlit prototype is retained as `app.py`; the recommended new interface runs through FastAPI and the browser's microphone.

## Core experience

The voice selector lists ten Indian speech locales documented for Gnani: Kannada, Telugu, Tamil, Hindi, Malayalam, Marathi, Bengali, Gujarati, Punjabi and English (India). Kannada, Telugu and English have built-in complete NammaVaani workflows. The other seven are marked beta unless an optional multilingual translation endpoint is configured; even with that bridge, local-speaker validation is required before claiming full native-language support.

- "What is the weather today in Anekal?"
- "What is today's tomato price?"
- "My borewell motor is not working. Please raise a complaint."
- "Write a letter to the MRO asking for guidance about pesticides for my tomato crop."
- "Which crops are listed for my area?"

NammaVaani uses Gnani Prisma v2.5 to transcribe each voice turn and Gnani Timbre v2.5 to speak the reply when a valid API key is configured. The conversation manager routes the request to a focused service. The current prototype uses transparent rules and verified data services for intent routing; it does not claim to answer every possible question or to use a separate LLM. An optional reasoning model can be added later for broader open-ended queries.

## What is included

1. **Single-microphone home screen** – browser-based recording, clear listening state, language choice, transcript and spoken answer.
2. **Weather questions** – geocodes the selected village/town and fetches a forecast from Open-Meteo. Source, location and retrieval time are shown.
3. **Mandi prices** – tries the official data.gov.in Agmarknet daily-price API first when `DATA_GOV_IN_API_KEY` is configured; falls back to the official CSV saved in the app. Every result displays its recorded arrival date, freshness, source and retrieval time.
4. **Farm repair conversation** – asks for machine, problem and village one question at a time; creates a SQLite service ticket only after spoken confirmation.
5. **Letter drafting** – asks for crop, observed issue and village, then drafts a request to the MRO / concerned Agriculture Officer for official crop-protection guidance. It does not prescribe a pesticide.
6. **Crop information** – displays the UAS Bengaluru Zone V crop basket with a clear note that it is not a plot-specific crop ranking.
7. **My Farm profile** – saves state → district → taluk/mandal → hobli/revenue circle → village, plus land size, soil, irrigation and current crop. The farmer can optionally opt in to save GPS coordinates; those coordinates can be used for a more local weather forecast.
8. **Recent activity and operator ticket list**.

Crop photograph diagnosis and a full daily farm calendar are future extensions, not claimed as implemented in this version.

## Gnani integrations

- **Prisma v2.5:** browser-recorded WAV audio is sent to the Gnani STT endpoint using the selected language code.
- **Timbre v2.5:** the answer is sent to Gnani TTS and returned as WAV audio for playback.
- **Evon v3.3:** not integrated in this prototype. Its open weights require a separately provisioned inference environment.

The UI makes the input and output layers visible: "Prisma listens · Timbre speaks". It does not claim that these models were retrained or internally improved. NammaVaani's application-level contributions are the natural-language task routing, clarification flows, farm profile, source validation and service/letter workflows.

Prisma v2.5 is the default and uses the farmer's selected language code for each recording. The interface offers all ten documented Indian speech locales. Automatic language detection is optional and requires account access to Prisma v3.0: set `GNANI_STT_MODEL=prisma-v3.0` to enable `Auto detect`. Prisma v3.0 supports `indic-auto` and the `codemix` output format. Keep v2.5 as the competition default unless your account has v3.0 access.

For seven additional response languages, an optional OpenAI-compatible translation endpoint can translate requests to English, use NammaVaani's existing verified workflows, then translate the answer back before Timbre speaks it. The endpoint is not bundled; see [LANGUAGE_SUPPORT.md](LANGUAGE_SUPPORT.md) for setup and limitations. English mixing should be tested separately for each language pair.

## Windows setup

Open PowerShell in the inner `NammaVaani` folder (the folder containing `web_app.py`, `app.py` and `requirements.txt`).

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Add your Gnani key to `.env`:

```text
GNANI_API_KEY=your_real_gnani_key
GNANI_STT_MODEL=prisma-v2.5
NAMMAVAANI_MANDI_CSV=data/mandi_prices.csv
```

Keep `.env` private. Do not upload it to GitHub or share screenshots containing the key. `DATA_GOV_IN_API_KEY` is optional for automatic mandi lookup. If it is blank, NammaVaani uses the official Agmarknet CSV upload/backup path.

Start the redesigned web application:

```powershell
uvicorn web_app:app --reload
```

Open `http://127.0.0.1:8000`.

The microphone requires browser permission and works on `localhost`/`127.0.0.1` or an HTTPS deployment. If the Gnani key is not configured, the microphone clearly reports that live speech is unavailable; **Type instead** remains available for testing. Browser text-to-speech fallback is clearly labelled as a device voice, not Gnani Timbre.

For automatic mandi lookup, add a data.gov.in API key to `.env`:

```text
DATA_GOV_IN_API_KEY=your_data_gov_in_key
DATA_GOV_IN_MANDI_RESOURCE_ID=9ef84268-d588-465a-a308-a864a43d0070
```

The key is read only by the Python server and is never sent to the browser. If the key is missing, invalid, or the API has no matching record, NammaVaani tries the saved/uploaded CSV. If both sources fail, it explains that no matching observation is available. The resource contains daily wholesale market observations; it is not a real-time quote or a guaranteed farm-gate price. Official resource: [data.gov.in – Current Daily Price of Various Commodities from Various Markets (Mandi)](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi).

To use the older Streamlit interface, run:

```powershell
streamlit run app.py
```

## Mandi CSV

1. Download the official Agmarknet daily-price CSV from: https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
2. Open NammaVaani → Settings → Mandi price data.
3. Upload the CSV.
4. The file is stored locally as `data/mandi_prices.csv`.
5. Ask for a commodity price. The app shows the market, min/max/modal price, unit, arrival date and freshness label.

CSV values are observations from the downloaded file, not guaranteed farm-gate prices. The app does not invent a price if no matching record exists. Follow the dataset's licence and attribution terms.

## What each request does

- **Weather:** uses the saved farm place name or asks for a village. If the farmer explicitly opts in and captures GPS in My Farm, it can use those saved coordinates. GPS is never requested silently.
- **Market price:** uses the saved state and district; tries the official data.gov.in API first and then the local CSV backup. If no matching record is available, it says so.
- **Repair:** asks for the missing equipment/problem/village; the farmer must say yes before a ticket is created. Unknown motor HP is not mandatory.
- **MRO letter:** asks crop, visible issue and village, then generates a draft. It requests official guidance and does not prescribe pesticides. The farmer must review the recipient designation and fill their name/date before submission.
- **Crop planner:** provides a regional crop information basket from UAS Bengaluru Zone V; it is not a guaranteed best-crop recommendation.

## Competition presentation

For a simple judge-friendly explanation, see [COMPETITION_BRIEF.md](COMPETITION_BRIEF.md). The recommended 60-second live demo is in [DEMO_SCRIPT_60S.md](DEMO_SCRIPT_60S.md). Keep the demonstration focused on one farmer task that actually succeeds; do not claim features that are still marked as limitations.

## Testing

```powershell
pytest -q
```

The automated tests cover crop/market/weather/repair services, the API-first/CSV-fallback path, farmer location hierarchy and consented GPS weather use, common Romanised Kannada/Telugu phrases, letter and repair conversation flows, all ten speech configurations and Timbre voices, script-based language fallback, Prisma v2.5/v3.0 request formatting and optional language bridging. A real Prisma/Timbre call needs your valid Gnani key and account access; a live data.gov.in request needs your own API key and internet access. Phrase support improves common village expressions but does not guarantee arbitrary dialect or code-mixed recognition. Script-based fallback is not acoustic language detection. Built-in task replies are localised in Kannada, Telugu and English; seven additional languages need the optional translation endpoint for task conversations.

## Privacy and production limitations

- Audio is sent to Gnani only after the user checks consent and submits a recording.
- Do not ask farmers to share Aadhaar, bank PINs, OTPs or other unnecessary sensitive information.
- This is a local single-farmer prototype. Production deployment needs authentication, per-farmer data isolation, secure hosting, consent/retention controls, monitoring and expert review for agricultural advice.
- External weather and market data must be shown with its source and timestamp. Weather forecasts are not a guarantee for an individual field.
- The location hierarchy stores names typed by the farmer; this version does not validate every name against a live Local Government Directory (LGD) registry.
- This application currently supports a defined set of intents and conversational workflows. A separate grounded reasoning model and retrieval layer would be needed before presenting it as a general answer-anything assistant.

### Language and detection notes

All ten languages in the selector are configured for Gnani speech input/output, but the full built-in workflows are currently localised in Kannada, Telugu and English. The other seven languages need the optional translation bridge described in `LANGUAGE_SUPPORT.md`; without it, they receive a clearly marked speech-beta notice. This is intentional and avoids presenting an English response as a correct native-language answer.

Auto Detect is disabled under the default Prisma v2.5 setting. Only enable `GNANI_STT_MODEL=prisma-v3.0` when the account has v3.0 access. A Unicode-script fallback can estimate the script after transcription but is not acoustic detection.

## Verify real Gnani API usage (important)

The presence of `GNANI_API_KEY` in `.env` only proves that the application can read a key; it does not prove Gnani accepted it. The Settings page now includes **Test Timbre**, which sends one short real `timbre-v2.5` request. A successful response displays HTTP 200 and the returned audio byte count, and may consume programme credits.

For a command-line check from the inner `NammaVaani` folder (with `.venv` active):

```powershell
python scripts/test_gnani_api.py --language kn
```

This sends one short Kannada sentence to Timbre and saves `gnani_timbre_test_kn.wav` if it succeeds. To test Prisma as well, record a short WAV (maximum 30 seconds) and run:

```powershell
python scripts/test_gnani_api.py --language kn --audio "C:\path\to\your-recording.wav"
```

Each successful API request may consume programme credits. The script never prints the API key. A successful STT test prints the provider request ID; a successful TTS test prints HTTP status and returned audio bytes.

When using the microphone in the web app, the answer card displays separate Prisma and Timbre statuses. `Prisma SUCCESS` means the `/api/voice` request received a successful Prisma response. `Timbre SUCCESS` means real Timbre audio bytes were returned. If Timbre fails, the error is shown explicitly; browser speech fallback is not counted as Gnani usage.

The `/api/health` endpoint only reports whether a key is present—it cannot validate the key. Make sure the key was created in the Gnani **APIs** dashboard for the same account used to register for the competition. Do not share or upload `.env`.
