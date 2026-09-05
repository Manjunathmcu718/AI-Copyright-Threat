# CineShield Presentation Q&A

## Where exactly is the AI?

The current prototype uses AI/ML-style multimedia intelligence, not a fake
chatbot. It extracts video fingerprints using computer vision, compares visual,
scene, temporal, duration, and coverage signals, then uses adaptive evidence
fusion to classify each candidate as Match, Review, or No match.

The investigator layer reads the structured scan evidence and produces:

- priority
- strongest and weakest signals
- uncertainty boundary
- audit trail
- human-review recommendation

A future LLM layer can summarize larger threat graphs, but the current build is
already a working verification and evidence-fusion pipeline.

## What AI/ML model are you using?

The current version is not claiming a trained deep-learning model yet. It uses a
computer-vision feature pipeline and deterministic evidence-fusion model:

1. sample frames from the protected video and candidate video
2. resize and normalize sampled frames
3. build visual fingerprints
4. compare scene order, temporal pattern, duration, and coverage
5. adapt the evidence weights when a signal becomes weak
6. produce Match / Review / No match with reasons

This is the implemented intelligence layer. A later version can replace or
extend the handcrafted features with CNN/CLIP/video embeddings and use an LLM to
summarize larger threat graphs.

## How exactly is Content DNA generated?

```text
Video
  -> frame/audio sampling
  -> visual feature extraction
  -> scene and temporal profile
  -> metadata and coverage signals
  -> feature normalization
  -> adaptive evidence fusion
  -> Content DNA similarity score
```

In the present backend, the working scan uses OpenCV to sample frames, converts
them into normalized visual vectors, compares them with cosine similarity, checks
scene order and temporal movement, then computes a confidence score.

## Are we crawling piracy websites?

No. The current project scans local uploaded candidate videos and controlled
demo media. Production discovery should be added through lawful connectors:
rights-holder URL queues, public/search APIs allowed by terms, platform partner
feeds, and authorized monitoring sources.

MovieRulz, iBOMMA, NetMirror, and similar screenshots should be presented only
as examples of the problem ecosystem, not as current project data sources.

## What is the main technical problem?

Can the system identify the same underlying video after transformations such as
compression, cropping, watermarking, resolution change, subtitle edits, partial
clips, or re-uploads?

## Why is this suitable as a major project?

It combines multimedia computing, computer vision, backend engineering,
evidence scoring, explainability, and responsible human-in-the-loop design.
