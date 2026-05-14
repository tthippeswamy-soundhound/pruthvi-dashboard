from __future__ import annotations

import numpy as np
import librosa
from sklearn.cluster import AgglomerativeClustering


def extract_segment_embedding(audio: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    """Extract MFCC-based embedding for an audio segment."""
    start_sample = int(start * sr)
    end_sample = int(end * sr)
    segment = audio[start_sample:end_sample]

    if len(segment) < sr * 0.1:  # less than 100ms
        return np.zeros(40)

    mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=20)
    # Use mean and std of MFCCs as a simple speaker embedding
    embedding = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)])
    return embedding


def diarize_segments(
    file_path: str,
    segments: list[dict],
    num_speakers: int = 2,
) -> list[dict]:
    """
    Assign speaker labels to Whisper segments using MFCC clustering.

    Returns segments with a 'speaker' field: 'Agent' or 'User'.
    """
    if not segments:
        return []

    audio, sr = librosa.load(file_path, sr=16000, mono=True)

    embeddings = []
    valid_indices = []
    for i, seg in enumerate(segments):
        emb = extract_segment_embedding(audio, sr, seg["start"], seg["end"])
        if np.any(emb != 0):
            embeddings.append(emb)
            valid_indices.append(i)

    if len(embeddings) < 2:
        # Can't cluster with fewer than 2 segments, assign all to Agent
        for seg in segments:
            seg["speaker"] = "Agent"
        return segments

    embeddings = np.array(embeddings)

    # Cluster into num_speakers groups
    n_clusters = min(num_speakers, len(embeddings))
    clustering = AgglomerativeClustering(n_clusters=n_clusters)
    labels = clustering.fit_predict(embeddings)

    # The first speaker encountered is labeled "Agent"
    label_map = {}
    speaker_names = ["Agent", "User"]
    next_speaker = 0

    for label in labels:
        if label not in label_map:
            label_map[label] = speaker_names[next_speaker] if next_speaker < len(speaker_names) else f"Speaker {next_speaker + 1}"
            next_speaker += 1

    # Assign labels back to segments
    label_idx = 0
    for i, seg in enumerate(segments):
        if i in valid_indices:
            seg["speaker"] = label_map[labels[label_idx]]
            label_idx += 1
        else:
            seg["speaker"] = "Agent"

    return segments


def format_diarized_transcript(segments: list[dict]) -> str:
    """
    Format diarized segments into a readable transcript with speaker labels.

    Merges consecutive segments from the same speaker.
    """
    if not segments:
        return ""

    merged = []
    current_speaker = None
    current_text = []

    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        if not text:
            continue

        if speaker == current_speaker:
            current_text.append(text)
        else:
            if current_speaker is not None and current_text:
                merged.append(f"{current_speaker}: {' '.join(current_text)}")
            current_speaker = speaker
            current_text = [text]

    if current_speaker is not None and current_text:
        merged.append(f"{current_speaker}: {' '.join(current_text)}")

    return "\n".join(merged)
