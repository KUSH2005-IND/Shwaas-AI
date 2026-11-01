# Historical reports

Files already present here predate the audio-only pipeline refactor. They include
synthetic questionnaire experiments, differing partitions, manually entered plot
values and an infinite-threshold bug. They are retained for provenance, and should
not be used as the current model's performance evidence.

Generate new reports with:

    python -m src.evaluate --model artifacts/mel --features cache/mel_features.npz
    python -m src.plot --evaluation artifacts/mel/evaluation

Results are written below the selected model directory. This code refactor does
not establish new clinical performance numbers.
