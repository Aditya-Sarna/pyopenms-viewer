"""Features table panel component.

This panel displays a table of detected features from featureXML files
with filtering and zoom-to-feature functionality.
"""

from typing import Optional, Callable

from nicegui import ui

from pyopenms_viewer.core.state import ViewerState
from pyopenms_viewer.panels.base_panel import BasePanel


class FeaturesTablePanel(BasePanel):
    """Features table panel.

    Features:
    - Table of detected features with metadata
    - Filtering by intensity, quality, charge
    - Click to zoom to feature location
    - Hover highlighting
    """

    def __init__(self, state: ViewerState):
        """Initialize features table panel.

        Args:
            state: ViewerState instance (shared reference)
        """
        super().__init__(state, "features_table", "Features", "scatter_plot")

        # UI elements
        self.feature_table = None
        self.min_intensity_input = None
        self.min_quality_input = None
        self.charge_select = None

        # Callback for feature selection
        self._on_feature_selected: Optional[Callable] = None

    def build(self, container: ui.element) -> ui.expansion:
        """Build the features table panel UI.

        Args:
            container: Parent element to build panel in

        Returns:
            The expansion element created
        """
        with container:
            self.expansion = ui.expansion(
                self.name, icon=self.icon, value=False
            ).classes("w-full max-w-[1700px]")

            with self.expansion:
                self._build_help_text()
                self._build_filter_row()
                self._build_table()

        # Subscribe to events
        self.state.on_data_loaded(self._on_data_loaded)

        self._is_built = True
        return self.expansion

    def _build_help_text(self):
        """Build the help text."""
        ui.label("Click a row to zoom to that feature").classes(
            "text-sm text-gray-400 mb-2"
        )

    def _build_filter_row(self):
        """Build the filter controls row."""
        with ui.row().classes("w-full items-end gap-2 mb-2 flex-wrap"):
            ui.label("Filter:").classes("text-xs text-gray-400")

            self.min_intensity_input = ui.number(
                label="Min Intensity",
                format="%.0f"
            ).props("dense outlined").classes("w-28")

            self.min_quality_input = ui.number(
                label="Min Quality",
                format="%.2f"
            ).props("dense outlined").classes("w-24")

            self.charge_select = ui.select(
                ["All", "1", "2", "3", "4", "5+"],
                value="All",
                label="Charge"
            ).props("dense outlined").classes("w-20")

            ui.button("Apply", on_click=self._apply_filter).props(
                "dense size=sm color=primary"
            )
            ui.button("Reset", on_click=self._reset_filter).props(
                "dense size=sm color=grey"
            )

    def _build_table(self):
        """Build the features table."""
        columns = [
            {"name": "idx", "label": "#", "field": "idx", "sortable": True, "align": "left"},
            {"name": "rt", "label": "RT (s)", "field": "rt", "sortable": True, "align": "right"},
            {"name": "mz", "label": "m/z", "field": "mz", "sortable": True, "align": "right"},
            {"name": "intensity", "label": "Intensity", "field": "intensity", "sortable": True, "align": "right"},
            {"name": "charge", "label": "Z", "field": "charge", "sortable": True, "align": "center"},
            {"name": "quality", "label": "Quality", "field": "quality", "sortable": True, "align": "right"},
        ]

        self.feature_table = (
            ui.table(
                columns=columns,
                rows=[],
                row_key="idx",
                pagination={"rowsPerPage": 8, "sortBy": "intensity", "descending": True},
                selection="single",
                on_select=self._on_table_select,
            )
            .classes("w-full hover-highlight")
            .props("flat bordered dense")
        )
        # Note: Removed rowClick handler - on_select already handles selection
        # and rowClick can send large amounts of data via websocket

        # Store reference in state
        self.state.feature_table = self.feature_table

    def update(self) -> None:
        """Update the table display."""
        if self.feature_table is not None:
            self.feature_table.rows = self.state.feature_data
            self.feature_table.update()

    def _has_data(self) -> bool:
        """Check if panel has data to display."""
        return len(self.state.feature_data) > 0

    def _get_filtered_data(self) -> list:
        """Get filtered feature data based on current filters."""
        data = self.state.feature_data

        # Filter by intensity
        if self.min_intensity_input and self.min_intensity_input.value is not None:
            data = [f for f in data if f.get("intensity", 0) >= self.min_intensity_input.value]

        # Filter by quality
        if self.min_quality_input and self.min_quality_input.value is not None:
            data = [f for f in data if f.get("quality", 0) >= self.min_quality_input.value]

        # Filter by charge
        if self.charge_select and self.charge_select.value and self.charge_select.value != "All":
            if self.charge_select.value == "5+":
                data = [f for f in data if f.get("charge", 0) >= 5]
            else:
                charge_val = int(self.charge_select.value)
                data = [f for f in data if f.get("charge", 0) == charge_val]

        return data

    # === Event handlers ===

    def _on_data_loaded(self, data_type: str):
        """Handle data loaded event."""
        if data_type == "features":
            self.update()
            # Auto-expand if features present
            if self._has_data() and self.expansion:
                self.expansion.value = True

    def _on_table_select(self, e):
        """Handle row selection."""
        if e.selection:
            row = e.selection[0]
            if row and "idx" in row:
                self._zoom_to_feature(row["idx"])

    def _apply_filter(self):
        """Apply current filter settings."""
        filtered = self._get_filtered_data()
        if self.feature_table:
            self.feature_table.rows = filtered
        ui.notify(f"Showing {len(filtered)} features", type="info")

    def _reset_filter(self):
        """Reset all filters."""
        if self.min_intensity_input:
            self.min_intensity_input.value = None
        if self.min_quality_input:
            self.min_quality_input.value = None
        if self.charge_select:
            self.charge_select.value = "All"
        self.update()

    def _zoom_to_feature(self, feature_idx: int):
        """Zoom the view to a specific feature.

        Args:
            feature_idx: Index of the feature to zoom to
        """
        if self.state.feature_map is None:
            return

        try:
            feature = self.state.feature_map[feature_idx]
            rt = feature.getRT()
            mz = feature.getMZ()

            # Get feature bounds from convex hull or use defaults
            hulls = feature.getConvexHulls()
            if hulls:
                hull = hulls[0]
                points = hull.getHullPoints()
                if len(points) > 0:
                    rts = [p[0] for p in points]
                    mzs = [p[1] for p in points]
                    rt_min, rt_max = min(rts), max(rts)
                    mz_min, mz_max = min(mzs), max(mzs)
                    # Add padding
                    rt_pad = (rt_max - rt_min) * 0.2 or 30
                    mz_pad = (mz_max - mz_min) * 0.2 or 5
                    rt_min -= rt_pad
                    rt_max += rt_pad
                    mz_min -= mz_pad
                    mz_max += mz_pad
                else:
                    # Default zoom
                    rt_min, rt_max = rt - 30, rt + 30
                    mz_min, mz_max = mz - 5, mz + 5
            else:
                # Default zoom
                rt_min, rt_max = rt - 30, rt + 30
                mz_min, mz_max = mz - 5, mz + 5

            # Update view bounds
            self.state.view_rt_min = max(self.state.rt_min, rt_min)
            self.state.view_rt_max = min(self.state.rt_max, rt_max)
            self.state.view_mz_min = max(self.state.mz_min, mz_min)
            self.state.view_mz_max = min(self.state.mz_max, mz_max)

            # Update selected feature
            self.state.selected_feature_idx = feature_idx

            # Emit view changed
            self.state.emit_view_changed()

        except Exception as e:
            ui.notify(f"Error zooming to feature: {e}", type="negative")

    def set_on_feature_selected(self, callback: Callable):
        """Set callback for when a feature is selected.

        Args:
            callback: Function to call with feature index
        """
        self._on_feature_selected = callback
