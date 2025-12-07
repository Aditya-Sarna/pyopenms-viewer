"""Peak map rendering using Datashader.

This module provides the main renderer for 2D peak maps using Datashader
for server-side aggregation of millions of peaks.
"""

import base64
import io

import datashader as ds
import datashader.transfer_functions as tf
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from pyopenms_viewer.core.config import COLORMAPS, get_colormap_background
from pyopenms_viewer.core.state import ViewerState


class PeakMapRenderer:
    """Renders 2D peak maps using Datashader.

    This is a stateless renderer that takes ViewerState and produces images.
    All data access is via state references (no copies).

    Example:
        renderer = PeakMapRenderer()
        base64_png = renderer.render(state, fast=False)
    """

    def __init__(
        self,
        plot_width: int = 1100,
        plot_height: int = 550,
        margin_left: int = 80,
        margin_right: int = 20,
        margin_top: int = 20,
        margin_bottom: int = 50,
    ):
        """Initialize renderer with dimensions.

        Args:
            plot_width: Width of the plot area (excluding margins)
            plot_height: Height of the plot area (excluding margins)
            margin_left: Left margin for axis labels
            margin_right: Right margin
            margin_top: Top margin
            margin_bottom: Bottom margin for axis labels
        """
        self.plot_width = plot_width
        self.plot_height = plot_height
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.canvas_width = plot_width + margin_left + margin_right
        self.canvas_height = plot_height + margin_top + margin_bottom

    def render(
        self,
        state: ViewerState,
        fast: bool = False,
        draw_overlays: bool = True,
        draw_axes: bool = True,
    ) -> str:
        """Render the peak map to a base64-encoded PNG string.

        Args:
            state: ViewerState containing all data and view bounds
            fast: If True, render at reduced resolution for panning
            draw_overlays: If True, draw features/IDs/markers (skipped in fast mode)
            draw_axes: If True, draw axis labels (skipped in fast mode)

        Returns:
            Base64-encoded PNG string, or empty string if no data
        """
        if state.df is None or len(state.df) == 0:
            return ""

        # Get view bounds
        view_rt_min = state.view_rt_min if state.view_rt_min is not None else state.rt_min
        view_rt_max = state.view_rt_max if state.view_rt_max is not None else state.rt_max
        view_mz_min = state.view_mz_min if state.view_mz_min is not None else state.mz_min
        view_mz_max = state.view_mz_max if state.view_mz_max is not None else state.mz_max

        # Filter to current view
        mask = (
            (state.df["rt"] >= view_rt_min)
            & (state.df["rt"] <= view_rt_max)
            & (state.df["mz"] >= view_mz_min)
            & (state.df["mz"] <= view_mz_max)
        )
        view_df = state.df[mask]

        if len(view_df) == 0:
            return ""

        # Render with Datashader
        resolution_factor = 4 if fast else 1
        render_width = self.plot_width // resolution_factor
        render_height = self.plot_height // resolution_factor

        if state.swap_axes:
            # m/z on x-axis, RT on y-axis
            ds_canvas = ds.Canvas(
                plot_width=render_width,
                plot_height=render_height,
                x_range=(view_mz_min, view_mz_max),
                y_range=(view_rt_min, view_rt_max),
            )
            agg = ds_canvas.points(view_df, "mz", "rt", ds.max("log_intensity"))
        else:
            # RT on x-axis, m/z on y-axis
            ds_canvas = ds.Canvas(
                plot_width=render_width,
                plot_height=render_height,
                x_range=(view_rt_min, view_rt_max),
                y_range=(view_mz_min, view_mz_max),
            )
            agg = ds_canvas.points(view_df, "rt", "mz", ds.max("log_intensity"))

        # Apply colormap
        img = tf.shade(agg, cmap=COLORMAPS[state.colormap], how="linear")
        if not fast:
            img = tf.dynspread(img, threshold=0.5, max_px=3)
        img = tf.set_background(img, get_colormap_background(state.colormap))

        plot_img = img.to_pil()

        # Upscale if fast mode
        if fast and resolution_factor > 1:
            plot_img = plot_img.resize(
                (self.plot_width, self.plot_height), Image.Resampling.NEAREST
            )

        # Compose final canvas
        canvas = Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))
        plot_img_rgba = plot_img.convert("RGBA")
        canvas.paste(plot_img_rgba, (self.margin_left, self.margin_top))

        # Encode to base64
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def render_faims(self, state: ViewerState, cv: float) -> str:
        """Render a single FAIMS CV peak map.

        Args:
            state: ViewerState with FAIMS data
            cv: Compensation voltage value

        Returns:
            Base64-encoded PNG string
        """
        if cv not in state.faims_data or len(state.faims_data[cv]) == 0:
            return ""

        cv_df = state.faims_data[cv]

        view_rt_min = state.view_rt_min if state.view_rt_min is not None else state.rt_min
        view_rt_max = state.view_rt_max if state.view_rt_max is not None else state.rt_max
        view_mz_min = state.view_mz_min if state.view_mz_min is not None else state.mz_min
        view_mz_max = state.view_mz_max if state.view_mz_max is not None else state.mz_max

        mask = (
            (cv_df["rt"] >= view_rt_min)
            & (cv_df["rt"] <= view_rt_max)
            & (cv_df["mz"] >= view_mz_min)
            & (cv_df["mz"] <= view_mz_max)
        )
        view_df = cv_df[mask]

        if len(view_df) == 0:
            return ""

        # Smaller dimensions for FAIMS panels
        faims_width = self.plot_width // 2
        faims_height = self.plot_height // 2

        if state.swap_axes:
            ds_canvas = ds.Canvas(
                plot_width=faims_width,
                plot_height=faims_height,
                x_range=(view_mz_min, view_mz_max),
                y_range=(view_rt_min, view_rt_max),
            )
            agg = ds_canvas.points(view_df, "mz", "rt", ds.max("log_intensity"))
        else:
            ds_canvas = ds.Canvas(
                plot_width=faims_width,
                plot_height=faims_height,
                x_range=(view_rt_min, view_rt_max),
                y_range=(view_mz_min, view_mz_max),
            )
            agg = ds_canvas.points(view_df, "rt", "mz", ds.max("log_intensity"))

        img = tf.shade(agg, cmap=COLORMAPS[state.colormap], how="linear")
        img = tf.dynspread(img, threshold=0.5, max_px=2)
        img = tf.set_background(img, get_colormap_background(state.colormap))

        plot_img = img.to_pil()

        buffer = io.BytesIO()
        plot_img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")


class IMPeakMapRenderer:
    """Renders ion mobility peak maps using Datashader."""

    def __init__(
        self,
        plot_width: int = 1100,
        plot_height: int = 550,
        margin_left: int = 80,
        margin_right: int = 20,
        margin_top: int = 20,
        margin_bottom: int = 50,
    ):
        self.plot_width = plot_width
        self.plot_height = plot_height
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.canvas_width = plot_width + margin_left + margin_right
        self.canvas_height = plot_height + margin_top + margin_bottom

    def render(self, state: ViewerState) -> str:
        """Render ion mobility peak map.

        Args:
            state: ViewerState with IM data

        Returns:
            Base64-encoded PNG string
        """
        if state.im_df is None or len(state.im_df) == 0:
            return ""

        view_mz_min = state.view_mz_min if state.view_mz_min is not None else state.mz_min
        view_mz_max = state.view_mz_max if state.view_mz_max is not None else state.mz_max
        view_im_min = state.view_im_min if state.view_im_min is not None else state.im_min
        view_im_max = state.view_im_max if state.view_im_max is not None else state.im_max

        mask = (
            (state.im_df["mz"] >= view_mz_min)
            & (state.im_df["mz"] <= view_mz_max)
            & (state.im_df["im"] >= view_im_min)
            & (state.im_df["im"] <= view_im_max)
        )
        view_df = state.im_df[mask]

        if len(view_df) == 0:
            return ""

        # m/z on x-axis, IM on y-axis
        ds_canvas = ds.Canvas(
            plot_width=self.plot_width,
            plot_height=self.plot_height,
            x_range=(view_mz_min, view_mz_max),
            y_range=(view_im_min, view_im_max),
        )
        agg = ds_canvas.points(view_df, "mz", "im", ds.max("log_intensity"))

        img = tf.shade(agg, cmap=COLORMAPS[state.colormap], how="linear")
        img = tf.dynspread(img, threshold=0.5, max_px=3)
        img = tf.set_background(img, get_colormap_background(state.colormap))

        plot_img = img.to_pil()

        # Calculate canvas width - add space for mobilogram if enabled
        mobilogram_space = state.mobilogram_plot_width + 20 if state.show_mobilogram else 0
        total_canvas_width = self.canvas_width + mobilogram_space

        # Compose final canvas
        canvas = Image.new("RGBA", (total_canvas_width, self.canvas_height), (0, 0, 0, 0))
        plot_img_rgba = plot_img.convert("RGBA")
        canvas.paste(plot_img_rgba, (self.margin_left, self.margin_top))

        # Draw mobilogram on the right side if enabled
        if state.show_mobilogram:
            canvas = self._draw_mobilogram(canvas, state, view_mz_min, view_mz_max, view_im_min, view_im_max)

        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _draw_mobilogram(
        self,
        canvas: Image.Image,
        state: ViewerState,
        view_mz_min: float,
        view_mz_max: float,
        view_im_min: float,
        view_im_max: float,
    ) -> Image.Image:
        """Draw mobilogram (summed intensity vs IM) on the right side of the IM peakmap."""
        draw = ImageDraw.Draw(canvas)

        # Get mobilogram data
        im_values, intensities = self._extract_mobilogram(
            state, view_mz_min, view_mz_max, view_im_min, view_im_max
        )
        if len(im_values) == 0 or len(intensities) == 0:
            return canvas

        # Sort by IM values for proper line drawing (prevents jumps)
        sort_idx = np.argsort(im_values)
        im_values = im_values[sort_idx]
        intensities = intensities[sort_idx]

        # Mobilogram plot area (to the right of the main plot)
        mob_left = self.margin_left + self.plot_width + 10
        mob_right = mob_left + state.mobilogram_plot_width
        mob_top = self.margin_top
        mob_bottom = self.margin_top + self.plot_height

        # Draw border for mobilogram area
        axis_color = (136, 136, 136, 255)
        label_color = (136, 136, 136, 255)
        draw.rectangle([mob_left, mob_top, mob_right, mob_bottom], outline=axis_color, width=1)

        # Normalize intensities to plot width
        max_intensity = np.max(intensities) if len(intensities) > 0 else 1.0
        if max_intensity == 0:
            max_intensity = 1.0

        # Draw filled mobilogram as horizontal bars
        im_range = view_im_max - view_im_min
        if im_range == 0:
            im_range = 1.0

        # Draw as a filled area plot
        points = []
        for im_val, intensity in zip(im_values, intensities):
            # Y position (IM axis, inverted - low IM at bottom)
            y_frac = 1.0 - (im_val - view_im_min) / im_range
            y = mob_top + int(y_frac * self.plot_height)

            # X position (intensity, starting from left edge)
            x_frac = intensity / max_intensity
            x = mob_left + int(x_frac * state.mobilogram_plot_width)

            points.append((x, y))

        # Draw line connecting all points
        if len(points) > 1:
            # Build polygon path: bottom-left -> data points (bottom to top) -> top-left -> close
            fill_points = [(mob_left, mob_bottom)]  # Start at bottom-left
            fill_points.extend(points)  # Go through data points (bottom to top)
            fill_points.append((mob_left, mob_top))  # End at top-left

            # Fill with semi-transparent cyan
            draw.polygon(fill_points, fill=(0, 200, 255, 80))

            # Draw the line on top
            draw.line(points, fill=(0, 200, 255, 255), width=2)

        # Draw axis label at top
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 10)
            except OSError:
                font = ImageFont.load_default()

        label = "Mobilogram"
        bbox = draw.textbbox((0, 0), label, font=font)
        label_width = bbox[2] - bbox[0]
        draw.text(
            (mob_left + (state.mobilogram_plot_width - label_width) // 2, mob_top - 15),
            label,
            fill=label_color,
            font=font,
        )

        return canvas

    def _extract_mobilogram(
        self,
        state: ViewerState,
        mz_min: float,
        mz_max: float,
        im_min: float,
        im_max: float,
    ) -> tuple:
        """Extract mobilogram (summed intensity vs ion mobility) from IM data.

        Returns:
            Tuple of (im_values, intensities) arrays for plotting
        """
        if state.im_df is None or len(state.im_df) == 0:
            return np.array([]), np.array([])

        # Filter to m/z range and current IM view
        mask = (
            (state.im_df["mz"] >= mz_min)
            & (state.im_df["mz"] <= mz_max)
            & (state.im_df["im"] >= im_min)
            & (state.im_df["im"] <= im_max)
        )
        filtered_df = state.im_df[mask]

        if len(filtered_df) == 0:
            return np.array([]), np.array([])

        # Bin IM values and sum intensities
        n_bins = min(200, max(50, int(len(filtered_df) / 100)))  # Adaptive bin count

        bin_edges = np.linspace(im_min, im_max, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Digitize IM values into bins
        bin_indices = np.digitize(filtered_df["im"].values, bin_edges) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        # Sum intensities per bin
        intensities = np.zeros(n_bins, dtype=np.float64)
        np.add.at(intensities, bin_indices, filtered_df["intensity"].values)

        return bin_centers, intensities
