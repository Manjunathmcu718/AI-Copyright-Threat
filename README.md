# CineShield 2.0

AI Copyright Threat Intelligence and Autonomous Response Platform.

CineShield gives every copyrighted video a Content DNA, detects transformed copies,
maps related distribution clusters, explains every match, and generates evidence-backed
response cases for human review.

## Track

Razorpay Buildathon 2026, Open Track.

## Core Innovation

The technical centerpiece is the Content DNA Robustness Engine:

- Multimodal content profile: visual, audio, scene, temporal, OCR/text, metadata, semantic.
- Transformation detection: compression, crop, watermark, subtitle edit, audio modification, partial clip.
- Adaptive evidence fusion: signal weights change based on the detected transformation.
- Human-gated response: the system produces evidence, not accusations or automatic takedowns.

The current repository includes a reproducible synthetic benchmark engine in
`engine/cineshield_engine.py`. It generates Content DNA vectors, applies
transformation profiles, compares a fixed-weight baseline against adaptive
fusion, and writes dashboard-ready results to `data/benchmark-results.json` and
`data/benchmark-results.js`.

Current generated result:

- Baseline F1: 87%
- Adaptive CineShield F1: 97%
- Evaluation sample count: 540 held-out synthetic examples
- Total generated examples: 900
- Split: content-level, with 4 calibration works and 6 held-out test works
- Decision coverage: 94% automated match/reject, 6% human review
- Automated decision accuracy: 100% on automated synthetic decisions
- Seed: 7429

The repository also includes a smaller real-media smoke test in
`engine/real_media_benchmark.py`. It creates permitted synthetic videos and WAV
audio locally, applies transformations, extracts frame/audio/scene/temporal
fingerprints with OpenCV and NumPy, and writes results to
`data/real-media-results.json` and `data/real-media-results.js`.

Current real-media smoke result:

- Baseline F1: 82%
- Adaptive CineShield F1: 100%
- Evaluation sample count: 200 generated media pairs
- Works: 5 generated permitted test videos
- Hard negative: includes a deliberate Project Monsoon lookalike
- Threshold: 90%
- Decision coverage: 72% automated match/reject, 28% human review
- Automated decision accuracy: 100% on automated smoke-test decisions

The current app also includes a real local scanner path:

- `backend/main.py` exposes FastAPI endpoints including `/api/scan` and `/api/scan/demo`.
- `backend/main.py` exposes `/api/scan/url-candidates` for the bridge between discovery leads and Content DNA verification. It accepts a protected video plus direct public candidate media URLs only when authorization is confirmed.
- `backend/media_scan.py` extracts local video fingerprints with OpenCV and NumPy.
- `backend/investigator.py` turns scan results into priority, uncertainty boundaries, audit steps, and human-review reasoning.
- The frontend uploads a protected video plus candidate videos and renders ranked Match / Review / No match results from the backend.
- `backend/discovery.py` adds a public Discovery Connector. It accepts a protected title, aliases, seed URLs, provider choices, expansion depth, and authorized domains; fetches public HTML/metadata; extracts candidate links and media-reference hints; excludes official sources; scores non-authorized leads; and sends them to the dashboard for review before Content DNA verification.
- `backend/discovery.py` also includes optional multi-index discovery through `/api/discovery/search`. With Brave, Bing, or Google Programmable Search keys set on the backend, plus a no-key Common Crawl archive-index fallback, CineShield creates Level 0 public web-index leads, deep-scans the top reachable public result pages, expands through relevant public links, filters authorized domains, and reports coverage across pages, domains, unknown domains, blocked sources, media references, and high-risk leads.

Discovery and verification are intentionally separate:

```text
Discovery score: title, URL, page context, media-reference hints
Content match score: visual, scene, temporal, duration, coverage fingerprints
```

Discovery scoring is split so ordinary articles do not look like confirmed
matches:

```text
Metadata relevance -> investigation risk -> media evidence -> Content DNA score
```

A news/review/encyclopedia page can be highly relevant but low risk. A high-risk
lead requires distribution language, media references, or stronger source-page
signals. Only uploaded media or authorized direct media URLs can produce a
Content DNA match score.

The discovery UI also shows an evidence ladder:

```text
0 Search lead -> 1 Page evidence -> 2 Media reference -> 3 Content fingerprint -> 4 Multimodal match
```

Current public-web discovery reaches Levels 1-2 for ordinary pages. The existing uploaded-media scanner reaches Levels 3-4 for media the project is authorized to process.
The URL-candidate verifier now moves a direct public media URL discovered from a public page into Levels 3-4, attaches the Content DNA result back to that discovery lead, and updates the graph/evidence case. This only runs when the URL is a direct video file and the user confirms they are authorized to process it.

Implemented discovery stack:

- Continuous monitor mode reruns the selected discovery cycle every 45 seconds and records run history.
- Multi-provider mode supports Brave, Bing, Google Programmable Search, and Common Crawl provider status side by side.
- Unknown-domain expansion follows relevant public links with bounded depth, page count, and per-domain limits.
- Blocked/unreachable reporting records sources that cannot be reached instead of hiding them.
- Direct-media extraction identifies public video file references without downloading pages that are not eligible.
- Partner/source connector input accepts public URL lists or simple JSON feeds and routes them through the same discovery pipeline.
- Coverage dashboard reports searched results, reached pages, blocked pages, media references, DNA-verified candidates, and matches.

## Where Exactly Is The AI?

The current prototype does not pretend to be a full LLM product. The implemented
intelligence is the multimedia verification layer:

- computer-vision fingerprint extraction from video frames
- temporal and scene-pattern comparison
- adaptive evidence fusion that changes weights based on signal reliability
- explainable investigator reasoning over structured scan evidence

The future generative AI layer can summarize larger cases and source graphs, but
the present system is already a working pattern-recognition and evidence-fusion
pipeline.

The current implementation is not claiming a trained deep-learning piracy model.
It uses a deterministic OpenCV/NumPy feature pipeline today, with a clear upgrade
path to CNN, CLIP, or video-embedding models later.

Content DNA is generated as:

```text
Video -> frame sampling -> normalized visual vectors -> scene order
      -> temporal profile -> duration/coverage signals -> evidence fusion
      -> similarity score and decision
```

## Demo Flow

1. Register a protected test reel.
2. Generate Content DNA.
3. Use **Search Internet For This Work** from the Live Scan panel, or run Live Web Discovery with public seed URLs, to create candidate leads.
4. For a blind owned test, tick the discovered-media authorization checkbox. If a discovered page exposes a direct public video file, CineShield sends that media into Content DNA verification and upgrades the same web lead to Match / Review / No match.
5. Inspect a ranked candidate and its adaptive match explanation.
6. Explore the threat graph of related source clusters.
7. Generate an evidence package for authorized human review.

## Run

Start the backend:

```powershell
python -m uvicorn backend.main:app --reload --port 8001
```

Serve the frontend:

```powershell
python -m http.server 8080
```

Then open:

```text
http://127.0.0.1:8080/index.html
```

No frontend build step is required for this prototype.

For blind live web discovery, enter only the protected title, aliases,
official/authorized domains to exclude, provider choices, and expansion limits.
CineShield generates broad search variants such as title, full movie, watch
online, free streaming, download, 1080p, 720p, 4K, web-dl, dubbed, torrent, and
stream; queries configured public indexes; fetches
reachable public page metadata; expands through relevant public links; ranks
non-authorized candidate leads; shows media-reference evidence where present; and
excludes official OTT/distributor domains before the verification queue. It does
not fetch or download video content from those pages.

From the Live Scan panel, uploading a protected video can also infer the discovery
title from the filename. Use **Search Internet For This Work** to sync that title
into the discovery connector and launch the blind public search-index flow. This
button ignores manual source-focus domains and seed URLs so the demo can show:
protected work plus title in, public discovery leads out.

Manual discovery is still available separately. Use **Scan Public Sources** when a
rights-holder, partner, or researcher gives you public seed URLs to inspect.

For URL candidate verification, select a protected video, paste direct public
candidate video file URLs that you are authorized to process, tick the permission
confirmation box, and run **Verify URL Candidates**. CineShield downloads only
direct video files such as `.mp4`, `.webm`, `.avi`, `.mov`, `.mkv`, or `.m4v`,
caps each candidate at 75 MB, and then runs the same Content DNA verification
pipeline used for uploaded files.

For blind web discovery plus verification, upload the protected video, enter the
title/aliases, tick the discovered-media authorization checkbox, and click
**Search Internet For This Work**. Search results without direct public video
files remain discovery leads. Search results with direct public video files move
through URL verification and reappear in the discovery list, threat graph, and
evidence case with the actual Content DNA score.

Common Crawl URL-index discovery can run without a key, but it is archive
coverage, not fresh real-time search. To enable stronger live public search-index
discovery, set one or more provider keys before starting the backend. The easiest
local setup is:

```powershell
Copy-Item .env.example .env
notepad .env
python -m uvicorn backend.main:app --reload --port 8001
```

Or set the variables directly in PowerShell:

```powershell
$env:BRAVE_SEARCH_API_KEY="your_key_here"
$env:BING_SEARCH_API_KEY="your_key_here"
$env:GOOGLE_CSE_API_KEY="your_key_here"
$env:GOOGLE_CSE_ID="your_search_engine_id"
python -m uvicorn backend.main:app --reload --port 8001
```

Then use **Search Web Index** in the dashboard. Without provider keys, the app
still tries the Common Crawl public archive URL index and shows missing-key
provider chips for Brave, Bing, or Google instead of pretending full internet-wide
discovery ran.

To regenerate benchmark results:

```powershell
python engine\cineshield_engine.py
python engine\real_media_benchmark.py
```

## Safety Boundary

The Discovery Connector fetches public HTML and metadata from public search
results and user-provided seed URLs. It does not download pirated videos, capture
streams, bypass logins, bypass paywalls, solve CAPTCHA, defeat Cloudflare/DRM, or
access hidden/private sources. The URL-candidate verifier is intentionally limited
to direct public video files with explicit authorization confirmation. Use the
Content DNA scanner only with media you have permission to process. Screenshots of
external piracy ecosystems are problem-context examples, not proof that those
sites are current data sources.

## Known Limitations

- The larger 540-example benchmark uses synthetic Content DNA vectors; the smaller smoke test and local API path use generated or uploaded media.
- Real-media inputs are locally generated test videos, not real films or internet sources.
- Discovery can scan user-provided public seed URLs immediately. Common Crawl URL-index discovery works without a key but is not real-time. Fresh public search-index discovery requires at least one configured provider key such as `BRAVE_SEARCH_API_KEY`, `BING_SEARCH_API_KEY`, or `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID`.
- Multi-index discovery expands through reachable public links with a bounded page budget and reports coverage; it still cannot guarantee every private, blocked, unindexed, or hidden source on the internet.
- Authorized-source filtering is domain-based and should be configured by the rights holder.
- Public discovery results are candidate leads until the media scanner verifies actual content fingerprints.
- URL verification accepts direct public video file URLs only; it does not inspect embedded players, playlists, DRM streams, private groups, or hidden/blocked pages.
- Partial clips remain a hard case and are intentionally review-gated.
- Smoke-test 100% F1 is pipeline validation, not a generalization claim.
- The system supports evidence preparation, not legal determination or automatic takedown.

## Next Engineering Steps

- Replace generated videos with permitted sample films/trailers.
- Add FFmpeg support for richer transformations when available.
- Expand the FastAPI service with authentication, persistent cases, and audit logs.
- Expand the real-media benchmark with more hard negatives and severity levels.
- Add persistent discovery queues, scheduled jobs, Common Crawl/domain intelligence, partner feeds, case export, and monitored candidate queues.

## Buildathon Materials

- Architecture notes: `docs/architecture.md`
- Five-minute pitch script: `docs/pitch-script.md`
- Plain-language demo scenario: `docs/demo-scenario.md`
- Benchmark methodology: `docs/benchmark-methodology.md`
