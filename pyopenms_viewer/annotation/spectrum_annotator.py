"""Spectrum annotation using theoretical spectra matching."""

import re
from typing import Optional

import numpy as np
import plotly.graph_objects as go
from pyopenms import (
    AASequence,
    MSSpectrum,
    SpectrumAlignment,
    SpectrumAnnotator,
    TheoreticalSpectrumGenerator,
)

from pyopenms_viewer.annotation.theoretical_spectrum import generate_theoretical_spectrum
from pyopenms_viewer.core.config import ION_COLORS


def annotate_spectrum_with_id(
    spectrum: MSSpectrum,
    peptide_hit,
    tolerance_da: float = 0.05,
) -> list[tuple[int, str, str]]:
    """Annotate a spectrum using SpectrumAnnotator.

    Uses TheoreticalSpectrumGenerator and SpectrumAnnotator to generate
    annotations. Annotations are stored in the spectrum's string data array.

    Args:
        spectrum: The experimental MS2 spectrum
        peptide_hit: PeptideHit with sequence information
        tolerance_da: Mass tolerance in Da for matching

    Returns:
        List of (peak_index, ion_name, ion_type) for annotated peaks
    """
    annotations = []

    try:
        # Create copy to avoid modifying original
        spec_copy = MSSpectrum(spectrum)

        # Setup TheoreticalSpectrumGenerator
        tsg = TheoreticalSpectrumGenerator()
        params = tsg.getParameters()
        params.setValue("add_b_ions", "true")
        params.setValue("add_y_ions", "true")
        params.setValue("add_a_ions", "true")
        params.setValue("add_c_ions", "false")
        params.setValue("add_x_ions", "false")
        params.setValue("add_z_ions", "false")
        params.setValue("add_metainfo", "true")
        tsg.setParameters(params)

        # Setup SpectrumAlignment with absolute tolerance in Da
        sa = SpectrumAlignment()
        sa_params = sa.getParameters()
        sa_params.setValue("tolerance", tolerance_da)
        sa_params.setValue("is_relative_tolerance", "false")
        sa.setParameters(sa_params)

        # Setup SpectrumAnnotator
        annotator = SpectrumAnnotator()

        # Annotate the spectrum - this adds "IonNames" string data array
        annotator.annotateMatches(spec_copy, peptide_hit, tsg, sa)

        # Read annotations from spectrum's string data arrays
        string_arrays = spec_copy.getStringDataArrays()
        for arr in string_arrays:
            arr_name = arr.getName()
            # Handle both bytes and string for array name
            if arr_name == "IonNames" or arr_name == b"IonNames":
                for peak_idx, ion_name in enumerate(arr):
                    if ion_name:
                        # Handle bytes or string annotation
                        if isinstance(ion_name, bytes):
                            ion_name = ion_name.decode("utf-8", errors="ignore")

                        # Determine ion type from name
                        if ion_name.startswith("b"):
                            ion_type = "b"
                        elif ion_name.startswith("y"):
                            ion_type = "y"
                        elif ion_name.startswith("a"):
                            ion_type = "a"
                        elif ion_name.startswith("c"):
                            ion_type = "c"
                        elif ion_name.startswith("x"):
                            ion_type = "x"
                        elif ion_name.startswith("z"):
                            ion_type = "z"
                        else:
                            ion_type = "unknown"
                        annotations.append((peak_idx, ion_name, ion_type))
                break

    except Exception as e:
        print(f"Error annotating spectrum: {e}")

    return annotations


def get_external_peak_annotations(spectrum: MSSpectrum) -> list[tuple[int, str, str]]:
    """Get peak annotations from external sources (idXML).

    Checks for annotations in:
    1. PeakAnnotations from getPeakAnnotations()
    2. UserParam "fragment_annotation" string

    Args:
        spectrum: MS2 spectrum that may have external annotations

    Returns:
        List of (peak_index, ion_name, ion_type) tuples
    """
    annotations = []

    try:
        # Try getPeakAnnotations() first (OpenMS >= 3.0)
        peak_annotations = spectrum.getPeakAnnotations()
        if peak_annotations:
            for pa in peak_annotations:
                peak_idx = pa.peak_index
                annotation = pa.annotation
                if annotation:
                    ion_name = str(annotation)
                    ion_type = _get_ion_type(ion_name)
                    annotations.append((peak_idx, ion_name, ion_type))
    except Exception:
        pass

    # Also check for UserParam annotations
    if spectrum.metaValueExists("fragment_annotation"):
        try:
            frag_annot = spectrum.getMetaValue("fragment_annotation")
            if isinstance(frag_annot, bytes):
                frag_annot = frag_annot.decode()
            annotations.extend(parse_fragment_annotation_string(frag_annot, spectrum))
        except Exception:
            pass

    return annotations


def parse_fragment_annotation_string(
    annotation_str: str,
    spectrum: MSSpectrum,
) -> list[tuple[int, str, str]]:
    """Parse fragment annotation string from UserParam.

    Handles various annotation formats like:
    - "y1@100.5" (ion@mz)
    - "b2+2@200.3" (ion+charge@mz)
    - Space or comma separated

    Args:
        annotation_str: Annotation string from UserParam
        spectrum: Spectrum to match peaks against

    Returns:
        List of (peak_index, ion_name, ion_type) tuples
    """
    annotations = []

    if not annotation_str:
        return annotations

    # Split by common separators
    parts = re.split(r"[,\s]+", annotation_str.strip())

    mz_array, _ = spectrum.get_peaks()

    for part in parts:
        if "@" in part:
            ion_part, mz_part = part.split("@", 1)
            try:
                target_mz = float(mz_part)
                # Find closest peak
                if len(mz_array) > 0:
                    diffs = abs(mz_array - target_mz)
                    min_idx = int(diffs.argmin())
                    if diffs[min_idx] < 0.5:  # Within 0.5 Da
                        ion_name = ion_part
                        ion_type = _get_ion_type(ion_name)
                        annotations.append((min_idx, ion_name, ion_type))
            except ValueError:
                pass

    return annotations


def _get_ion_type(ion_name: str) -> str:
    """Determine ion type from ion name.

    Args:
        ion_name: Ion name string (e.g., "b3", "y5+2")

    Returns:
        Ion type character ("b", "y", "a", "c", "x", "z", "precursor", "unknown")
    """
    name = ion_name.lower()
    if name.startswith("b"):
        return "b"
    elif name.startswith("y"):
        return "y"
    elif name.startswith("a"):
        return "a"
    elif name.startswith("c"):
        return "c"
    elif name.startswith("x"):
        return "x"
    elif name.startswith("z"):
        return "z"
    elif "precursor" in name or "prec" in name or "[m" in name:
        return "precursor"
    elif "mi:" in name or name.startswith("i"):
        return "unknown"  # Immonium ions
    else:
        return "unknown"


def get_external_peak_annotations_from_hit(
    peptide_hit,
    exp_mz: np.ndarray,
    tolerance_da: float = 0.05,
) -> list[tuple[int, str, str]]:
    """Get external peak annotations from a PeptideHit using getPeakAnnotations() API.

    This uses the pyOpenMS PeptideHit.getPeakAnnotations() method which returns
    pre-parsed PeakAnnotation objects from idXML fragment_annotation data.

    Args:
        peptide_hit: PeptideHit object with peak annotations
        exp_mz: Experimental m/z array to match annotations to peak indices
        tolerance_da: Mass tolerance in Da for matching annotations to peaks

    Returns:
        List of (peak_index, ion_name, ion_type) for matched annotations
    """
    annotations = []

    if len(exp_mz) == 0:
        return annotations

    try:
        peak_annotations = peptide_hit.getPeakAnnotations()

        if not peak_annotations:
            return annotations

        for peak_ann in peak_annotations:
            ann_mz = peak_ann.mz
            ion_name = peak_ann.annotation

            # Handle bytes if needed
            if isinstance(ion_name, bytes):
                ion_name = ion_name.decode("utf-8", errors="ignore")

            # Find closest experimental peak within tolerance
            diffs = np.abs(exp_mz - ann_mz)
            min_idx = np.argmin(diffs)
            if diffs[min_idx] <= tolerance_da:
                ion_type = _get_ion_type(ion_name)
                annotations.append((int(min_idx), ion_name, ion_type))

    except Exception as e:
        print(f"Error getting external peak annotations: {e}")

    return annotations


def create_annotated_spectrum_plot(
    exp_mz: np.ndarray,
    exp_int: np.ndarray,
    sequence_str: str,
    charge: int,
    precursor_mz: float,
    tolerance_da: float = 0.5,
    peak_annotations: Optional[list[tuple[int, str, str]]] = None,
    annotate: bool = True,
    mirror_mode: bool = False,
) -> go.Figure:
    """Create an annotated spectrum plot using Plotly.

    Args:
        exp_mz: Experimental m/z values
        exp_int: Experimental intensity values
        sequence_str: Peptide sequence string
        charge: Precursor charge
        precursor_mz: Precursor m/z value
        tolerance_da: Mass tolerance in Da for matching (used if no peak_annotations)
        peak_annotations: Optional list of (peak_index, ion_name, ion_type) from SpectrumAnnotator
        annotate: Whether to show annotations (if False, shows raw spectrum)
        mirror_mode: If True, flip annotated peaks downward for comparison view

    Returns:
        Plotly Figure object with annotated spectrum
    """
    # Normalize intensities to percentage
    max_int = exp_int.max() if len(exp_int) > 0 else 1
    exp_int_norm = (exp_int / max_int) * 100

    # Create figure
    fig = go.Figure()

    # Add experimental spectrum as vertical lines (stem plot)
    x_stems = []
    y_stems = []
    for mz, intensity in zip(exp_mz, exp_int_norm):
        x_stems.extend([mz, mz, None])
        y_stems.extend([0, intensity, None])

    fig.add_trace(
        go.Scatter(
            x=x_stems,
            y=y_stems,
            mode="lines",
            line={"color": "gray", "width": 1},
            name="Experimental",
            hoverinfo="skip",
            opacity=0.6,
        )
    )

    # Add invisible hover points for experimental peaks
    fig.add_trace(
        go.Scatter(
            x=exp_mz,
            y=exp_int_norm,
            mode="markers",
            marker={"color": "gray", "size": 8, "opacity": 0},
            showlegend=False,
            hovertemplate="m/z: %{x:.4f}<br>Intensity: %{y:.1f}%<extra></extra>",
        )
    )

    # Add annotations if enabled
    if annotate:
        matched_peaks = {"b": [], "y": [], "a": [], "c": [], "x": [], "z": [], "precursor": [], "unknown": []}

        if peak_annotations:
            # Use provided peak annotations from SpectrumAnnotator
            for peak_idx, ion_name, ion_type in peak_annotations:
                if peak_idx < len(exp_mz):
                    matched_peaks[ion_type].append(
                        {"mz": exp_mz[peak_idx], "intensity": exp_int_norm[peak_idx], "label": ion_name}
                    )
        else:
            # Fall back to generating theoretical spectrum for annotation
            try:
                seq = AASequence.fromString(sequence_str)
                theo_ions = generate_theoretical_spectrum(seq, charge)

                for ion_type, ions in [("b", theo_ions["b"]), ("y", theo_ions["y"])]:
                    for theo_mz, ion_name in ions:
                        # Find closest experimental peak
                        if len(exp_mz) > 0:
                            diffs = np.abs(exp_mz - theo_mz)
                            min_idx = np.argmin(diffs)
                            if diffs[min_idx] <= tolerance_da:
                                matched_peaks[ion_type].append(
                                    {"mz": exp_mz[min_idx], "intensity": exp_int_norm[min_idx], "label": ion_name}
                                )
            except Exception:
                pass

        # Add matched peaks as colored lines grouped by ion type
        for ion_type, peaks in matched_peaks.items():
            if not peaks:
                continue
            color = ION_COLORS[ion_type]

            # Create stem plot for this ion type
            x_ions = []
            y_ions = []
            for peak in peaks:
                x_ions.extend([peak["mz"], peak["mz"], None])
                if mirror_mode:
                    y_ions.extend([0, -peak["intensity"], None])
                else:
                    y_ions.extend([0, peak["intensity"], None])

            fig.add_trace(
                go.Scatter(
                    x=x_ions,
                    y=y_ions,
                    mode="lines",
                    line={"color": color, "width": 2},
                    name=f"{ion_type}-ions",
                    hoverinfo="skip",
                )
            )

            # Add hover points and annotations for matched peaks
            for peak in peaks:
                y_val = -peak["intensity"] if mirror_mode else peak["intensity"]
                fig.add_trace(
                    go.Scatter(
                        x=[peak["mz"]],
                        y=[y_val],
                        mode="markers",
                        marker={"color": color, "size": 4},
                        showlegend=False,
                        hovertemplate=f"{peak['label']}<br>m/z: {peak['mz']:.4f}<br>Intensity: {peak['intensity']:.1f}%<extra></extra>",
                    )
                )

                # Add text annotation
                if mirror_mode:
                    text_y = y_val - 3
                    text_angle = 45
                else:
                    text_y = peak["intensity"] + 3
                    text_angle = -45
                fig.add_annotation(
                    x=peak["mz"],
                    y=text_y,
                    text=peak["label"],
                    showarrow=False,
                    font={"size": 9, "color": color},
                    textangle=text_angle,
                )

    # Add precursor marker
    fig.add_vline(
        x=precursor_mz, line_dash="dash", line_color="orange", annotation_text=f"Precursor ({precursor_mz:.2f})"
    )

    # Update layout
    fig.update_layout(
        title={"text": f"MS2 Spectrum: {sequence_str} (z={charge}+)", "font": {"size": 14, "color": "#888"}},
        xaxis_title="m/z",
        yaxis_title="Relative Intensity (%)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin={"l": 60, "r": 20, "t": 50, "b": 50},
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1, "font": {"size": 10}},
        modebar={"remove": ["lasso2d", "select2d"]},
        font={"color": "#888"},
    )

    fig.update_xaxes(
        range=[0, max(exp_mz) * 1.05] if len(exp_mz) > 0 else [0, 2000],
        showgrid=False,
        linecolor="#888",
        tickcolor="#888",
    )

    if mirror_mode:
        # Symmetric y-axis for mirror view with zero line
        fig.update_yaxes(
            range=[-110, 110],
            showgrid=False,
            fixedrange=True,
            linecolor="#888",
            tickcolor="#888",
            zeroline=True,
            zerolinecolor="#888",
            zerolinewidth=1,
            tickvals=[-100, -50, 0, 50, 100],
            ticktext=["100", "50", "0", "50", "100"],
        )
    else:
        fig.update_yaxes(
            range=[0, 110],
            showgrid=False,
            fixedrange=True,
            linecolor="#888",
            tickcolor="#888",
        )

    return fig
