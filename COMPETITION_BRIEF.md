# NammaVaani — Competition Project Brief

## One-line idea

**NammaVaani lets a farmer speak naturally in a familiar language and get clear farming help or complete a small farm-service task by voice.**

## The problem

Many farmers are more comfortable speaking than typing or navigating complex apps. Farming information is also spread across weather services, mandi reports and local service providers. A farmer should not need to understand several apps to ask one simple question.

## The solution

NammaVaani is a simple voice-first farm companion. The farmer selects Kannada, Telugu or English, taps one microphone and speaks. NammaVaani transcribes the recording, recognises a supported task, checks the relevant service or data source, asks a short follow-up when details are missing and speaks the answer.

## Where Gnani AI is used

- **Gnani Prisma v2.5:** converts the farmer's recording into text (speech-to-text).
- **Gnani Timbre v2.5:** converts NammaVaani's answer into spoken audio (text-to-speech).

NammaVaani does not claim to retrain Prisma or Timbre. Its application-level work includes the farmer workflows, local phrase matching, source checks, clarification questions, and repair-ticket and letter-drafting functions. Evon is not integrated in this version.

## What makes the demo useful

1. **Speak simply:** common Kannada/Telugu expressions and English-mixed words are recognised by the application's phrase rules. This is an improvement for tested phrases, not a promise to understand every dialect.
2. **Ask instead of guessing:** when an important detail is missing, the assistant asks one question at a time. It repeats repair details and saves a ticket only after the farmer confirms.
3. **Remember the farm context:** My Farm saves state, district, taluk/mandal, hobli and village. GPS is optional and requires the farmer's explicit consent.
4. **Use visible sources:** weather is fetched from Open-Meteo. Mandi prices use the data.gov.in Agmarknet API first when configured, with the official CSV as fallback. The app shows the observation date and source.
5. **Do a small task:** a farmer can create a repair request or prepare a letter asking an Agriculture Officer for official guidance.

## Recommended live demo (about 60 seconds)

Use the Kannada language setting and make a short voice recording:

> ನಮ್ಮ ಬೋರ್‌ವೆಲ್ ಮೋಟಾರ್ ಓಡುತ್ತಿದೆ, ಆದರೆ ನೀರು ಬರ್ತಿಲ್ಲ. ನಮ್ಮ ಊರು ಅತ್ತಿಬೆಲೆ.

Meaning: “Our borewell motor is running, but water is not coming. Our village is Attibele.”

Show these steps:

1. Prisma transcribes the recording.
2. NammaVaani identifies the borewell motor, the water-output problem and the village.
3. Timbre speaks a confirmation; the farmer says “ಹೌದು”.
4. The app creates a repair ticket and displays its ID.
5. Briefly show My Farm location fields and the source/freshness display for mandi data.

Do not pretend a ticket was created unless the app actually displays the ticket ID. If the transcript misses a detail, answer the clarification question naturally.

## Competition-ready explanation

“Gnani Prisma listens and Gnani Timbre speaks. NammaVaani connects those voice capabilities to practical farmer workflows. Instead of giving an uncertain answer, it asks for missing information, shows where weather and mandi data came from, and asks the farmer to confirm before saving a service request.”

## Technical flow

```text
Farmer speaks
    ↓
Gnani Prisma v2.5 (speech-to-text)
    ↓
NammaVaani intent and phrase rules
    ↓
Weather / Agmarknet API or CSV / repair and letter workflow
    ↓
Clarification and farmer confirmation when needed
    ↓
Gnani Timbre v2.5 (text-to-speech)
    ↓
Farmer hears the answer or sees a completed ticket/draft
```

## What is implemented and what is not

- Built-in full assistant workflows: Kannada, Telugu and English.
- Ten speech-locale configurations exist, but the other seven languages still need the optional translation bridge for complete task conversations.
- Prisma v2.5 requires the farmer to select the spoken language. Auto Detect requires Prisma v3.0 account access and is off by default.
- Agmarknet live API needs the farmer/developer's own data.gov.in API key. If it is not configured or the API fails, the app uses the official CSV backup.
- Farm hierarchy names are typed by the farmer; they are not currently validated against a live LGD directory.
- GPS is only requested after opt-in and button press. It can be used for the farm weather lookup.
- Crop suggestions are a regional UAS Zone V information basket, not a personalised crop ranking. Crop-photo diagnosis and pesticide recommendations are not implemented.
- This is a local prototype, not a production multi-user service. Production use needs authentication, per-farmer data isolation, privacy/security review and agricultural expert validation.

## Test status for this package

- `pytest -q`: 44 automated tests pass.
- `python -m compileall -q .`: passes.
- `node --check static/app.js`: passes.
- Local FastAPI smoke checks passed for the homepage, health endpoint, farmer profile save and typed repair conversation.
- Live Gnani and data.gov.in calls still require the user's private keys and account access. The earlier separate Prisma/Timbre command-line tests were successful; this package has not been live-tested against data.gov.in because no data.gov.in key was available in the build environment.
