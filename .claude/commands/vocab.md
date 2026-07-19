---
description: Teach the STT model words/names it mishears (app names, jargon, rare terms) -- "/vocab add <word>", "/vocab remove <word>", "/vocab" or "/vocab list" to see the current list
argument-hint: "[add <word> | remove <word> | list]"
---
Parse `$ARGUMENTS`:

- Starts with **"add "**: call `vocabulary` action="add" word="<the rest of the text after 'add '>". Confirm what was added and show the resulting full list.
- Starts with **"remove "**: call `vocabulary` action="remove" word="<the rest of the text after 'remove '>". Confirm what was removed and show the resulting full list.
- **empty or "list"**: call `vocabulary` action="list" and show the current vocabulary (or note it's empty and explain what this is for, if so).
