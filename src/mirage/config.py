PARAM_INFO = {
    "RADI": "Smoothing radius. Lower values preserve subtle signatures.",
    "GTHR": "Detection strictness. Higher values reduce weak edges.",
    "LTHR": "Minimum signature length in pixels.",
    "FTHR": "Output simplification tolerance.",
    "ATHR": "Maximum angular mismatch when linking signatures.",
    "DTHR": "Maximum linking gap in pixels.",
}


PRESETS = {
    "Structural continuity": {
        "RADI": 3,
        "GTHR": 66,
        "LTHR": 28,
        "FTHR": 4,
        "ATHR": 16,
        "DTHR": 12,
        "summary": "Best when you want cleaner natural signatures and want to avoid outlining every possible edge.",
    },
    "Geo-arch balance": {
        "RADI": 4,
        "GTHR": 58,
        "LTHR": 22,
        "FTHR": 3,
        "ATHR": 18,
        "DTHR": 14,
        "summary": "Good starting point when geometric expression matters and you still want a controlled result.",
    },
    "Anthropogenic detail": {
        "RADI": 4,
        "GTHR": 50,
        "LTHR": 18,
        "FTHR": 2,
        "ATHR": 22,
        "DTHR": 18,
        "summary": "Keeps more weak, short, and irregular responses when subtle evidence is important.",
    },
    "Magnetometry": {
        "RADI": 3,
        "GTHR": 60,
        "LTHR": 20,
        "FTHR": 3,
        "ATHR": 14,
        "DTHR": 10,
        "summary": "Optimized for high-resolution magnetometry to delineate dykes and structural boundaries.",
    },
    "Gravimetry": {
        "RADI": 5,
        "GTHR": 55,
        "LTHR": 25,
        "FTHR": 4,
        "ATHR": 16,
        "DTHR": 12,
        "summary": "Optimized for regional gravity anomaly maps to define deep structural basements and domains.",
    },
}


FEATURE_MODES = {
    "Geological signature": {
        "value": "signature",
        "summary": "Preferred orientations from tectonic stress, fractal/self-similar behavior, and resilience to high natural noise (topography and vegetation).",
    },
    "Archaeological signature": {
        "value": "geometry",
        "summary": "Anthropogenic/localized patterns with less directional preference, preserving circular, rectilinear, and pipe-like geometry under extreme micro-relief disturbances.",
    },
    "Geophysics Potential Fields": {
        "value": "geophysics",
        "summary": "Geological structures (faults, shear zones, dykes, contacts) extracted from gravity and magnetic data using local quadratic curvature and multi-filter fusion.",
    },
}
