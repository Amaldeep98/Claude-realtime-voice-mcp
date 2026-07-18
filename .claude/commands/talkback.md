---
description: Control spoken replies -- "/talkback on" or "off" set it explicitly, bare "/talkback" toggles. Independent of /talk's listening toggle.
argument-hint: "[on | off]"
---
This controls spoken replies only (`auto_speak`); it does not touch `hands_free`/listening, which `/talk` controls separately.

Parse `$ARGUMENTS`:

- **"on"**: call `voice_config` action="set" key="auto_speak" value="true" unconditionally, then briefly confirm (in text) that spoken replies are back on -- and since auto_speak is now on, this confirmation itself should be spoken aloud.
- **"off"**: call `voice_config` action="set" key="auto_speak" value="false" unconditionally, then briefly confirm (in text) that spoken replies are now off.
- **empty**: toggle -- first call `voice_config` action="get" key="auto_speak" to check the current state, then set it to the opposite and confirm accordingly (same wording rules as above).
