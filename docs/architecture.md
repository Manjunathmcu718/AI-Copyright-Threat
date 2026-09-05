# CineShield Architecture

## One-Glance Flow

```text
Protected movie / episode / clip
  -> Content DNA
  -> Candidate discovery
  -> Video fingerprinting
  -> Visual + audio + scene evidence
  -> Evidence fusion
  -> Match / Review / Reject
  -> Threat graph
  -> Evidence package
  -> Human authorization
```

```text
CINESHIELD
  |
  +-- Register Content
  |     owner, title, duration, authorized sources
  |
  +-- Content DNA Engine
  |     visual fingerprint
  |     audio fingerprint
  |     scene sequence
  |     temporal profile
  |     OCR/text profile
  |     metadata profile
  |     semantic embedding
  |
  +-- Discovery Engine
  |     optional multi-index public search connector
  |     public-page connector from seed URLs
  |     query variant generation
  |     bounded public link expansion
  |     authorized-source registry
  |     title, metadata, and link extraction
  |     media-reference detection without download
  |     candidate lead scoring
  |     coverage report: providers, pages, domains, blocked sources
  |     candidate media records
  |     safe direct media URL verification bridge
  |
  +-- Transformation Detector
  |     compression
  |     crop
  |     watermark
  |     resolution change
  |     audio modification
  |     subtitle modification
  |     partial extraction
  |
  +-- Adaptive Evidence Fusion
  |     transformation-aware signal weighting
  |     confidence calculation
  |     review thresholding
  |
  +-- Threat Graph
  |     nodes: works, candidates, variants, source clusters
  |     edges: content DNA match, scene sequence match, pattern relationship
  |
  +-- AI Investigator
  |     structured evidence summary from scan results
  |     priority recommendation
  |     uncertainty and failure-boundary explanation
  |     audit trail for human review
  |
  +-- Evidence Case
  |     match scores
  |     transformation profile
  |     related sources
  |     human review status
  |
  +-- Authorized Response
        generated packet only after rights-holder review
```

## Research Claim

Can adaptive multimodal evidence fusion improve transformed-content identification
compared with fixed-weight or single-modality matching?

## Evaluation

Create a permitted test corpus:

- original sample video
- compressed variant
- cropped variant
- watermarked variant
- resolution-changed variant
- audio-modified variant
- subtitle-modified variant
- partial clip
- unrelated negatives

Measure:

- precision
- recall
- F1 score
- false-positive rate
- confidence by transformation type
- baseline versus adaptive fusion gain

The current prototype includes a reproducible synthetic version of this
evaluation in `engine/cineshield_engine.py`. It writes generated results into
`data/benchmark-results.json` and `data/benchmark-results.js`, which are loaded
by the dashboard.

The current prototype also includes a small real-media smoke test in
`engine/real_media_benchmark.py`. It generates permitted local videos and WAV
audio, applies transformations, extracts actual frame/audio/scene/temporal
fingerprints, and writes results into `data/real-media-results.json` and
`data/real-media-results.js`.

The current backend includes a real local scanning path:

- `backend/main.py` exposes `/api/scan` for protected-video plus candidate-video uploads.
- `backend/main.py` exposes `/api/scan/url-candidates` for authorized direct media URL candidate verification.
- `backend/main.py` exposes `/api/discovery/scan` for public seed URL discovery.
- `backend/main.py` exposes `/api/discovery/search` for optional Brave/Bing/Google public web-index discovery.
- `backend/media_scan.py` extracts visual, scene, temporal, duration, and coverage signals.
- `backend/discovery.py` fetches public HTML/metadata, extracts relevant links, detects media-reference hints, excludes configured authorized domains, scores discovery leads, and keeps them separate from verified Content DNA matches.
- `backend/investigator.py` converts scan results into priority, uncertainty boundaries, and an audit trail.

## Discovery Connector Boundary

The Phase 2 connector is designed as:

```text
Protected title + aliases
  -> query variants: title, full movie, watch online, free streaming, download, 1080p, 720p, 4K, web-dl, dubbed, torrent
  -> public search indexes or public seed URLs
  -> no-key Common Crawl archive URL-index fallback
  -> authorized domain exclusion
  -> Level 0 search leads
  -> HTML/metadata fetch on reachable public pages
  -> title/link/context/media-reference extraction
  -> relevant public links added to bounded expansion queue
  -> next public pages scanned up to configured depth/page budget
  -> discovery lead score
  -> coverage report: results, pages, domains, unknown domains, blocked/unreachable
  -> candidate queue
  -> authorized direct media URL or uploaded candidate
  -> Content DNA verification
```

It does not download unauthorized videos, capture streams, bypass access controls,
or make legal claims from metadata. A discovery lead only means "worth verifying";
the evidence case starts after Content DNA comparison. Without a configured search
provider key, the app still performs seed URL discovery and displays the planned
search queries for setup. Common Crawl can provide archive URL-index leads without
a key, but those leads are not guaranteed to be fresh. The connector reports
measured public coverage; it does not claim to scan private, blocked,
CAPTCHA-protected, DRM-protected, or unindexed parts of the internet.

The URL verification bridge is deliberately narrow:

```text
Protected video upload
  -> authorized direct candidate media URLs
  -> public URL and extension validation
  -> 75 MB candidate cap
  -> local Content DNA extraction
  -> Match / Review / Reject
```

It does not process webpages, embedded players, HLS/DASH playlists, DRM streams,
private groups, login-only sources, or blocked pages.

## Evidence Ladder

Every candidate has an evidence level:

```text
0 Search lead
1 Page evidence
2 Media reference
3 Content fingerprint
4 Multimodal match
```

The live public-web connector currently produces Level 0-2 records. Uploaded or
authorized candidate media can then move to Level 3-4 through the Content DNA
scanner. This prevents a search/page title match from being presented as a
verified copyright match.

Discovery candidates carry separate fields for metadata relevance,
investigation risk, media evidence, and content-match score. Metadata can be high
for news or encyclopedia pages, while risk stays low until distribution language
or media references appear. Content-match score stays empty until a permitted
media candidate is processed by the Content DNA engine.

## AI Positioning

The first implemented AI layer is not a generative chatbot. It is a
pattern-recognition and evidence-fusion system:

- computer-vision fingerprint extraction
- temporal and scene similarity matching
- adaptive weighting based on signal reliability
- explainable investigator reasoning over the scan evidence

A future LLM layer can summarize larger threat graphs, but legal conclusions and
external actions remain human-authorized.

## Product Principle

CineShield should say "high-confidence suspected unauthorized distribution", not
"illegal content". Legal and platform action remains with the authorized rights holder.
