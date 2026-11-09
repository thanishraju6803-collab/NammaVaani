# NammaVaani – Simple Local Intelligence Upgrade

## What is better now

1. **More natural local words:** understands more common Romanised Kannada/Telugu, regional crop names and English-mixed phrases such as “motor on agutte, neeru baralla”, “tamota rate eshtu?” and “ivattu male barutta?”. This is an application phrase-list improvement; Prisma itself has not been retrained.
2. **Human-style clarification:** when the assistant is unsure, it says so and asks a short follow-up instead of inventing an answer. Repair details are reviewed aloud and a ticket is saved only after the farmer confirms.
3. **Full farm location profile:** My Farm records state, district, taluk/mandal, hobli/revenue circle and village/town. These names are farmer-entered and are not yet validated against a live LGD registry.
4. **Optional GPS:** GPS permission is requested only after the farmer checks the consent box and presses “Use my current location”. The saved coordinates can be used for a more local weather forecast. Unchecking consent removes the stored coordinates the next time the profile is saved.
5. **Official mandi API first:** when configured, NammaVaani calls the official data.gov.in Agmarknet daily price resource. If the key, connection or matching data is unavailable, it uses the saved/uploaded official CSV. Results show source, arrival date and freshness.
6. **Clear source labels:** weather shows Open-Meteo and retrieval time; mandi shows Agmarknet API/CSV source, actual arrival date, freshness and retrieval time.

## Configure the government mandi API

Add your own data.gov.in API key in `.env`:

```text
DATA_GOV_IN_API_KEY=your_data_gov_in_key
DATA_GOV_IN_MANDI_RESOURCE_ID=9ef84268-d588-465a-a308-a864a43d0070
```

Restart NammaVaani. Keep the key private. It is used by the server only and is not included in browser code. The CSV flow remains the fallback and works when the API key is blank.

Official dataset: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi

## What remains unchanged

- Gnani Prisma v2.5 speech-to-text and Timbre v2.5 text-to-speech.
- Kannada, Telugu and English built-in assistant workflows.
- Farmer-confirmed repair tickets and MRO letter drafts.
- The simple single-microphone interface and local SQLite profile.

## Honest limits

Local phrase matching improves common examples but cannot guarantee every dialect, accent or arbitrary Kannada–Telugu–English switch. Prisma v2.5 still uses the selected language per recording. GPS is opt-in and only used for the weather lookup when the farmer has saved it with consent. The hierarchy fields store names but are not yet checked against a live government LGD list. Mandi data is a daily wholesale observation, not a real-time quote or guaranteed farm-gate price.
