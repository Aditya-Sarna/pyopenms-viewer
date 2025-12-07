"""Custom range panel component.

This panel allows manual input of RT and m/z ranges for precise
view control.
"""

from typing import Optional

from nicegui import ui

from pyopenms_viewer.core.state import ViewerState
from pyopenms_viewer.panels.base_panel import BasePanel


class CustomRangePanel(BasePanel):
    """Custom range input panel.

    Features:
    - Manual RT min/max input
    - Manual m/z min/max input
    - Apply button to update view
    """

    def __init__(self, state: ViewerState):
        """Initialize custom range panel.

        Args:
            state: ViewerState instance (shared reference)
        """
        super().__init__(state, "custom_range", "Custom Range", "tune")

        # UI elements
        self.rt_min_input: Optional[ui.number] = None
        self.rt_max_input: Optional[ui.number] = None
        self.mz_min_input: Optional[ui.number] = None
        self.mz_max_input: Optional[ui.number] = None

    def build(self, container: ui.element) -> ui.expansion:
        """Build the custom range panel UI.

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
                with ui.row().classes("w-full gap-4 items-end"):
                    self.rt_min_input = ui.number(
                        label="RT Min (s)",
                        value=0,
                        format="%.2f"
                    ).props("dense outlined").classes("w-32")

                    self.rt_max_input = ui.number(
                        label="RT Max (s)",
                        value=1000,
                        format="%.2f"
                    ).props("dense outlined").classes("w-32")

                    self.mz_min_input = ui.number(
                        label="m/z Min",
                        value=0,
                        format="%.2f"
                    ).props("dense outlined").classes("w-32")

                    self.mz_max_input = ui.number(
                        label="m/z Max",
                        value=2000,
                        format="%.2f"
                    ).props("dense outlined").classes("w-32")

                    ui.button("Apply Range", on_click=self._apply_range).props(
                        "color=primary"
                    )

                    ui.button("Reset", on_click=self._reset_to_full).props(
                        "color=grey outline"
                    )

        # Subscribe to events
        self.state.on_data_loaded(self._on_data_loaded)
        self.state.on_view_changed(self._on_view_changed)

        self._is_built = True
        return self.expansion

    def update(self) -> None:
        """Update the input fields with current view bounds."""
        if self.state.view_rt_min is not None:
            if self.rt_min_input:
                self.rt_min_input.value = self.state.view_rt_min
            if self.rt_max_input:
                self.rt_max_input.value = self.state.view_rt_max
            if self.mz_min_input:
                self.mz_min_input.value = self.state.view_mz_min
            if self.mz_max_input:
                self.mz_max_input.value = self.state.view_mz_max

    def _has_data(self) -> bool:
        """Check if panel has data to display."""
        return self.state.df is not None

    # === Event handlers ===

    def _on_data_loaded(self, data_type: str):
        """Handle data loaded event."""
        if data_type == "mzml":
            self.update()

    def _on_view_changed(self):
        """Handle view changed event."""
        self.update()

    def _apply_range(self):
        """Apply the custom range to the view."""
        if self.state.df is None:
            ui.notify("No data loaded", type="warning")
            return

        rt_min = self.rt_min_input.value if self.rt_min_input else 0
        rt_max = self.rt_max_input.value if self.rt_max_input else 1000
        mz_min = self.mz_min_input.value if self.mz_min_input else 0
        mz_max = self.mz_max_input.value if self.mz_max_input else 2000

        # Validate ranges
        if rt_min >= rt_max:
            ui.notify("RT Min must be less than RT Max", type="warning")
            return
        if mz_min >= mz_max:
            ui.notify("m/z Min must be less than m/z Max", type="warning")
            return

        # Clamp to data bounds
        self.state.view_rt_min = max(self.state.rt_min, rt_min)
        self.state.view_rt_max = min(self.state.rt_max, rt_max)
        self.state.view_mz_min = max(self.state.mz_min, mz_min)
        self.state.view_mz_max = min(self.state.mz_max, mz_max)

        # Emit view changed event
        self.state.emit_view_changed()

        ui.notify("Range applied", type="positive")

    def _reset_to_full(self):
        """Reset to full data range."""
        if self.state.df is None:
            return

        self.state.reset_view()
        self.update()
        ui.notify("Reset to full range", type="info")
