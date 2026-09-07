# Cybersecurity Workforce Planning

Workforce application for cost-aware cybersecurity workforce planning.

## Launch

From the CISO repository root:

```bash
./web-force/run.sh
```

Open http://127.0.0.1:8503. From this directory, you can also run `./run.sh`.
The launcher uses its own `.venv` environment and port 8503 to avoid conflicts.

## Set up a new environment

From the repository root:

```bash
python3.12 -m venv web-force/.venv
web-force/.venv/bin/python -m pip install -r web-force/requirements.txt
```

## Shared data

`configuration.py` resolves paths relative to its own location, regardless of the
working directory used to launch the application:

- `../data/`: NICE data, costs, `company_state.json`, and mappings under `all_models/`.

Data remains in its original directories. Organization state is read from and saved
to `../data/company_state.json`.

## Tests

The published test suite is `tests/test_scoring_consistency.py`. Run it from the repository root:

```bash
web-force/.venv/bin/python -m unittest discover -s web-force/tests -p 'test_scoring_consistency.py'
```

The scenario pipeline and its embedding test are maintained in the local research
workspace and are not included in this repository. They are not required to run
the Workforce application or the scoring tests above.
