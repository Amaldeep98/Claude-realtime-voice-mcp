---
description: Toggle talk-back — turn spoken replies (auto_speak) on or off, independent of /talk's listening toggle
---
This is a toggle for spoken replies only (it does not touch `hands_free`/listening, which `/talk` controls separately).

First call `voice_config` action="get" key="auto_speak" to check the current state.

- If it is currently **true** (on): call `voice_config` action="set" key="auto_speak" value="false", then briefly confirm (in text) that spoken replies are now off.
- If it is currently **false** (off): call `voice_config` action="set" key="auto_speak" value="true", then briefly confirm (in text) that spoken replies are back on -- and this confirmation itself should be spoken aloud since auto_speak is now on.
