# Local use and later hosting

Public hosting is deferred until both portfolio projects are ready. There is currently no verified public app URL. [Open the local application](http://localhost:8502) works only after starting Streamlit on the reader's computer.

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run streamlit_app.py --server.port 8502
```

Committed lightweight data, model/evaluation artifacts and scenario outputs support startup without raw data or retraining. Relative resources resolve from project paths. Dependency versions are pinned in `requirements.txt`; the local tested runtime is Python 3.12.12; Python 3.11 is the declared minimum, and application/unit/integration CI passed on both Python 3.11 and 3.12. Full artifact reproduction was run locally on Python 3.12.12. Cache loading and repeated simulation inputs in the application.

For later Streamlit Community Cloud deployment, choose public repository `Priynka-Roy/enertwin-industrial-energy-digital-twin`, branch `main`, entry point `streamlit_app.py`, and Python 3.12. Deploy with committed artifacts and no private paths or credentials. Account sign-in and platform terms are completed by the user when hosting begins. Verify every page and a reachable public URL before adding a live-demo badge.

The raw source is excluded from routine deployment and CI. Reproduction downloads it through the official ingestion script. Scenarios use local open-source SciPy HiGHS, not a paid optimization API. Public views must retain dataset attribution and the distinction between observed energy, forecasts and hypothetical costs.

## Version 2 deployment checks

V2 retains the entry point and local port, with separate portable uncertainty/decision artifacts. Historical preserved files in `versions/v1/` are evidence archives and do not need to be loaded by the app. No raw telemetry download, model fitting, external optimizer subscription or credentials are required during startup. Confirm the active V2 artifact schema and manifest integrity, exercise all eight pages and distinguish missing/incompatible artifacts from infeasible user scenarios.

Public hosting remains deferred. A verified local application and passing deployment integration tests establish readiness, not an already hosted service.
