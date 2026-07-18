---
description: Control hands-free voice mode -- "/talk on" arms it, "/talk off" disarms it, "/talk" alone toggles, a number does a one-shot timed listen
argument-hint: "[on | off | duration in seconds]"
---
Parse `$ARGUMENTS`:

- **"on"** (or empty): call `voice_config` action="set" key="hands_free" value="true" unconditionally (arms continuous voice mode: after you speak your response, the Stop hook will automatically listen for what's said next, so the user won't need to run `/talk` again until they say "stop listening", go quiet for a while, or run `/talk off`). Then call the `listen` MCP tool with no arguments. Then respond to what was transcribed as you normally would.
  - Exception: if `$ARGUMENTS` is empty AND `voice_config` action="get" key="hands_free" is already **true**, treat this as a toggle instead -- set it to **false** and confirm hands-free is now off, without calling `listen`.
- **"off"**: call `voice_config` action="set" key="hands_free" value="false" unconditionally, and briefly confirm hands-free is now off. Do not call `listen`.
- **a number**: call the `listen` MCP tool once with that `duration` (seconds), for a one-shot timed recording. Do not change `hands_free` state either way. Then respond to what was transcribed as you normally would.
