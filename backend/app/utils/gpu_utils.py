"""
GPU utilities for KaizenLap ML processing.

Provides GPU-accelerated data processing with automatic fallback to CPU.
"""

import logging

log = logging.getLogger(__name__)

try:
    import cudf as pd
    import cupy as np
    from cuml.linear_model import LinearRegression
    GPU_AVAILABLE = True
    log.info("✅ GPU detected. Using cuDF, cuPy, and cuML.")
except ImportError as e:
    # In Cloud Run GPU jobs, GPU libraries MUST be available
    # This is a fatal error, not a fallback condition
    import os
    if os.getenv("USE_GPU", "false").lower() == "true":
        log.error(f"❌ FATAL: GPU libraries not found in GPU-enabled job. Error: {e}")
        raise RuntimeError("GPU libraries (cudf, cupy, cuml) not found. This job requires GPU environment.") from e
    # Fallback only for local development (USE_GPU=false)
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression
    GPU_AVAILABLE = False
    log.warning("⚠️ GPU not detected. Falling back to pandas, numpy, and scikit-learn. Performance will be slower.")


def is_gpu_available():
    """Checks if a GPU environment is available."""
    return GPU_AVAILABLE





