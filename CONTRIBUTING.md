# Contributing

Thanks for wanting to improve this project. Humans cooperating is rare, so let's keep it simple.

## Quick rules
- Be respectful. No drama.
- Keep PRs focused (one change-set per PR).
- If you change UI text, update both EN and TR in `languages.py`.
- If you add a dependency, explain why and keep optional features optional.

## Dev setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Optional: repair feature
pip install -r requirements-repair.txt
python main.py
```

## Making a plugin
Drop a `*.py` file into the `plugins/` folder, define a `Plugin` class, and either:
- implement `run(main_window)`, or
- override `get_actions(main_window)` to expose multiple menu actions.

See `plugins/hello_plugin.py`.

## Reporting bugs
Include:
- what you clicked
- what you expected
- what happened instead
- OS + Python version (if running from source)
- the relevant part of the log output
