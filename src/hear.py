"""Optional frozen HeAR encoder. Never downloads during normal API startup."""
from __future__ import annotations
import numpy as np
from src.audio import activity_windows

MODEL_ID = "google/hear-pytorch"
FRONTEND_COMMIT = "36bbb90879545a2f1106668048b1a12a61ff2a0d"

class HeAREncoder:
    def __init__(self, revision=None, allow_download=False, device="cpu"):
        try:
            import torch
            from transformers import AutoModel
        except ImportError as error:
            raise ImportError("Install requirements-hear.txt and CPU PyTorch; see README.") from error
        try:
            self.model = AutoModel.from_pretrained(
                MODEL_ID, revision=revision, local_files_only=not allow_download,
                trust_remote_code=False,
            ).to(device).eval()
        except Exception as error:
            raise RuntimeError(
                "HeAR weights unavailable. Accept the Google HeAR terms on Hugging Face, "
                "log in, then run feature extraction with --allow-download. "
                "The API only uses cached weights."
            ) from error
        self.revision = getattr(self.model.config, "_commit_hash", None) or revision
        if not self.revision:
            raise RuntimeError("Cannot identify the HeAR revision; use a pinned model commit.")
        self.device = torch.device(device)
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)

    def encode(self, y: np.ndarray) -> np.ndarray:
        import torch
        from src.vendor.hear_audio_utils import preprocess_audio
        windows = activity_windows(y, seconds=2, stride=1)
        # Google's frontend min/max is batch-wide. Preprocess one clip at a time
        # so a recording's embedding cannot depend on other batch members.
        images = torch.cat([
            preprocess_audio(torch.from_numpy(window.copy()[None])) for window in windows
        ]).to(self.device)
        with torch.inference_mode():
            batches = [self.model(batch, return_dict=True).pooler_output
                       for batch in images.split(4)]
            if any(batch is None for batch in batches):
                raise RuntimeError("HeAR did not return pooler_output.")
            embeddings = torch.cat(batches)
        if embeddings is None or tuple(embeddings.shape) != (len(windows), 512):
            raise RuntimeError("Unexpected HeAR output; expected [windows, 512] pooler_output.")
        vector = embeddings.float().mean(dim=0).cpu().numpy()
        if not np.isfinite(vector).all():
            raise RuntimeError("HeAR returned non-finite embeddings.")
        return vector.astype(np.float32)
