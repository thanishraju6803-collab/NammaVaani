# NammaVaani – 60-second competition demo

## Opening (0–8 seconds)

“NammaVaani is a simple voice-first farm companion. A farmer can speak naturally instead of typing or searching through menus.”

## Voice repair task (8–42 seconds)

Choose **Kannada** and record:

> ನಮ್ಮ ಬೋರ್‌ವೆಲ್ ಮೋಟಾರ್ ಓಡುತ್ತಿದೆ, ಆದರೆ ನೀರು ಬರ್ತಿಲ್ಲ. ನಮ್ಮ ಊರು ಅತ್ತಿಬೆಲೆ.

Meaning: “Our borewell motor is running, but water is not coming. Our village is Attibele.”

Show Prisma's transcript and the details NammaVaani understood. Timbre speaks the confirmation. Say **“ಹೌದು”** and show the actual repair ticket ID. If a detail was not understood, answer the follow-up; never fake a successful ticket.

## Trust and local context (42–53 seconds)

Show My Farm's state, district, taluk, hobli and village fields. Mention that optional GPS is saved only after the farmer opts in. If you have live mandi API credentials configured, show the Agmarknet result's source and arrival date; otherwise use a real, current official CSV and label it as CSV data.

## Closing (53–60 seconds)

“Gnani Prisma listens. Gnani Timbre speaks. NammaVaani adds local farmer workflows, clear follow-up questions and source-backed information.”

## Demo honesty notes

- A typed question is not a Prisma speech test. Use the microphone for the main demo.
- Browser speech fallback is not proof of Gnani Timbre. Check the response flags/status.
- Never display made-up mandi prices. Use a real API response or official CSV and show the arrival date.
- The weather forecast uses Open-Meteo, not IMD. The mandi source is daily wholesale data, not a real-time or guaranteed farm-gate price.
- The crop planner shows a UAS Bengaluru Zone V crop basket, not a personalised best-crop prediction.
