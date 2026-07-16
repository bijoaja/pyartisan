# Project API (PRD.md section 3/12 "Project API" layer) is deferred until a
# second framework plugin needs it — right now pyartisan.plugin.flask writes
# files directly via pyartisan.utils.fs, which is enough for one plugin.
# ponytail: no ProjectAPI abstraction yet, add when a plugin must not touch
# the filesystem directly (e.g. sandboxed/dry-run generation, marketplace
# plugins that must go through a mediated write path).
