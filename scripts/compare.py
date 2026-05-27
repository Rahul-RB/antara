#!/usr/bin/env python3
"""
Usage: python3 compare.py <image1> <image2>

Compares the faces in two images and prints a similarity score.
"""

import sys


def load_image(path: str):
    import cv2
    import numpy as np
    import pillow_heif
    from PIL import Image

    img = cv2.imread(path)
    if img is not None:
        return img
    try:
        pillow_heif.register_heif_opener()
        pil_img = Image.open(path).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def get_embeddings(path: str) -> list[list[float]]:
    from insightface.app import FaceAnalysis

    img = load_image(path)
    if img is None:
        print(f"Error: could not read image: {path}", file=sys.stderr)
        sys.exit(1)

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    faces = app.get(img)
    return [face.normed_embedding.tolist() for face in faces]


def best_similarity(a: list[list[float]], b: list[list[float]]) -> float:
    import numpy as np

    best = -1.0
    for ea in a:
        for eb in b:
            sim = float(np.dot(np.array(ea), np.array(eb)))
            if sim > best:
                best = sim
    return best


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 compare.py <image1> <image2>", file=sys.stderr)
        sys.exit(1)

    path1, path2 = sys.argv[1], sys.argv[2]

    print("Loading model...")
    emb1 = get_embeddings(path1)
    emb2 = get_embeddings(path2)

    if not emb1:
        print(f"No face detected in: {path1}")
        sys.exit(1)
    if not emb2:
        print(f"No face detected in: {path2}")
        sys.exit(1)

    print(f"Faces detected — image 1: {len(emb1)}, image 2: {len(emb2)}")

    sim = best_similarity(emb1, emb2)
    confidence = (sim + 1) / 2 * 100

    print(f"Similarity : {sim:.4f}")
    print(f"Confidence : {confidence:.1f}%")

    if sim >= 0.4:
        print("Verdict    : likely the same person")
    else:
        print("Verdict    : likely different people")


if __name__ == "__main__":
    main()
