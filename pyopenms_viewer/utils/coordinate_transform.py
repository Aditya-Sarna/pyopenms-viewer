"""Coordinate transformation utilities for pixel <-> data conversion."""

from pyopenms_viewer.core.state import ViewerState


class CoordinateTransform:
    """Coordinate transformation utilities for pixel <-> data conversion.

    Handles transformation between:
    - Screen pixel coordinates (from mouse events)
    - Data coordinates (RT, m/z, IM values)

    Takes into account:
    - Plot margins
    - Axis swapping (swap_axes option)
    - Current view bounds
    """

    def __init__(
        self,
        plot_width: int,
        plot_height: int,
        margin_left: int,
        margin_top: int,
    ):
        """Initialize transformer.

        Args:
            plot_width: Width of the plot area (excluding margins)
            plot_height: Height of the plot area (excluding margins)
            margin_left: Left margin in pixels
            margin_top: Top margin in pixels
        """
        self.plot_width = plot_width
        self.plot_height = plot_height
        self.margin_left = margin_left
        self.margin_top = margin_top

    def data_to_pixel(
        self,
        state: ViewerState,
        rt: float,
        mz: float,
    ) -> tuple[int, int]:
        """Convert RT/m/z data coordinates to pixel coordinates.

        Args:
            state: ViewerState with current view bounds and swap_axes setting
            rt: Retention time value
            mz: m/z value

        Returns:
            Tuple of (x, y) pixel coordinates (relative to plot area origin)
        """
        bounds = state.get_view_bounds()
        rt_range = bounds.rt_max - bounds.rt_min
        mz_range = bounds.mz_max - bounds.mz_min

        if rt_range == 0 or mz_range == 0:
            return (0, 0)

        if state.swap_axes:
            # m/z on x-axis, RT on y-axis (inverted)
            x = int((mz - bounds.mz_min) / mz_range * self.plot_width)
            y = int((1 - (rt - bounds.rt_min) / rt_range) * self.plot_height)
        else:
            # RT on x-axis, m/z on y-axis (inverted)
            x = int((rt - bounds.rt_min) / rt_range * self.plot_width)
            y = int((1 - (mz - bounds.mz_min) / mz_range) * self.plot_height)

        return (x, y)

    def pixel_to_data(
        self,
        state: ViewerState,
        pixel_x: int,
        pixel_y: int,
    ) -> tuple[float, float]:
        """Convert pixel coordinates to RT/m/z data coordinates.

        Args:
            state: ViewerState with current view bounds and swap_axes setting
            pixel_x: X pixel coordinate (including margin)
            pixel_y: Y pixel coordinate (including margin)

        Returns:
            Tuple of (rt, mz) data coordinates
        """
        # Adjust for margins
        plot_x = pixel_x - self.margin_left
        plot_y = pixel_y - self.margin_top

        # Clamp to plot area
        plot_x = max(0, min(self.plot_width, plot_x))
        plot_y = max(0, min(self.plot_height, plot_y))

        bounds = state.get_view_bounds()

        if state.swap_axes:
            # m/z on x-axis, RT on y-axis (inverted)
            mz = bounds.mz_min + (plot_x / self.plot_width) * (bounds.mz_max - bounds.mz_min)
            rt = bounds.rt_max - (plot_y / self.plot_height) * (bounds.rt_max - bounds.rt_min)
            return (rt, mz)
        else:
            # RT on x-axis, m/z on y-axis (inverted)
            rt = bounds.rt_min + (plot_x / self.plot_width) * (bounds.rt_max - bounds.rt_min)
            mz = bounds.mz_max - (plot_y / self.plot_height) * (bounds.mz_max - bounds.mz_min)
            return (rt, mz)

    def im_data_to_pixel(
        self,
        state: ViewerState,
        mz: float,
        im: float,
    ) -> tuple[int, int]:
        """Convert m/z/IM data coordinates to pixel coordinates for IM plot.

        Args:
            state: ViewerState with current view bounds
            mz: m/z value
            im: Ion mobility value

        Returns:
            Tuple of (x, y) pixel coordinates
        """
        bounds = state.get_view_bounds()
        mz_range = bounds.mz_max - bounds.mz_min
        im_range = bounds.im_max - bounds.im_min

        if mz_range == 0 or im_range == 0:
            return (0, 0)

        # m/z on x-axis, IM on y-axis (inverted)
        x = int((mz - bounds.mz_min) / mz_range * self.plot_width)
        y = int((1 - (im - bounds.im_min) / im_range) * self.plot_height)

        return (x, y)

    def im_pixel_to_data(
        self,
        state: ViewerState,
        pixel_x: int,
        pixel_y: int,
    ) -> tuple[float, float]:
        """Convert pixel coordinates to m/z/IM data coordinates for IM plot.

        Args:
            state: ViewerState with current view bounds
            pixel_x: X pixel coordinate (including margin)
            pixel_y: Y pixel coordinate (including margin)

        Returns:
            Tuple of (mz, im) data coordinates
        """
        # Adjust for margins
        plot_x = pixel_x - self.margin_left
        plot_y = pixel_y - self.margin_top

        # Clamp to plot area
        plot_x = max(0, min(self.plot_width, plot_x))
        plot_y = max(0, min(self.plot_height, plot_y))

        bounds = state.get_view_bounds()

        mz = bounds.mz_min + (plot_x / self.plot_width) * (bounds.mz_max - bounds.mz_min)
        im = bounds.im_max - (plot_y / self.plot_height) * (bounds.im_max - bounds.im_min)

        return (mz, im)
