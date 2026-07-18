---
description: Activate voice — record from the microphone and transcribe what you hear
argument-hint: "[duration in seconds, optional]"
---
Call `voice_config` action="set" key="hands_free" value="true" (this arms continuous voice mode: after you speak your response, the Stop hook will automatically listen for what's said next, so the user won't need to type `/talk` again until they say "stop listening" or go quiet for a while). Then call the `listen` MCP tool from the voice server. If `$ARGUMENTS` is a number, pass it as the `duration` argument; otherwise call it with no arguments so it records until trailing silence is detected. Then respond to what was transcribed as you normally would.
