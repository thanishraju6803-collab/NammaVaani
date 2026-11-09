# NammaVaani Farm Companion — competition submission draft

## One-line summary

NammaVaani is a voice-first farming companion for the Bengaluru region that uses Gnani Prisma and Timbre to let farmers ask questions in Kannada, Telugu or Indian English, then connects the conversation to locally grounded crop information, weather forecasts, mandi observations and farm-repair requests.

## Problem

Farmers may need to navigate multiple sources and digital forms for crop information, weather, market prices and equipment support. Text-heavy interfaces can create language and usability barriers. A transcript alone is not enough: important details such as location, crop, units and dates should be checked before the application takes an action.

## Solution

A simple voice-first interface with a large microphone and clear service choices. The shared conversation flow transcribes a short recording with Gnani Prisma v2.5, identifies the user's intent and routes it to a service. The app reuses a locally stored farm profile, requests missing information one question at a time, retrieves available information from named sources and can speak the response using Gnani Timbre v2.5.

## Competition MVP features

1. Smart Crop Planner — uses UAS Bengaluru Zone V crop information as a local starting point and clearly distinguishes a crop basket from a personalised crop recommendation.
2. Weather and Farm Advisory — retrieves a five-day forecast from Open-Meteo, shows retrieval time and attribution, and explains that forecasts are not guarantees.
3. Mandi Price Assistant — imports the official Agmarknet daily-price CSV, filters by commodity and district, and shows the market, arrival date and freshness; it does not fabricate missing prices and does not require a data.gov.in API key in CSV mode.
4. Shared multilingual voice layer — ten Gnani-supported Indian speech locales are selectable per recording. Kannada, Telugu and English have complete application replies in this release; other locales are disclosed as speech-beta. Prisma v2.5 uses explicit language selection; optional Prisma v3.0 enables `indic-auto` and `codemix`.
5. My Farm profile and retained repair tickets — stores farm context and supports a confirmed equipment-repair request workflow.

## How Gnani is used

- Prisma v2.5: speech-to-text for farmer questions and repair requests.
- Timbre v2.5: spoken responses and confirmations.
- Evon v3.3: not integrated in the submitted MVP; optional future work after a separate inference deployment is available.

## Differentiation

The application-level contribution is a shared farmer profile, conversational intent routing, one-at-a-time clarification, source-labelled data retrieval, explicit freshness labels and confirmation before service actions. We do not claim to have retrained or improved the underlying Gnani speech models. We measure the complete application workflow around them.

## Evidence and evaluation

Run test cases across all ten configured speech locales, prioritising Kannada, Telugu and English-dominant recordings for the competition demo, including controlled code-mixed utterances. Measure transcription word error rate, intent classification accuracy, field extraction accuracy, number of repeated questions, task completion, response latency and source freshness. For crop information, review answers against the relevant UAS Bengaluru Package of Practices. For mandi data, check commodity, market, date, unit, freshness and reported price fields. Publish only measured results.

## Data sources

- UAS Bengaluru agro-climatic zone information and Package of Practices resources.
- Open-Meteo weather forecast API (with attribution).
- Agmarknet daily price dataset downloaded from data.gov.in and imported as CSV.

## Limitations

The first release does not yet provide crop disease image diagnosis, pesticide prescriptions, a complete crop calendar, full offline operation, automatic detection of arbitrary language switching or real technician dispatch. Crop information is not a personalised agronomic prescription. Weather forecasts and market reports must be checked for freshness and local relevance.

## Privacy

The prototype sends a recording to Gnani only after the user explicitly consents. Audio is not stored in the application's SQLite database. The current database is a single-local-profile prototype, not a production multi-user system.
