"""Annotation modules for spectrum matching and labeling."""

from pyopenms_viewer.annotation.tick_formatter import (
    calculate_nice_ticks,
    format_tick_label,
    format_rt_label,
    format_mz_label,
    format_intensity,
)
from pyopenms_viewer.annotation.theoretical_spectrum import generate_theoretical_spectrum
from pyopenms_viewer.annotation.spectrum_annotator import (
    annotate_spectrum_with_id,
    get_external_peak_annotations,
    parse_fragment_annotation_string,
)

__all__ = [
    "calculate_nice_ticks",
    "format_tick_label",
    "format_rt_label",
    "format_mz_label",
    "format_intensity",
    "generate_theoretical_spectrum",
    "annotate_spectrum_with_id",
    "get_external_peak_annotations",
    "parse_fragment_annotation_string",
]
