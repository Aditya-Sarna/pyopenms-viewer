"""Axis tick calculation and formatting utilities."""

import math


def calculate_nice_ticks(vmin: float, vmax: float, num_ticks: int = 6) -> list[float]:
    """Calculate nice round tick values for an axis.

    Uses a "nice numbers" algorithm to select human-friendly tick values
    (multiples of 1, 2, 5, or 10 at appropriate scale).

    Args:
        vmin: Minimum value of the range
        vmax: Maximum value of the range
        num_ticks: Approximate number of ticks desired

    Returns:
        List of tick values
    """
    if vmin >= vmax:
        return [vmin]

    range_val = vmax - vmin
    rough_step = range_val / (num_ticks - 1)

    mag = math.floor(math.log10(rough_step))
    pow10 = 10**mag
    norm_step = rough_step / pow10

    if norm_step < 1.5:
        nice_step = 1
    elif norm_step < 3:
        nice_step = 2
    elif norm_step < 7:
        nice_step = 5
    else:
        nice_step = 10

    step = nice_step * pow10
    first_tick = math.ceil(vmin / step) * step
    ticks = []
    tick = first_tick
    while tick <= vmax + step * 0.001:
        ticks.append(tick)
        tick += step

    return ticks


def format_tick_label(value: float, range_val: float) -> str:
    """Format a tick label based on the value and range.

    Automatically selects appropriate precision based on the data range.

    Args:
        value: The tick value to format
        range_val: The total range of the axis (max - min)

    Returns:
        Formatted string for the tick label
    """
    if range_val >= 1000:
        if abs(value) >= 1000:
            return f"{value:.0f}"
        return f"{value:.1f}"
    elif range_val >= 10:
        return f"{value:.1f}"
    elif range_val >= 1:
        return f"{value:.2f}"
    else:
        return f"{value:.3f}"


def format_rt_label(rt_seconds: float, in_minutes: bool = False) -> str:
    """Format retention time for display.

    Args:
        rt_seconds: RT value in seconds
        in_minutes: If True, convert to minutes

    Returns:
        Formatted RT string
    """
    if in_minutes:
        return f"{rt_seconds / 60:.2f}"
    else:
        return f"{rt_seconds:.1f}"


def format_mz_label(mz: float, precision: int = 4) -> str:
    """Format m/z value for display.

    Args:
        mz: m/z value
        precision: Decimal places to show

    Returns:
        Formatted m/z string
    """
    return f"{mz:.{precision}f}"


def format_intensity(intensity: float, scientific: bool = True) -> str:
    """Format intensity value for display.

    Args:
        intensity: Intensity value
        scientific: If True, use scientific notation

    Returns:
        Formatted intensity string
    """
    if scientific:
        return f"{intensity:.2e}"
    else:
        return f"{intensity:.0f}"
