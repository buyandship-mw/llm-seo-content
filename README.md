Ensure you are in the root directory before proceeding with these commands.

To run the pipeline: `python3 app.py`

The OpenAI clients now read credentials from environment variables. You can
create a `.env` file (see `.env.sample`) and the application will load it
automatically.

To run a module on its own: `python3 -m modules/<module>.py`

To run the test suite: `pytest`

Firecrawl scraper: https://www.firecrawl.dev/playground