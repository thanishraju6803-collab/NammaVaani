# NammaVaani language support

## Configured Gnani speech locales

| Language | Locale | Timbre v2.5 voice | NammaVaani answer status |
|---|---|---|---|
| Bengali | `bn-IN` | Kirra | Translation bridge required; otherwise speech beta |
| English (India) | `en-IN` | Kaveri (or `.env` override) | Full |
| Gujarati | `gu-IN` | Falak | Translation bridge required; otherwise speech beta |
| Hindi | `hi-IN` | Nalini | Translation bridge required; otherwise speech beta |
| Kannada | `kn-IN` | Kavin | Full |
| Malayalam | `ml-IN` | Reshma | Translation bridge required; otherwise speech beta |
| Marathi | `mr-IN` | Zahira | Translation bridge required; otherwise speech beta |
| Punjabi | `pa-IN` | Mehuli | Translation bridge required; otherwise speech beta |
| Tamil | `ta-IN` | Asmita | Translation bridge required; otherwise speech beta |
| Telugu | `te-IN` | Suhana | Full |

The language locales and preferred Timbre v2.5 voices follow Gnani's published language and voice catalog: https://docs.gnani.ai/api/TTS/available-voices and the official `gnani-vachana` SDK documentation.

## What “supported” means

- Prisma v2.5 speech input and Timbre v2.5 voice configurations are available in the application for all ten listed locales, subject to the user's Gnani account permissions and successful real API testing.
- NammaVaani's built-in farming workflows are directly localised in Kannada, Telugu and English.
- The other seven languages can use the optional translation bridge. The farmer's utterance is translated to English, processed by NammaVaani's existing service logic and source-backed data adapters, then the response is translated back before Timbre speaks it.
- Without the translation bridge, these seven languages are explicitly marked as speech beta and receive a notice in the selected language. They are not presented as fully localised farming assistants.
- Translated responses should be treated as a bridge, not as locally validated native-language agricultural advice. Important names, quantities, prices, dates and instructions must be checked before acting.

## Prisma model modes

- **Default: Prisma v2.5.** Set `GNANI_STT_MODEL=prisma-v2.5`. The farmer chooses the main language for each recording.
- **Optional: Prisma v3.0.** Set `GNANI_STT_MODEL=prisma-v3.0` only if the Gnani account has access. This enables the Auto Detect option and sends `language_code=indic-auto` with `format=codemix`.
- Prisma v3.0 model detection is acoustic/model-level detection. The application's Unicode-script fallback only estimates language from a completed transcript; it is not acoustic language detection.
- English mixing should be tested separately for Kannada-English and Telugu-English. Do not assume every language pair or dialect has equal recognition accuracy.

Official SDK reference: https://github.com/gnani-ai/gnani-vachana (Prisma v3.0 options and API usage).

## Optional multilingual translation bridge

To enable full application flows for Bengali, Gujarati, Hindi, Malayalam, Marathi, Punjabi and Tamil, configure an OpenAI-compatible chat-completions endpoint in `.env`:

```text
NAMMAVAANI_TRANSLATION_API_URL=http://127.0.0.1:8001/v1
NAMMAVAANI_TRANSLATION_API_KEY=
NAMMAVAANI_TRANSLATION_MODEL=your-multilingual-model-name
```

The endpoint is not bundled or hosted by NammaVaani. It must be provisioned separately. A self-hosted Evon v3.3 inference service can be used if it exposes an OpenAI-compatible chat-completions API; another multilingual model may also be used.

NammaVaani uses the translation model only as a language bridge. Weather, market and crop facts continue to come from the application's data services and knowledge sources. The bridge asks the model to preserve numbers exactly and rejects a translation if numeric tokens change. This check is a safeguard, not proof that every translation is perfect.

## Language recovery

- With Prisma v2.5, select the language that will be spoken.
- With Prisma v3.0 and account access, Auto Detect can be enabled.
- When a transcript is visibly returned in a different Indic script from the selected language, NammaVaani can use the script as a fallback signal and reply in the matching configured language. This fallback does not prove the actual acoustic language or understand every code-mixed utterance.
- If speech is unclear, the farmer should repeat, choose the language manually or use the typing fallback.
