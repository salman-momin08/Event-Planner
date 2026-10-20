"""Dev helper: run a local TGI-compatible fake so the AI tab can be tried without a Hugging Face token.

From the repository root:
    python -m tests.run_fake_tgi            # listens on http://127.0.0.1:4020
Then, in backend/.env (or the environment) set
    HF_ENDPOINT_URL=http://127.0.0.1:4020
    HF_MODEL_ID=demo/fake-model
and start the backend from backend/ with: python -m app
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from tests.fake_tgi import FakeTgi  # noqa: E402

if __name__ == "__main__":
    with FakeTgi(port=4020) as fake:
        print(f"Fake TGI endpoint on {fake.url}")
        while True:
            time.sleep(3600)
