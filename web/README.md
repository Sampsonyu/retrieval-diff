# Public demo source

Live URL: https://retrieval-diff-demo.sampsonyu.chatgpt.site

`index.html` is a buildless landing page. Numeric placeholders are filled from
executed experiment measurements by `scripts/build_public_demo.py`. Reports are
regenerated from recorded snapshots using the current Python template and include
links to the overview and companion cases. Measurements are checked against the
snapshots before publication.
No uploads, model calls, analytics, signup, or server application are needed.

Rebuild from the repository root:

```sh
python examples/build_demo.py
retrieval-diff compare artifacts/demo/baseline.json artifacts/demo/candidate.json \
  --k 1 --html artifacts/demo/report.html  # expected exit 1
python examples/fastapi_docs/run.py
python examples/fastapi_docs/run.py --fixed --output artifacts/fastapi-docs-fixed
python scripts/build_public_demo.py
```

Install the optional public-document example requirements first. The build output
is `artifacts/public-demo/`. Copy it into the retained Sites checkout's `dist/`
when updating hosting; preserve that checkout's `.openai/hosting.json` identity.
Sites credentials are not part of this repository.

Hosting project ID: `appgprj_6af785735f448191bb46f1d8cfbc2810`.
The original publication was confirmed by the native Sites deployment service.
The Cloud preview relay failed to start; hosted-page browser QA is unverified.
A direct executor HTTP probe encountered Cloudflare 403/1010, so it did not
establish anonymous browser access. The native service confirms public access and
successful deployment; verify the live experience in an ordinary browser before
a broad launch.
