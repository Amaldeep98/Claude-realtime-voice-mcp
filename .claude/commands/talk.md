---
description: Toggle voice — first use arms continuous voice mode and starts listening, second use turns it off
argument-hint: "[duration in seconds, optional]"
---
This is a toggle. First call `voice_config` action="get" key="hands_free" to check the current state.

- If it is currently **false** (off): call `voice_config` action="set" key="hands_free" value="true" (this arms continuous voice mode: after you speak your response, the Stop hook will automatically listen for what's said next, so the user won't need to type `/talk` again until they say "stop listening", go quiet for a while, or run `/talk` again). Then call the `listen` MCP tool from the voice server. If `$ARGUMENTS` is a number, pass it as the `duration` argument; otherwise call it with no arguments so it records until trailing silence is detected. Then respond to what was transcribed as you normally would.
- If it is currently **true** (on): call `voice_config` action="set" key="hands_free" value="false" to turn it off, and briefly confirm to the user that voice mode is now off. Do not call `listen` in this case.
