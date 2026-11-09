# NammaVaani – Product and UI specification

## Product idea

NammaVaani is a voice-first farmer task assistant. The farmer opens one microphone and speaks naturally. NammaVaani identifies the task, asks only necessary follow-up questions, retrieves verified information or prepares a document, then speaks the answer in the selected language.

## Primary tasks in the current prototype

- Ask for weather in a village/town (Open-Meteo forecast with source/time shown).
- Ask for a commodity price (official Agmarknet CSV imported locally; actual observation date shown).
- Report a farm equipment problem (voice-led clarification and confirmed service ticket).
- Draft a letter to the MRO / concerned Agriculture Officer requesting official crop-protection guidance (asks crop, issue and village; provides editable/downloadable draft; does not prescribe pesticides).
- Ask about locally documented crop options (UAS Bengaluru Zone V crop basket; not a personalised crop ranking).

## Future farmer services

- Crop health image support with a separately validated vision model.
- Crop calendar and daily task reminders.
- Soil Health Card reading.
- Government scheme information with official-source retrieval.
- Nearby KVK/agriculture office contacts.
- Local repair/service-provider directory and actual dispatch integrations.

## UI direction from the user references

- Warm cream/off-white background.
- Soft pale yellow-to-lilac welcome card.
- Compact brand header, village/location at the top right and profile shortcut.
- One large round microphone at the centre, with a gentle yellow/lilac ring.
- Language picker directly above the mic.
- Minimal instruction below the mic.
- Small "Farmers are asking" examples.
- Recent conversations with visible written answers and play-audio control.
- Bottom navigation: Talk, My Farm, Activity, Settings.
- On mobile, the microphone and greeting occupy the first screen; secondary content stays below.

## Gnani model showcase

- Prisma v2.5 handles each farmer voice turn (STT).
- Timbre v2.5 speaks assistant prompts and answers (TTS).
- Both are shown in the UI and response metadata.
- Evon v3.3 is optional and not falsely marked as integrated.
- Application-level differentiation is task routing, conversational slot filling, farm memory, verification, trusted data sources and real-world actions.

## Current limitations

This is a defined set of conversational workflows, not an unrestricted answer-anything LLM. STT language is selected per recording; automatic arbitrary language identification is not implemented. The project uses a local single-farmer SQLite profile and in-memory sessions; production deployment needs authentication, per-farmer isolation, persistent session state and security review.
