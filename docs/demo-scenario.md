# Demo Scenario: Project X

This is the plain-language story the demo is built around.

## Setup

A production company releases a film called Project X on authorized platforms.
The owner registers that work in CineShield.

## 1. Register Content

CineShield records:

- protected work
- rights holder
- duration
- authorized sources

The current demo uses `Project Monsoon` as the sample protected work.

## 2. Generate Content DNA

CineShield creates a layered fingerprint:

- visual DNA
- audio DNA
- scene DNA
- temporal DNA
- OCR/text DNA
- metadata DNA
- semantic profile

The current demo shows these channels in the Content DNA panel.

## 3. Transformed Copy Appears

A candidate copy may be:

- compressed
- cropped
- watermarked
- downscaled
- audio-modified
- subtitle-edited
- partially clipped

The current demo lets you toggle these transformations in the Transformation
Lab and watch the adaptive evidence weights change.

The repository also includes `engine/real_media_benchmark.py`, which generates
short permitted local videos and creates transformed media files for this stage.

## 4. Find My Content

CineShield can now run two discovery modes:

- Blind public discovery: protected title and aliases are searched across
  configured public web indexes, reachable result pages are inspected, relevant
  public links are expanded, authorized domains are excluded, and unknown
  third-party leads are queued.
- If Brave/Bing/Google keys are not configured, the no-key Common Crawl provider
  can still produce public archive URL-index leads, but this is not fresh
  real-time coverage.
- Controlled media verification: uploaded candidate videos, or authorized direct
  public media file URLs, are compared against the protected work with Content
  DNA.

The current demo can run a real local scan through the FastAPI backend when a
protected video and candidate videos are uploaded. It can also run public web
discovery when at least one search provider key is configured. The controlled
scenario and benchmark panels remain for explanation and comparison.

The dashboard now shows two benchmark layers:

- synthetic Content DNA benchmark with a content-level held-out split
- real-media smoke test with generated videos, WAV audio, and extracted fingerprints
- lookalike hard negatives to check false-positive behavior

## 5. Verify and Explain

The system compares each candidate against the protected work and explains which
signals matched.

The current demo shows visual, audio, scene, temporal, OCR/text, and metadata
scores for each selected candidate.

The benchmark layer also reports whether a case is an automated match, automated
negative, or human-review case. This is the decision-coverage metric.

The backend investigator now converts the latest scan results into a structured
summary, priority, failure boundary, and audit trail. This is the current
explainable AI layer over the measured evidence.

## 6. Map the Distribution Cluster

CineShield connects related candidates into a threat graph.

The current demo supports clickable graph nodes and clickable graph edges. Edges
show why two items are connected: Content DNA, same variant, partial match, or
distribution pattern.

## 7. AI Investigator

The AI investigator summarizes structured evidence. It does not decide legality.

The current demo explains the selected candidate and names the uncertainty
boundary, especially for review-gated partial clips.

## 8. Evidence Package

CineShield generates an evidence case for authorized human review.

The current demo can generate and authorize a case package. It does not claim
automatic takedown or legal determination.

## 9. Continuous Monitoring

After authorization, CineShield keeps watching for related transformed copies
and updates the case graph.

The current demo represents this as the final timeline state. Real monitoring is
a future backend milestone.

## Current Coverage

Implemented in this prototype:

- product workflow
- Content DNA UI
- local video upload and FastAPI `/api/scan`
- OpenCV/NumPy fingerprint extraction from uploaded or demo media
- blind public search-index discovery through `/api/discovery/search`
- public seed URL discovery through `/api/discovery/scan`
- bounded public link expansion and coverage reporting
- authorized direct media URL verification bridge
- backend AI investigator summary over scan evidence
- transformation lab
- adaptive fusion simulation
- reproducible synthetic benchmark
- candidate ranking
- clickable threat graph with edge evidence
- evidence package and human authorization
- end-to-end scenario timeline

Not implemented yet:

- FFmpeg transformation generation
- full internet-wide coverage across private, blocked, unindexed, or hidden sources
- automatic verification of arbitrary embedded players or protected streams
- real continuous backend monitoring
- production source connectors at scale
