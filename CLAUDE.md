# pyopenms-viewer

Fast mzML peak map viewer using NiceGUI, Datashader, and pyOpenMS. Designed to handle 50+ million peaks with smooth zooming and panning.

## Project Structure

- `pyopenms_viewer.py` - Main application source (single-file application)
- `pyproject.toml` - Project configuration and dependencies
- `.venv/` - Virtual environment (managed by uv)

## Tech Stack

- **UI Framework**: NiceGUI (web-based interface)
- **Rendering**: Datashader (server-side rendering of massive datasets)
- **MS Data**: pyOpenMS (mzML, FeatureXML, idXML file handling)
- **Visualization**: Plotly (interactive spectrum viewer)
- **Data**: pandas, numpy

## Development

### Setup
```bash
uv sync                    # Install dependencies
uv sync --extra dev        # Install with dev dependencies
uv sync --extra native     # Install with native window support
```

### Running
```bash
uv run pyopenms-viewer                              # Start with empty viewer
uv run pyopenms-viewer sample.mzML                  # Load mzML file
uv run pyopenms-viewer sample.mzML features.featureXML  # With features
```

### Testing & Linting
```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint code
uv run ruff format .       # Format code
```

## Code Style

- Line length: 120 characters
- Python 3.10+ (uses modern type hints)
- Ruff linter with rules: E, F, W, I, N, UP, B, C4
- BSD-3-Clause license

## Key Features

- Peak map visualization with datashader
- FeatureMap overlay (centroids, bounding boxes, convex hulls)
- idXML overlay (peptide identification precursor positions)
- Annotated MS2 spectrum viewer
- Total Ion Chromatogram (TIC) with clickable MS1 spectrum viewer
