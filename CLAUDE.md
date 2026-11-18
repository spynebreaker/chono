# Rules for AI agents working on this repository

## Clean room
- Never copy, decompile, disassemble or read Adobe Acrobat code or binaries. Behavior comes only from the public PDF standard (ISO 32000) and from observing documents.
- Never copy code from projects whose license is incompatible with AGPL-3.0.
- No Adobe names, logos or look-alike branding in the UI.

## Licensing
- The project is AGPL-3.0 and public. Any new dependency goes into `THIRD_PARTY.md` (name, use, license, copyleft yes/no) in the same commit.

## Users
- The main user is 80 years old and reads Spanish. All UI text is Spanish, short and plain. Big fonts, few options, no technical words.
- No real civil records, names or personal data are committed. Tests use the synthetic corpus in `tests/corpus.py`.

## Code
- Code, comments, file names and commit messages in English.
- Never use the em dash character (U+2014) anywhere: code, docs, UI text or commits.
- Run `python -m pytest tests` before every commit; all tests must pass.
- Keep each external tool behind `app/pdfdad/tools.py` so it can be swapped.
