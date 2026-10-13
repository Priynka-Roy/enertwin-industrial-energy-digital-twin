# Local use and later hosting

Public hosting is deferred until both portfolio projects are ready. There is currently no verified public app URL. [Open the local application](http://localhost:8502) works only after starting Streamlit on the reader's computer.

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run streamlit_app.py --server.port 8502
```

Committed lightweight data, model/evaluation artifacts and scenario outputs support startup without raw data or retraining. Relative resources resolve from project paths. Dependency versions are pinned in `requirements.txt`; the local tested runtime is Python 3.12.12; Python 3.11 is the declared minimum, not a separately tested runtime. Cache loading and repeated simulation inputs in the application.

For later Streamlit Community Cloud deployment, choose public repository `Priynka-Roy/enertwin-industrial-energy-digital-twin`, branch `main`, entry point `streamlit_app.py`, and Python 3.12. Deploy with committed artifacts and no private paths or credentials. Account sign-in and platform terms are completed by the user when hosting begins. Verify every page and a reachable public URL before adding a live-demo badge.

The raw source is excluded from routine deployment and CI. Reproduction downloads it through the official ingestion script. Scenarios use local open-source SciPy HiGHS, not a paid optimization API. Public views must retain dataset attribution and the distinction between observed energy, forecasts and hypothetical costs.
