# flaky-detector-cli

A tiny, zero-dependency command-line tool that uploads a JUnit XML test
report to a [flaky-detector](https://github.com/YOURNAME/flaky-detector)
project — the same thing the project's GitHub Actions snippet does with
`curl`, packaged as a real command.

```bash
pip install flaky-detector-cli
```

## Usage

```bash
pytest --junitxml=report.xml
flaky-detector submit report.xml
```

By default it reads two environment variables — the same two names your
flaky-detector project's CI snippet already uses:

- `FLAKY_DETECTOR_URL` — your backend's base URL
- `FLAKY_DETECTOR_TOKEN` — the project's upload token

Everything else is auto-detected. In GitHub Actions, it reads `GITHUB_SHA`,
`GITHUB_REF_NAME`, `GITHUB_RUN_ID`, and `GITHUB_RUN_ATTEMPT` automatically.
Running locally, it falls back to your current `git` checkout for the
commit and branch. You can override any of it explicitly:

```bash
flaky-detector submit report.xml \
  --url https://your-backend.example.com \
  --token YOUR_TOKEN \
  --commit abc1234 \
  --branch main \
  --run-id 42 \
  --run-attempt 1
```

## Why not `curl`?

`curl` works fine and is what the project's own onboarding flow suggests
first. This exists for people who'd rather not hand-build a multipart
`curl` command in CI YAML, and for local use: run your suite, then
`flaky-detector submit report.xml` to see the result on your dashboard
without touching CI at all.

## Exit codes

- `0` — uploaded successfully
- `1` — the server rejected the upload (bad token, malformed report, etc.);
  stderr has the reason
- `2` — a required argument is missing (no URL/token, and none could be
  auto-detected)

## Development

```bash
git clone https://github.com/YOURNAME/flaky-detector
cd flaky-detector/cli
pip install -e .
```

No dependencies to install for either running or developing this tool —
only the Python standard library.