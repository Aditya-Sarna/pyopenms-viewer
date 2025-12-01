# pyopenms-viewer

Fast mzML peak map viewer using NiceGUI, Datashader, and pyOpenMS.

Designed to handle **50+ million peaks** with smooth zooming and panning using server-side rendering.

## Features

- **Peak Map Visualization** - Datashader-powered rendering for massive datasets
- **FeatureMap Overlay** - Display centroids, bounding boxes, and convex hulls
- **idXML Overlay** - Show peptide identification precursor positions
- **MS2 Spectrum Viewer** - Annotated spectrum viewer for peptide identifications
- **TIC Display** - Total Ion Chromatogram with clickable MS1 spectrum viewer

## Installation

Requires Python 3.10+

```bash
# Using uv (recommended)
uv sync

# With native window support
uv sync --extra native

# With development dependencies
uv sync --extra dev
```

## Usage

```bash
# Start with empty viewer
mzml-viewer

# Load an mzML file
mzml-viewer sample.mzML

# Load mzML with feature overlay
mzml-viewer sample.mzML features.featureXML

# Load mzML with peptide identifications
mzml-viewer sample.mzML ids.idXML

# Load all three file types
mzml-viewer sample.mzML features.featureXML ids.idXML
```

## Development

```bash
# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .
```

## License

BSD-3-Clause
