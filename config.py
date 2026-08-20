from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_DIR / "diktat.txt"

# Bei jedem Release manuell mit dem neuen Git-Tag synchron halten (siehe update_check.py)
VERSION = "0.6.0"

# Whisper
MODEL_SIZE = "small"
LANGUAGE = "de"
COMPUTE_TYPE = "int8"
CPU_THREADS = 8

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 800  # ~50ms bei 16kHz

# Pausenerkennung / Chunking
SILENCE_THRESHOLD_RMS = 0.015
SILENCE_DURATION_MS = 700
MAX_CHUNK_DURATION_S = 18
MIN_CHUNK_DURATION_MS = 300
