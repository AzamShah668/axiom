"""Shared CLIP (open_clip ViT-B-16, LAION-2B) helpers: unit-norm image and text embeddings on CPU."""
import numpy as np

_M = {}
NAME, PRETRAINED = "ViT-B-16", "laion2b_s34b_b88k"


def _load():
    if not _M:
        import torch, open_clip
        torch.set_num_threads(4)
        m, _, pre = open_clip.create_model_and_transforms(NAME, pretrained=PRETRAINED)
        m.eval()
        _M.update(model=m, pre=pre, tok=open_clip.get_tokenizer(NAME), torch=torch)
    return _M


def embed_images(images, batch=32):
    """images: list of RGB numpy arrays or PIL images -> (n, 512) float32, unit norm."""
    from PIL import Image
    M = _load()
    out = []
    with M["torch"].no_grad():
        for i in range(0, len(images), batch):
            x = M["torch"].stack([M["pre"](im if isinstance(im, Image.Image) else Image.fromarray(im)) for im in images[i:i + batch]])
            f = M["model"].encode_image(x).float()
            out.append((f / f.norm(dim=-1, keepdim=True)).numpy())
    return np.concatenate(out) if out else np.zeros((0, 512), np.float32)


def embed_texts(texts, batch=64):
    M = _load()
    out = []
    with M["torch"].no_grad():
        for i in range(0, len(texts), batch):
            f = M["model"].encode_text(M["tok"](texts[i:i + batch])).float()
            out.append((f / f.norm(dim=-1, keepdim=True)).numpy())
    return np.concatenate(out) if out else np.zeros((0, 512), np.float32)
