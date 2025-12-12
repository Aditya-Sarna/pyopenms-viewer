# Plan: Out-of-Core Data Caching for pyopenms-viewer

## Overview

This plan describes how to implement disk-based caching for out-of-memory rendering and display, enabling the viewer to handle datasets larger than available RAM.

## Current Architecture

### Data in Memory
- **`state.df`**: Main peak DataFrame (~2GB for 50M peaks) with columns: `rt`, `mz`, `intensity`, `log_intensity`, `cv`
- **`state.im_df`**: Ion mobility DataFrame with: `mz`, `im`, `intensity`, `log_intensity`
- **`state.exp`**: pyOpenMS MSExperiment C++ object (~500MB)
- **`state.faims_data`**: Dictionary of per-CV DataFrames (views into `state.df`)

### Data Flow
1. Load mzML → Extract peaks → Build DataFrame in RAM
2. View change → Filter DataFrame by bounds → Datashader aggregation → PNG

## Proposed Solution: Unified DuckDB Interface

### Design Decision: Single Query Interface for Both Modes

Both in-memory and out-of-core modes use DuckDB for querying:

| Mode | Data Storage | Query Method |
|------|--------------|--------------|
| **In-memory** | DuckDB registers pandas DataFrame (zero-copy) | SQL query |
| **Out-of-core** | DuckDB reads from Parquet file | SQL query |

**Benefits of unified interface:**
- Single code path for queries (easier to maintain and test)
- DuckDB's `register()` provides zero-copy access to pandas DataFrames
- Identical behavior between modes
- No branching logic in renderers

### Why DuckDB + Parquet?

| Option | Pros | Cons |
|--------|------|------|
| **HDF5 (PyTables)** | Fast, mature, good compression | Requires pytables dependency, API less pandas-friendly |
| **SQLite** | Built-in, familiar | Slow for range queries on large datasets |
| **Parquet + DuckDB** | Zero-copy queries, columnar, excellent compression, pandas-native | Requires duckdb dependency |
| **Memory-mapped NumPy** | Fastest raw access | No compression, manual indexing needed |

---

## Implementation Plan

### Phase 1: Configuration and CLI Support

#### 1.1 Add Configuration Options

**File: `pyopenms_viewer/core/config.py`**

```python
# Add to DEFAULTS dict
"out_of_core": False,              # Enable disk-based caching
"cache_dir": None,                 # Cache directory (None = temp dir)
"cache_compression": "zstd",       # Compression: zstd, snappy, gzip, none
```

#### 1.2 CLI Arguments

**File: `pyopenms_viewer/cli.py`**

```python
@click.option("--out-of-core/--in-memory", default=False,
              help="Use disk-based caching for large datasets")
@click.option("--cache-dir", type=click.Path(), default=None,
              help="Directory for cache files (default: temp)")
```

#### 1.3 GUI Config Toggle

**File: `pyopenms_viewer/app.py`** - Add to existing `show_panel_settings()` dialog

Add a "Performance" section to the existing panel settings dialog:

```python
def show_panel_settings():
    with ui.dialog() as dialog, ui.card().classes("min-w-[400px]"):
        ui.label("Panel Configuration").classes("text-lg font-bold mb-2")

        # ... existing panel visibility and order sections ...

        ui.separator().classes("my-2")

        # Performance section (NEW)
        ui.label("Performance").classes("text-sm font-semibold text-gray-400 mt-2")

        with ui.row().classes("w-full items-center gap-2"):
            ui.icon("memory").classes("text-gray-400")
            ui.label("Out-of-core mode").classes("flex-grow text-sm")
            ooc_switch = ui.switch(value=state.out_of_core).props("dense")

        ui.label("Uses disk caching for large datasets (reduces RAM usage)").classes(
            "text-xs text-gray-500 ml-6"
        )

        # Cache info (shown when out-of-core is enabled)
        cache_info = ui.label("").classes("text-xs text-gray-400 ml-6")

        def update_cache_info():
            if state.data_manager:
                size_mb = state.data_manager.get_cache_size_mb()
                cache_info.set_text(f"Cache: {size_mb:.1f} MB")
            else:
                cache_info.set_text("")

        update_cache_info()
```

---

### Phase 2: Unified Data Manager

#### 2.1 Create DataManager Class

**File: `pyopenms_viewer/core/data_manager.py`**

```python
"""Unified data manager using DuckDB for both in-memory and out-of-core modes."""

from pathlib import Path
import tempfile
import hashlib
from typing import TYPE_CHECKING

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from pyopenms_viewer.core.state import ViewerState


class DataManager:
    """Manages peak data access via DuckDB for both in-memory and out-of-core modes.

    In-memory mode: Registers pandas DataFrames directly (zero-copy)
    Out-of-core mode: Writes Parquet files, queries via DuckDB
    """

    def __init__(self, out_of_core: bool = False, cache_dir: Path | None = None,
                 compression: str = "zstd"):
        self.out_of_core = out_of_core
        self.cache_dir = cache_dir or Path(tempfile.mkdtemp(prefix="pyopenms_viewer_"))
        self.compression = compression
        self.conn = duckdb.connect(":memory:")

        self._peaks_registered = False
        self._im_peaks_registered = False
        self._source_file: str | None = None

        # Keep DataFrame references for in-memory mode
        self._df: pd.DataFrame | None = None
        self._im_df: pd.DataFrame | None = None

    def _get_cache_key(self, filepath: str) -> str:
        """Generate cache key from file path and mtime."""
        path = Path(filepath)
        if path.exists():
            stat = path.stat()
            key_str = f"{filepath}:{stat.st_mtime}:{stat.st_size}"
        else:
            key_str = filepath
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def register_peaks(self, df: pd.DataFrame, source_file: str) -> pd.DataFrame | None:
        """Register peak DataFrame with DuckDB.

        In-memory: Registers DataFrame directly (zero-copy)
        Out-of-core: Writes to Parquet, registers as view, returns None to signal freeing

        Returns:
            DataFrame to keep in memory, or None if data was written to disk
        """
        self._source_file = source_file

        # Drop existing view if present
        if self._peaks_registered:
            self.conn.execute("DROP VIEW IF EXISTS peaks")

        if self.out_of_core:
            # Write to Parquet
            cache_key = self._get_cache_key(source_file)
            cache_path = self.cache_dir / f"peaks_{cache_key}.parquet"

            pq.write_table(
                pa.Table.from_pandas(df),
                cache_path,
                compression=self.compression,
                row_group_size=1_000_000,
            )

            # Register Parquet as view
            self.conn.execute(f"""
                CREATE VIEW peaks AS
                SELECT * FROM read_parquet('{cache_path}')
            """)
            self._peaks_registered = True
            self._df = None
            return None  # Signal to free DataFrame
        else:
            # Register DataFrame directly (zero-copy)
            self.conn.register("peaks_table", df)
            self.conn.execute("CREATE VIEW peaks AS SELECT * FROM peaks_table")
            self._peaks_registered = True
            self._df = df
            return df  # Keep in memory

    def register_im_peaks(self, df: pd.DataFrame, source_file: str) -> pd.DataFrame | None:
        """Register ion mobility DataFrame with DuckDB."""
        # Drop existing view if present
        if self._im_peaks_registered:
            self.conn.execute("DROP VIEW IF EXISTS im_peaks")

        if self.out_of_core:
            cache_key = self._get_cache_key(source_file)
            cache_path = self.cache_dir / f"im_peaks_{cache_key}.parquet"

            pq.write_table(
                pa.Table.from_pandas(df),
                cache_path,
                compression=self.compression,
                row_group_size=500_000,
            )

            self.conn.execute(f"""
                CREATE VIEW im_peaks AS
                SELECT * FROM read_parquet('{cache_path}')
            """)
            self._im_peaks_registered = True
            self._im_df = None
            return None
        else:
            self.conn.register("im_peaks_table", df)
            self.conn.execute("CREATE VIEW im_peaks AS SELECT * FROM im_peaks_table")
            self._im_peaks_registered = True
            self._im_df = df
            return df

    def query_peaks_in_view(
        self,
        rt_min: float, rt_max: float,
        mz_min: float, mz_max: float,
        cv: float | None = None
    ) -> pd.DataFrame:
        """Query peaks within view bounds."""
        if not self._peaks_registered:
            return pd.DataFrame()

        query = """
            SELECT rt, mz, intensity, log_intensity
            FROM peaks
            WHERE rt >= ? AND rt <= ?
              AND mz >= ? AND mz <= ?
        """
        params = [rt_min, rt_max, mz_min, mz_max]

        if cv is not None:
            query += " AND cv = ?"
            params.append(cv)

        return self.conn.execute(query, params).fetchdf()

    def query_im_peaks_in_view(
        self,
        mz_min: float, mz_max: float,
        im_min: float, im_max: float
    ) -> pd.DataFrame:
        """Query ion mobility peaks within view bounds."""
        if not self._im_peaks_registered:
            return pd.DataFrame()

        query = """
            SELECT mz, im, intensity, log_intensity
            FROM im_peaks
            WHERE mz >= ? AND mz <= ?
              AND im >= ? AND im <= ?
        """
        return self.conn.execute(query, [mz_min, mz_max, im_min, im_max]).fetchdf()

    def query_peaks_for_minimap(self, sample_rate: int = 100) -> pd.DataFrame:
        """Query downsampled peaks for minimap rendering."""
        if not self._peaks_registered:
            return pd.DataFrame()

        if self.out_of_core:
            # Sample every Nth row for out-of-core
            return self.conn.execute(f"""
                SELECT rt, mz, log_intensity
                FROM peaks
                WHERE rowid % {sample_rate} = 0
            """).fetchdf()
        else:
            # In-memory: return full DataFrame (minimap uses datashader anyway)
            return self._df

    def get_bounds(self) -> dict[str, float]:
        """Get data bounds without loading all data."""
        if not self._peaks_registered:
            return {"rt_min": 0, "rt_max": 0, "mz_min": 0, "mz_max": 0}

        result = self.conn.execute("""
            SELECT
                MIN(rt) as rt_min, MAX(rt) as rt_max,
                MIN(mz) as mz_min, MAX(mz) as mz_max
            FROM peaks
        """).fetchone()

        return {
            "rt_min": result[0] or 0,
            "rt_max": result[1] or 0,
            "mz_min": result[2] or 0,
            "mz_max": result[3] or 0,
        }

    def get_im_bounds(self) -> dict[str, float]:
        """Get ion mobility data bounds."""
        if not self._im_peaks_registered:
            return {"mz_min": 0, "mz_max": 0, "im_min": 0, "im_max": 0}

        result = self.conn.execute("""
            SELECT
                MIN(mz) as mz_min, MAX(mz) as mz_max,
                MIN(im) as im_min, MAX(im) as im_max
            FROM im_peaks
        """).fetchone()

        return {
            "mz_min": result[0] or 0,
            "mz_max": result[1] or 0,
            "im_min": result[2] or 0,
            "im_max": result[3] or 0,
        }

    def get_peak_count(self) -> int:
        """Get total peak count."""
        if not self._peaks_registered:
            return 0
        return self.conn.execute("SELECT COUNT(*) FROM peaks").fetchone()[0]

    def get_cache_size_mb(self) -> float:
        """Get total cache size in MB."""
        if not self.out_of_core:
            return 0.0

        total = 0
        for f in self.cache_dir.glob("*.parquet"):
            total += f.stat().st_size
        return total / (1024 * 1024)

    def clear_cache(self):
        """Clear all cached Parquet files."""
        for f in self.cache_dir.glob("*.parquet"):
            f.unlink()

        # Reset registration state
        if self._peaks_registered:
            self.conn.execute("DROP VIEW IF EXISTS peaks")
            self._peaks_registered = False
        if self._im_peaks_registered:
            self.conn.execute("DROP VIEW IF EXISTS im_peaks")
            self._im_peaks_registered = False

    def cleanup(self):
        """Clean up resources."""
        self.conn.close()
```

---

### Phase 3: Integrate with ViewerState

#### 3.1 Modify ViewerState

**File: `pyopenms_viewer/core/state.py`**

```python
from pyopenms_viewer.core.data_manager import DataManager

class ViewerState:
    def __init__(self):
        # ... existing init ...

        # Data manager (unified DuckDB interface)
        self.out_of_core: bool = False
        self.data_manager: DataManager | None = None

        # DataFrame references (may be None in out-of-core mode)
        self.df: pd.DataFrame | None = None
        self.im_df: pd.DataFrame | None = None

    def init_data_manager(self, out_of_core: bool = False, cache_dir: Path | None = None):
        """Initialize the data manager."""
        self.out_of_core = out_of_core
        self.data_manager = DataManager(out_of_core=out_of_core, cache_dir=cache_dir)

    def get_peaks_in_view(self) -> pd.DataFrame:
        """Get peaks in current view via DuckDB."""
        if self.data_manager is None:
            # Fallback for legacy/tests
            if self.df is None:
                return pd.DataFrame()
            mask = (
                (self.df["rt"] >= self.view_rt_min) &
                (self.df["rt"] <= self.view_rt_max) &
                (self.df["mz"] >= self.view_mz_min) &
                (self.df["mz"] <= self.view_mz_max)
            )
            return self.df[mask]

        return self.data_manager.query_peaks_in_view(
            self.view_rt_min, self.view_rt_max,
            self.view_mz_min, self.view_mz_max,
            self.current_cv if self.has_faims else None
        )

    def get_im_peaks_in_view(self) -> pd.DataFrame:
        """Get ion mobility peaks in current view via DuckDB."""
        if self.data_manager is None:
            if self.im_df is None:
                return pd.DataFrame()
            mask = (
                (self.im_df["mz"] >= self.view_mz_min) &
                (self.im_df["mz"] <= self.view_mz_max) &
                (self.im_df["im"] >= self.view_im_min) &
                (self.im_df["im"] <= self.view_im_max)
            )
            return self.im_df[mask]

        return self.data_manager.query_im_peaks_in_view(
            self.view_mz_min, self.view_mz_max,
            self.view_im_min, self.view_im_max
        )
```

---

### Phase 4: Modify Loaders

#### 4.1 Update MzMLLoader

**File: `pyopenms_viewer/loaders/mzml_loader.py`**

```python
class MzMLLoader:
    def process(self, progress_callback=None):
        # ... existing peak extraction to build df ...

        # Register with data manager
        if self.state.data_manager:
            self.state.df = self.state.data_manager.register_peaks(df, self.filepath)

            # Get bounds from data manager
            bounds = self.state.data_manager.get_bounds()
            self.state.rt_min = bounds["rt_min"]
            self.state.rt_max = bounds["rt_max"]
            self.state.mz_min = bounds["mz_min"]
            self.state.mz_max = bounds["mz_max"]

            if progress_callback:
                progress_callback(0.88, "Registered peaks with data manager")
        else:
            # Legacy: keep DataFrame in state
            self.state.df = df

        # ... rest of processing ...
```

Similar changes for ion mobility data in `ion_mobility_loader.py`.

---

### Phase 5: Modify Renderers

#### 5.1 Update PeakMapRenderer

**File: `pyopenms_viewer/rendering/peak_map_renderer.py`**

Renderers use `state.get_peaks_in_view()` which now routes through DuckDB. Minimal changes needed:

```python
def render(self, state: ViewerState, fast: bool = False) -> str:
    # Get view data (unified DuckDB query for both modes)
    view_df = state.get_peaks_in_view()

    if view_df.empty:
        return self._render_empty()

    # ... rest of rendering unchanged ...
```

#### 5.2 Update MinimapRenderer

**File: `pyopenms_viewer/rendering/minimap_renderer.py`**

```python
def render(self, state: ViewerState) -> str:
    # Get data for minimap
    if state.data_manager:
        minimap_df = state.data_manager.query_peaks_for_minimap()
    else:
        minimap_df = state.df

    if minimap_df is None or minimap_df.empty:
        return self._render_empty()

    # ... rest of minimap rendering ...
```

---

### Phase 6: GUI Integration

#### 6.1 Add to Existing Settings Dialog

**File: `pyopenms_viewer/app.py`** - Modify `show_panel_settings()` function

```python
def show_panel_settings():
    with ui.dialog() as dialog, ui.card().classes("min-w-[400px]"):
        ui.label("Panel Configuration").classes("text-lg font-bold mb-2")

        # ... existing panel visibility section ...

        ui.separator().classes("my-2")

        # ... existing panel order section ...

        ui.separator().classes("my-2")

        # NEW: Performance section
        ui.label("Performance").classes("text-sm font-semibold text-gray-400 mt-2")
        ui.label("Memory optimization for large datasets").classes("text-xs text-gray-500 mb-2")

        with ui.row().classes("w-full items-center gap-2"):
            ui.icon("storage").classes("text-gray-400 text-sm")
            ui.label("Out-of-core mode").classes("flex-grow text-sm")
            ooc_switch = ui.switch(value=state.out_of_core).props("dense")

        with ui.row().classes("ml-6"):
            ui.label("Caches data to disk, reducing RAM usage").classes("text-xs text-gray-500")

        # Cache status
        def get_cache_status():
            if state.data_manager and state.out_of_core:
                size = state.data_manager.get_cache_size_mb()
                return f"Cache: {size:.1f} MB"
            return "Cache: inactive"

        cache_label = ui.label(get_cache_status()).classes("text-xs text-gray-400 ml-6")

        # Store new setting for apply
        new_ooc_value = [state.out_of_core]  # Use list for mutability in closure

        def on_ooc_change(e):
            new_ooc_value[0] = e.value

        ooc_switch.on("change", on_ooc_change)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            def apply_settings():
                # ... existing panel order/visibility apply ...

                # Apply out-of-core setting
                if new_ooc_value[0] != state.out_of_core:
                    state.out_of_core = new_ooc_value[0]
                    if state.data_manager:
                        # Reinitialize data manager with new setting
                        state.init_data_manager(out_of_core=state.out_of_core)
                    ui.notify(
                        "Out-of-core mode " + ("enabled" if state.out_of_core else "disabled") +
                        ". Reload data to apply.",
                        type="info"
                    )

                dialog.close()
                ui.notify("Settings updated", type="positive")

            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Apply", on_click=apply_settings).props("color=primary")

    dialog.open()
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `core/config.py` | Add `out_of_core`, `cache_dir` defaults |
| `core/state.py` | Add `data_manager`, `init_data_manager()`, update `get_peaks_in_view()` |
| `core/data_manager.py` | **NEW** - Unified DuckDB interface |
| `cli.py` | Add `--out-of-core` and `--cache-dir` options |
| `loaders/mzml_loader.py` | Register DataFrame with data manager |
| `loaders/ion_mobility_loader.py` | Register IM DataFrame with data manager |
| `rendering/minimap_renderer.py` | Use data manager for minimap query |
| `app.py` | Add Performance section to settings dialog, init data manager |
| `pyproject.toml` | Add `duckdb`, `pyarrow` dependencies |

---

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing ...
    "duckdb>=1.0.0",
    "pyarrow>=15.0.0",
]
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ViewerState                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    DataManager                           │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │              DuckDB Connection                   │    │    │
│  │  │                                                  │    │    │
│  │  │  In-Memory Mode:                                │    │    │
│  │  │    pandas DataFrame → register() → VIEW peaks   │    │    │
│  │  │                                                  │    │    │
│  │  │  Out-of-Core Mode:                              │    │    │
│  │  │    DataFrame → Parquet → VIEW peaks             │    │    │
│  │  │                     ↓                           │    │    │
│  │  │              read_parquet()                     │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │                         ↓                                │    │
│  │              query_peaks_in_view()                      │    │
│  │                         ↓                                │    │
│  │                  pd.DataFrame                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│                  get_peaks_in_view()                            │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                      Renderers (unchanged)
                             ↓
                      Datashader → PNG
```

---

## Performance Expectations

### Memory Usage

| Mode | 50M Peaks | 200M Peaks |
|------|-----------|------------|
| In-memory | ~2.5 GB | ~10 GB |
| Out-of-core | ~200 MB | ~200 MB |

### Query Performance

| Operation | In-Memory | Out-of-Core |
|-----------|-----------|-------------|
| View query (1M peaks) | ~20ms | ~50-100ms |
| View query (10M peaks) | ~50ms | ~200-500ms |
| Minimap (full/1% sample) | ~30ms | ~100ms |

### Disk Usage (with zstd compression)

| Dataset Size | Cache Size |
|--------------|------------|
| 50M peaks (~2 GB RAM) | ~600 MB |
| 200M peaks (~10 GB RAM) | ~2.5 GB |

---

## Testing Plan

1. **Unit tests** for DataManager (register, query, bounds)
2. **Integration tests** comparing in-memory vs out-of-core results
3. **Performance benchmarks** for both modes
4. **Memory profiling** to verify RAM reduction
5. **Edge cases**: empty data, single peak, FAIMS CV filtering

---

## Migration Path

1. **Phase 1**: Add DataManager, CLI options (non-breaking, default off)
2. **Phase 2**: Integrate with state and loaders
3. **Phase 3**: Add to settings dialog
4. **Phase 4**: Performance optimizations (query caching)

---

## Conclusion

The unified DuckDB interface provides:
- **Single code path**: Same SQL queries for both modes
- **Zero-copy in-memory**: DuckDB registers pandas DataFrames directly
- **Efficient out-of-core**: Parquet with columnar compression
- **Memory reduction**: 90%+ reduction in RAM for out-of-core mode
- **Fast queries**: Sub-second range queries on 100M+ rows
- **Simple integration**: Minimal changes to existing renderers
