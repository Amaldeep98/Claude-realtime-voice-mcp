---
description: Browse the 54 available voices, or switch the active one
argument-hint: "[voice_id | language_code, optional]"
---
Handle this with the voice MCP server's tools:

- If `$ARGUMENTS` is empty: call `list_voices` and present the full list grouped by language (a=American English, b=British English, e=Spanish, f=French, h=Hindi, i=Italian, j=Japanese, p=Brazilian Portuguese, z=Mandarin), noting the current default voice (from `voice_config` action="get" key="voice").
- If `$ARGUMENTS` is a single letter matching one of those language codes: call `list_voices` filtered to that language and show only those options.
- Otherwise treat `$ARGUMENTS` as a voice id: call `voice_config` action="set" key="voice" value="$ARGUMENTS", then speak a short confirmation in the new voice.
