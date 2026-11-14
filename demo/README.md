# Free interactive showcase

This standalone Streamlit demo is designed for public portfolio viewing without API keys or usage charges. It does not import or modify the production Flask/PostgreSQL application.

## Features and scope

- Real TF-IDF/cosine-similarity retrieval over `data/knowledge_base.csv`, with verbatim source excerpts and document IDs.
- Parameterized SQLite queries over deterministic synthetic availability for eight courts.
- Sample prices copied from `scripts/seed_operational_data.py`; regenerate `catalog.json` if seed prices change.
- In-app architecture and deployment walkthrough.

No LLM generation, embeddings API, production database, booking writes, or personal customer records are used. Retrieval scores are lexical similarity, not confidence. The full RAG pipeline and its evaluations remain documented in the root README.

## Local run

From the repository root, using Python 3.12 or later:

```bash
pip install -r demo/requirements.txt
streamlit run demo/app.py
```

Check the UI flow with `python demo/check_demo.py`.

## Streamlit Community Cloud

1. Fork this repository and connect your GitHub account at https://share.streamlit.io/.
2. Create an app from the repository, branch `main`, entrypoint `demo/app.py`.
3. Choose Python 3.12 in Advanced settings. Leave secrets empty.
4. Deploy. Community Cloud reads `demo/requirements.txt` before dependency files in the repository root.
5. Open the resulting public URL and test the policy example and court-time selector.

Free apps can sleep after inactivity; visitors can wake them. See the [official deployment documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).

