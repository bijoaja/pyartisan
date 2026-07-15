# Jinja2 template engine wiring is deferred until a framework plugin needs
# anything beyond flat f-string templates (current flasktool commands use
# plain f-strings — see flasktool/commands/*.py and flasktool/utils.py).
# ponytail: no jinja2 dependency yet, add when a plugin needs loops/includes.
