"""Procedural audio generator creating 16-bit 44.1kHz mono WAV sound effects for chess."""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100


def save_wav(filepath: Path, samples: list[float]) -> None:
    """Save normalized float samples (-1.0 to 1.0) to 16-bit mono WAV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filepath), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)

        # 16-bit signed PCM
        raw_bytes = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            int_val = int(clamped * 32767)
            raw_bytes.extend(struct.pack("<h", int_val))
        wav_file.writeframes(raw_bytes)


def make_click(freq: float, duration_s: float, decay_rate: float) -> list[float]:
    """Generates a crisp percussive piece-placement click."""
    num_samples = int(SAMPLE_RATE * duration_s)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        envelope = math.exp(-decay_rate * t)
        # Pitch drop over time for wooden impact realism
        curr_freq = freq * (1.0 - 0.4 * (i / num_samples))
        val = math.sin(2 * math.pi * curr_freq * t) * envelope
        # Add slight resonant body
        val += 0.3 * math.sin(2 * math.pi * (curr_freq * 0.5) * t) * envelope
        samples.append(val * 0.8)
    return samples


def generate_move_sound(output_dir: Path) -> None:
    """Crisp, soft wood move tap."""
    samples = make_click(freq=750, duration_s=0.08, decay_rate=55.0)
    save_wav(output_dir / "move.wav", samples)


def generate_capture_sound(output_dir: Path) -> None:
    """Authoritative heavier piece capture knock."""
    num_samples = int(SAMPLE_RATE * 0.12)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-40.0 * t)
        val = (
            math.sin(2 * math.pi * 500 * t) * 0.7
            + math.sin(2 * math.pi * 320 * t) * 0.5
            + math.sin(2 * math.pi * 850 * t) * 0.3
        ) * env
        samples.append(val * 0.85)
    save_wav(output_dir / "capture.wav", samples)


def generate_check_sound(output_dir: Path) -> None:
    """Bright two-tone chime for check alert."""
    duration_s = 0.35
    num_samples = int(SAMPLE_RATE * duration_s)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-10.0 * t)
        # Chime: A5 (880Hz) + E6 (1318Hz)
        val = (math.sin(2 * math.pi * 880 * t) * 0.6 + math.sin(2 * math.pi * 1318 * t) * 0.4) * env
        samples.append(val * 0.75)
    save_wav(output_dir / "check.wav", samples)


def generate_castle_sound(output_dir: Path) -> None:
    """Two fast sequential taps representing king and rook."""
    tap1 = make_click(freq=700, duration_s=0.07, decay_rate=50.0)
    gap = [0.0] * int(SAMPLE_RATE * 0.04)
    tap2 = make_click(freq=620, duration_s=0.09, decay_rate=45.0)
    samples = tap1 + gap + tap2
    save_wav(output_dir / "castle.wav", samples)


def generate_promotion_sound(output_dir: Path) -> None:
    """Ascending cheerful triad chime."""
    duration_s = 0.45
    num_samples = int(SAMPLE_RATE * duration_s)
    samples = [0.0] * num_samples
    notes = [
        (523.25, 0.0),  # C5
        (659.25, 0.08),  # E5
        (783.99, 0.16),  # G5
        (1046.50, 0.24),  # C6
    ]
    for freq, start_t in notes:
        start_idx = int(start_t * SAMPLE_RATE)
        for i in range(start_idx, num_samples):
            t = (i - start_idx) / SAMPLE_RATE
            env = math.exp(-12.0 * t)
            samples[i] += math.sin(2 * math.pi * freq * t) * env * 0.35
    save_wav(output_dir / "promotion.wav", samples)


def generate_game_start_sound(output_dir: Path) -> None:
    """Warm opening resonant bell."""
    duration_s = 0.45
    num_samples = int(SAMPLE_RATE * duration_s)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-7.0 * t)
        val = (
            math.sin(2 * math.pi * 440 * t) * 0.6
            + math.sin(2 * math.pi * 554.37 * t) * 0.3
            + math.sin(2 * math.pi * 659.25 * t) * 0.2
        ) * env
        samples.append(val * 0.7)
    save_wav(output_dir / "game_start.wav", samples)


def generate_game_end_sound(output_dir: Path) -> None:
    """Gentle concluding chord."""
    duration_s = 0.55
    num_samples = int(SAMPLE_RATE * duration_s)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-5.5 * t)
        val = (
            math.sin(2 * math.pi * 261.63 * t) * 0.5
            + math.sin(2 * math.pi * 329.63 * t) * 0.3
            + math.sin(2 * math.pi * 392.00 * t) * 0.3
            + math.sin(2 * math.pi * 523.25 * t) * 0.2
        ) * env
        samples.append(val * 0.7)
    save_wav(output_dir / "game_end.wav", samples)


def generate_all_sounds() -> None:
    target_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
    target_dir.mkdir(parents=True, exist_ok=True)
    generate_move_sound(target_dir)
    generate_capture_sound(target_dir)
    generate_check_sound(target_dir)
    generate_castle_sound(target_dir)
    generate_promotion_sound(target_dir)
    generate_game_start_sound(target_dir)
    generate_game_end_sound(target_dir)
    print(f"Generated 7 WAV sounds in {target_dir}")


if __name__ == "__main__":
    generate_all_sounds()
