---
description: Control spoken replies -- "on"/"off" toggle auto_speak, "full"/"brief" set how much gets spoken. Independent of /talk's listening toggle.
argument-hint: "[on | off | full | brief]"
---
This controls spoken replies only (`auto_speak` and `auto_speak_verbosity`); it does not touch `hands_free`/listening, which `/talk` controls separately.

Parse `$ARGUMENTS`:

- **"on"**: call `voice_config` action="set" key="auto_speak" value="true" unconditionally, then briefly confirm (in text) that spoken replies are back on -- and since auto_speak is now on, this confirmation itself should be spoken aloud.
- **"off"**: call `voice_config` action="set" key="auto_speak" value="false" unconditionally, then briefly confirm (in text) that spoken replies are now off.
- **"full"**: call `voice_config` action="set" key="auto_speak" value="true", then call `voice_config` action="set" key="auto_speak_verbosity" value="full" (speaks the whole reply instead of a truncated summary). Confirm aloud.
- **"brief"**: call `voice_config` action="set" key="auto_speak" value="true", then call `voice_config` action="set" key="auto_speak_verbosity" value="brief" (the default -- a short summary, truncated to `brief_max_chars`). Confirm aloud.
- **empty**: toggle `auto_speak` only (does not change verbosity) -- first call `voice_config` action="get" key="auto_speak" to check the current state, then set it to the opposite and confirm accordingly (same wording rules as "on"/"off" above).
