# Benchmark Methodology

This milestone turns CineShield from a pure UI prototype into a measurable
engineering prototype.

## What Is Measured

The benchmark compares two matchers over the same synthetic Content DNA corpus.

Baseline:

- fixed evidence weights
- visual-heavy scoring
- no transformation-aware reliability estimate

CineShield adaptive fusion:

- estimates which evidence channels appear degraded
- adjusts trust across visual, audio, scene, temporal, text, and metadata signals
- keeps low-coverage cases review-gated

## Corpus

`engine/cineshield_engine.py` generates 900 examples from a fixed seed.
The dashboard reports evaluation results only on the held-out test works.

Current split:

- 4 calibration works
- 6 held-out test works
- 360 calibration examples
- 540 test examples
- 5 positive variants per transformation per work
- 5 hard negatives per transformation per work

The split is content-level: transformed variants of held-out test works are not
mixed with calibration works.

Each example contains six synthetic Content DNA channels:

- visual
- audio
- scene
- temporal
- text
- metadata

The benchmark includes positives and hard negatives for:

- clean copy
- compression
- resolution change
- cropping
- watermark
- audio modification
- subtitle edit
- partial clip
- combined transformations

Hard negatives intentionally share some surface-level evidence with the
protected work, such as similar metadata, title-like text, or one strong signal.
This prevents the benchmark from being too easy.

## Metrics

The generated dashboard reports:

- baseline F1
- adaptive F1
- gain
- robustness degradation
- precision and recall in the JSON output
- decision coverage
- review rate
- automated decision accuracy

The matching threshold is recorded in `data/benchmark-results.json`.

## Current Result

The current generated benchmark reports:

- Baseline F1: 87%
- Adaptive CineShield F1: 97%
- Test examples: 540
- Total generated examples: 900
- Decision coverage: 94%
- Review rate: 6%
- Automated decision accuracy: 100%
- Seed: 7429

The most important result is not that CineShield wins every row. The useful
claim is narrower:

Adaptive multimodal fusion improves robustness under transformations that
degrade one evidence channel, especially cropping, partial clips, and combined
transformations.

## Failure Boundary

Partial clips remain difficult because limited coverage can make legitimate
matches and hard negatives look similar. CineShield treats these as review-heavy
cases instead of sending them directly to response.

That behavior is deliberate: evidence systems should expose uncertainty rather
than over-claiming.

## Next Step

Replace synthetic vectors with real signals extracted from permitted test media:

- perceptual frame hashes
- audio fingerprints
- sampled scene embeddings
- OCR/subtitle text similarity
- metadata similarity

The dashboard can keep the same JSON interface once real extraction is added.

## Real-Media Smoke Test

`engine/real_media_benchmark.py` is the first real-media pipeline milestone.

It does not require FFmpeg. It uses OpenCV, NumPy, and the Python standard
library to generate permitted local media:

- 5 short synthetic videos
- matching WAV audio tracks
- transformed copies for crop, compression, resize, watermark, audio
  modification, partial clip, and combined transformations
- cross-work negatives
- one deliberate lookalike negative, `Project Rain`, that visually resembles
  `Project Monsoon` but has a different title/audio signature

It extracts actual fingerprints from the generated media files:

- frame-level visual fingerprints
- scene/color fingerprints
- temporal sequence fingerprints
- audio spectral fingerprints
- metadata similarity

Current smoke-test result:

- Baseline F1: 82%
- Adaptive CineShield F1: 100%
- Media pairs: 200
- Threshold: 90%
- Decision coverage: 72%
- Review rate: 28%
- Automated decision accuracy: 100%

This is intentionally presented as a smoke test, not the final benchmark. Its
purpose is to prove that the app has a working path from generated media files
to extracted fingerprints to measured matching results.
