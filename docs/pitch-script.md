# CineShield 2.0 Pitch Script

## 0:00 to 0:30

The problem is not that one unauthorized copy appears after a film release.
The real problem is that transformed copies keep appearing as a network:
compressed videos, cropped clips, watermark variants, subtitle edits, partial
clips, and mirrors.

CineShield is a digital immune system for copyrighted video.

## 0:30 to 1:10

The core idea is Content DNA.

Instead of matching filenames or plain hashes, CineShield builds a multimodal
profile:

- visual fingerprint
- audio fingerprint
- scene sequence
- temporal profile
- OCR/text profile
- metadata profile
- semantic profile

This lets the system ask a better question: is this the same underlying work
despite transformations?

## 1:10 to 2:00

The technical contribution is adaptive evidence fusion.

A simple detector uses fixed weights. CineShield first estimates what changed.
If the candidate is cropped or watermarked, visual evidence is discounted and
audio plus scene continuity become more trusted. If audio is modified, visual,
scene, and temporal evidence carry more weight.

That is the difference between a generic AI wrapper and a real detection system.

## 2:00 to 3:00

In the demo, I register a permitted test reel and generate its Content DNA.
Then I run Find My Content on a local candidate corpus through the FastAPI
scanner.

The result is not just a table. CineShield extracts fingerprints, ranks
candidates, explains every match, and shows the signal profile behind each
decision.

For this prototype, the benchmark numbers are generated from a reproducible
synthetic Content DNA engine with a fixed seed and a content-level split. The
dashboard reports held-out test-work results, not manually typed claims. The
headline benchmark is still synthetic because it is larger and content-split.

I also built a smaller real-media smoke test. It generates permitted local
videos and audio, applies transformations, extracts real frame/audio fingerprints,
and shows that the pipeline can produce measured results end to end.

We also report decision coverage. On the synthetic benchmark, CineShield
automates 94% of match/reject decisions and routes 6% to human review. On the
real-media smoke test, it automates 72% and routes 28% to review because the
smoke test includes cross-work and lookalike hard negatives.

If asked where the AI is, the answer is precise: the current prototype uses
computer-vision fingerprinting, temporal pattern matching, adaptive evidence
fusion, and an explainable investigator layer over structured scan evidence. A
larger generative AI investigator can be added later, but the current build is
already a real verification pipeline.

If asked which model is used, be honest: this version does not claim a trained
deep-learning model. It uses an OpenCV/NumPy feature pipeline and deterministic
evidence-fusion model today, with a roadmap to CNN/CLIP/video embeddings later.

## 3:00 to 3:50

The threat graph reconstructs related source clusters.

Each edge has evidence behind it: same Content DNA, similar scene sequence, or
related distribution pattern. This helps the rights holder prioritize clusters
instead of chasing isolated URLs.

## 3:50 to 4:35

The investigator does not pretend to decide legality.

It summarizes structured evidence, marks uncertainty, and recommends review
priority. The system generates an evidence case only for authorized human review.
It says "high-confidence suspected unauthorized distribution", not "illegal".

External piracy-site screenshots should be described only as examples of the
problem ecosystem. The current scanner uses permitted local media and uploaded
candidate files.

## 4:35 to 5:00

The next engineering step is to replace generated media with permitted real
film/trailer clips, then run FFmpeg-generated transformations and a held-out
negative set.

The goal is to prove whether adaptive multimodal fusion improves robustness
over fixed-weight matching.
