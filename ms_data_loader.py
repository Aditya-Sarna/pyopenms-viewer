"""
MS Data Loader Module

Handles loading and parsing of mass spectrometry data files (mzML, featureXML, idXML).
Separated from the viewer for better testability.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from pyopenms import (
    FeatureMap,
    FeatureXMLFile,
    IdXMLFile,
    MSExperiment,
    MzMLFile,
)


@dataclass
class MzMLData:
    """Container for data extracted from an mzML file."""

    # Core data
    exp: Optional[MSExperiment] = None
    df: Optional[pd.DataFrame] = None  # Main peak data: rt, mz, intensity, log_intensity
    filepath: Optional[str] = None

    # Bounds
    rt_min: float = 0.0
    rt_max: float = 1.0
    mz_min: float = 0.0
    mz_max: float = 1.0

    # TIC data
    tic_rt: Optional[np.ndarray] = None
    tic_intensity: Optional[np.ndarray] = None

    # Chromatogram data
    chromatograms: list = field(default_factory=list)
    chromatogram_data: dict = field(default_factory=dict)
    has_chromatograms: bool = False

    # Ion mobility data
    has_ion_mobility: bool = False
    im_type: Optional[str] = None
    im_unit: str = ""
    im_df: Optional[pd.DataFrame] = None
    im_min: float = 0.0
    im_max: float = 1.0

    # FAIMS data
    has_faims: bool = False
    faims_cvs: list = field(default_factory=list)
    faims_data: dict = field(default_factory=dict)
    faims_tic: dict = field(default_factory=dict)

    # Spectrum metadata
    spectrum_data: list = field(default_factory=list)


@dataclass
class FeatureData:
    """Container for data extracted from a featureXML file."""

    feature_map: Optional[FeatureMap] = None
    filepath: Optional[str] = None
    features: list = field(default_factory=list)  # List of feature metadata dicts


@dataclass
class IdXMLData:
    """Container for data extracted from an idXML file."""

    peptide_ids: list = field(default_factory=list)
    protein_ids: list = field(default_factory=list)
    filepath: Optional[str] = None
    id_data: list = field(default_factory=list)  # List of ID metadata dicts
    meta_keys: list = field(default_factory=list)  # Discovered meta value keys


def get_cv_from_spectrum(spec) -> Optional[float]:
    """Extract FAIMS compensation voltage from spectrum metadata."""
    cv_names = [
        "FAIMS compensation voltage",
        "ion mobility drift time",
        "MS:1001581",
    ]
    for name in cv_names:
        if spec.metaValueExists(name):
            try:
                return float(spec.getMetaValue(name))
            except (ValueError, TypeError):
                pass

    try:
        acq = spec.getAcquisitionInfo()
        if acq:
            for a in acq:
                for name in cv_names:
                    if a.metaValueExists(name):
                        return float(a.getMetaValue(name))
    except Exception:
        pass

    return None


def parse_mzml_file(filepath: str) -> Optional[MSExperiment]:
    """Parse mzML file and return MSExperiment object.

    Args:
        filepath: Path to the mzML file

    Returns:
        MSExperiment object or None if parsing failed
    """
    try:
        filename = Path(filepath).name
        print(f"Reading {filename} with MzMLFile (this may take a while)...")
        exp = MSExperiment()
        MzMLFile().load(filepath, exp)
        print(f"Loaded {exp.size()} spectra from {filename}")
        return exp if exp.size() > 0 else None
    except Exception as e:
        print(f"Error parsing mzML: {e}")
        return None


def extract_chromatograms(exp: MSExperiment) -> tuple[list, dict, bool]:
    """Extract chromatogram data from experiment.

    Args:
        exp: MSExperiment object

    Returns:
        Tuple of (chromatograms list, chromatogram_data dict, has_chromatograms bool)
    """
    if exp is None:
        return [], {}, False

    chroms = exp.getChromatograms()
    if len(chroms) == 0:
        return [], {}, False

    chromatograms = []
    chromatogram_data = {}

    for idx, chrom in enumerate(chroms):
        native_id = chrom.getNativeID()

        # Check if this is a TIC chromatogram
        is_tic = "TIC" in native_id.upper() or "total ion" in native_id.lower()

        # Get RT and intensity arrays
        rt_array, int_array = chrom.get_peaks()
        if len(rt_array) == 0:
            continue

        # Get precursor info
        precursor = chrom.getPrecursor()
        precursor_mz = precursor.getMZ() if precursor else 0.0
        precursor_charge = precursor.getCharge() if precursor else 0

        # Get product info
        product = chrom.getProduct()
        product_mz = product.getMZ() if product else 0.0

        # Calculate summary statistics
        rt_min = float(rt_array.min())
        rt_max = float(rt_array.max())
        max_intensity = float(int_array.max()) if len(int_array) > 0 else 0
        total_intensity = float(int_array.sum()) if len(int_array) > 0 else 0

        # Store metadata
        chromatograms.append({
            "idx": idx,
            "native_id": native_id,
            "is_tic": is_tic,
            "type": "TIC" if is_tic else "",
            "precursor_mz": round(precursor_mz, 4) if precursor_mz > 0 else "-",
            "precursor_z": precursor_charge if precursor_charge > 0 else "-",
            "product_mz": round(product_mz, 4) if product_mz > 0 else "-",
            "rt_min": round(rt_min, 2),
            "rt_max": round(rt_max, 2),
            "n_points": len(rt_array),
            "max_int": f"{max_intensity:.2e}",
            "total_int": f"{total_intensity:.2e}",
        })

        # Store data arrays
        chromatogram_data[idx] = (
            np.array(rt_array, dtype=np.float32),
            np.array(int_array, dtype=np.float32),
        )

    return chromatograms, chromatogram_data, len(chromatograms) > 0


def extract_ion_mobility_data(exp: MSExperiment) -> tuple[Optional[pd.DataFrame], Optional[str], str, float, float]:
    """Extract ion mobility data from spectra.

    Args:
        exp: MSExperiment object

    Returns:
        Tuple of (im_df, im_type, im_unit, im_min, im_max)
    """
    if exp is None:
        return None, None, "", 0.0, 1.0

    # Known IM array names
    im_array_names = [
        "ion mobility",
        "inverse reduced ion mobility",
        "drift time",
        "ion mobility drift time",
    ]

    # First pass: detect IM data
    detected_im_name = None
    for spec in exp:
        if spec.getMSLevel() != 1:
            continue
        float_arrays = spec.getFloatDataArrays()
        for fda in float_arrays:
            name = fda.getName().lower() if fda.getName() else ""
            for im_name in im_array_names:
                if im_name in name:
                    detected_im_name = fda.getName()
                    break
            if detected_im_name:
                break
        if detected_im_name:
            break

    if not detected_im_name:
        return None, None, "", 0.0, 1.0

    # Determine IM type and unit
    name_lower = detected_im_name.lower()
    if "inverse" in name_lower or "1/k0" in name_lower:
        im_type = "inverse_k0"
        im_unit = "Vs/cm2"
    elif "drift" in name_lower:
        im_type = "drift_time"
        im_unit = "ms"
    else:
        im_type = "ion_mobility"
        im_unit = ""

    # Second pass: extract all IM data
    all_mz = []
    all_im = []
    all_int = []

    for spec in exp:
        if spec.getMSLevel() != 1:
            continue

        mz_array, int_array = spec.get_peaks()
        if len(mz_array) == 0:
            continue

        # Find the IM array
        im_array = None
        float_arrays = spec.getFloatDataArrays()
        for fda in float_arrays:
            if fda.getName() == detected_im_name:
                im_array = np.array(fda.get_data(), dtype=np.float32)
                break

        if im_array is None or len(im_array) != len(mz_array):
            continue

        all_mz.append(mz_array)
        all_im.append(im_array)
        all_int.append(int_array)

    if not all_mz:
        return None, None, "", 0.0, 1.0

    # Concatenate all arrays
    mz_concat = np.concatenate(all_mz)
    im_concat = np.concatenate(all_im)
    int_concat = np.concatenate(all_int)

    # Create DataFrame
    im_df = pd.DataFrame({
        "mz": mz_concat,
        "im": im_concat,
        "intensity": int_concat,
    })
    im_df["log_intensity"] = np.log1p(im_df["intensity"])

    im_min = float(im_df["im"].min())
    im_max = float(im_df["im"].max())

    return im_df, im_type, im_unit, im_min, im_max


def extract_spectrum_metadata(exp: MSExperiment) -> list[dict[str, Any]]:
    """Extract spectrum metadata for the spectrum table.

    Args:
        exp: MSExperiment object

    Returns:
        List of spectrum metadata dicts
    """
    if exp is None:
        return []

    data = []
    for idx in range(exp.size()):
        spec = exp[idx]
        rt = spec.getRT()
        ms_level = spec.getMSLevel()
        mz_array, int_array = spec.get_peaks()
        n_peaks = len(mz_array)
        tic = float(np.sum(int_array)) if n_peaks > 0 else 0.0
        mz_min = float(mz_array.min()) if n_peaks > 0 else 0.0
        mz_max = float(mz_array.max()) if n_peaks > 0 else 0.0

        # Get precursor info for MS2+
        precursor_mz = None
        precursor_z = None
        if ms_level > 1:
            precursors = spec.getPrecursors()
            if precursors:
                precursor_mz = precursors[0].getMZ()
                precursor_z = precursors[0].getCharge()

        data.append({
            "idx": idx,
            "rt": round(rt, 2),
            "ms_level": ms_level,
            "n_peaks": n_peaks,
            "tic": f"{tic:.2e}",
            "mz_range": f"{mz_min:.1f}-{mz_max:.1f}" if n_peaks > 0 else "-",
            "precursor_mz": round(precursor_mz, 4) if precursor_mz else "-",
            "precursor_z": precursor_z if precursor_z else "-",
            "sequence": "-",
            "score": "-",
        })

    return data


def process_mzml_data(
    exp: MSExperiment,
    filepath: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Optional[MzMLData]:
    """Process parsed mzML data to extract peaks and create DataFrames.

    Args:
        exp: MSExperiment object from parse_mzml_file
        filepath: Path to the mzML file (for reference)
        progress_callback: Optional callback(message, progress) for progress updates

    Returns:
        MzMLData object or None if processing failed
    """
    try:
        if exp is None:
            return None

        total_peaks = sum(spec.size() for spec in exp)
        if total_peaks == 0:
            # No regular peaks - might be IM-only data, continue processing
            pass

        result = MzMLData(exp=exp, filepath=filepath)

        # First pass: detect FAIMS CVs
        if progress_callback:
            progress_callback("Detecting FAIMS CVs...", 0.05)

        cv_set = set()
        for spec in exp:
            if spec.getMSLevel() == 1:
                cv = get_cv_from_spectrum(spec)
                if cv is not None:
                    cv_set.add(cv)

        result.has_faims = len(cv_set) > 1
        result.faims_cvs = sorted(cv_set) if result.has_faims else []

        # Data structures for peak extraction
        rts = np.empty(total_peaks, dtype=np.float32) if total_peaks > 0 else np.array([], dtype=np.float32)
        mzs = np.empty(total_peaks, dtype=np.float32) if total_peaks > 0 else np.array([], dtype=np.float32)
        intensities = np.empty(total_peaks, dtype=np.float32) if total_peaks > 0 else np.array([], dtype=np.float32)
        cvs = np.empty(total_peaks, dtype=np.float32) if result.has_faims and total_peaks > 0 else None

        # TIC data
        tic_rts = []
        tic_intensities = []
        faims_tic_data = {cv: {"rt": [], "int": []} for cv in result.faims_cvs} if result.has_faims else {}

        if progress_callback:
            progress_callback("Extracting peaks...", 0.1)

        idx = 0
        ms1_count = 0
        total_ms1 = sum(1 for spec in exp if spec.getMSLevel() == 1)

        for spec in exp:
            if spec.getMSLevel() != 1:
                continue

            ms1_count += 1
            if progress_callback and ms1_count % 100 == 0:
                progress = 0.1 + 0.6 * (ms1_count / max(total_ms1, 1))
                progress_callback(f"Extracting peaks... {ms1_count:,}/{total_ms1:,}", progress)

            rt = spec.getRT()
            mz_array, int_array = spec.get_peaks()
            n = len(mz_array)

            cv = get_cv_from_spectrum(spec) if result.has_faims else None

            if n > 0 and total_peaks > 0:
                rts[idx : idx + n] = rt
                mzs[idx : idx + n] = mz_array
                intensities[idx : idx + n] = int_array
                if result.has_faims and cv is not None:
                    cvs[idx : idx + n] = cv
                idx += n

                # TIC
                tic_sum = float(np.sum(int_array))
                tic_rts.append(rt)
                tic_intensities.append(tic_sum)

                # Per-CV TIC
                if result.has_faims and cv is not None:
                    faims_tic_data[cv]["rt"].append(rt)
                    faims_tic_data[cv]["int"].append(tic_sum)

        if total_peaks > 0:
            rts = rts[:idx]
            mzs = mzs[:idx]
            intensities = intensities[:idx]
            if result.has_faims:
                cvs = cvs[:idx]

        if progress_callback:
            progress_callback("Building TIC...", 0.75)

        # Store TIC data
        result.tic_rt = np.array(tic_rts, dtype=np.float32)
        result.tic_intensity = np.array(tic_intensities, dtype=np.float32)

        # Store per-CV TIC data
        for cv in result.faims_cvs:
            result.faims_tic[cv] = (
                np.array(faims_tic_data[cv]["rt"], dtype=np.float32),
                np.array(faims_tic_data[cv]["int"], dtype=np.float32),
            )

        if progress_callback:
            progress_callback("Extracting chromatograms...", 0.77)

        # Extract chromatograms
        result.chromatograms, result.chromatogram_data, result.has_chromatograms = extract_chromatograms(exp)

        if progress_callback:
            progress_callback("Extracting ion mobility data...", 0.78)

        # Extract ion mobility data
        im_df, im_type, im_unit, im_min, im_max = extract_ion_mobility_data(exp)
        result.im_df = im_df
        result.im_type = im_type
        result.im_unit = im_unit
        result.im_min = im_min
        result.im_max = im_max
        result.has_ion_mobility = im_df is not None

        if progress_callback:
            progress_callback("Extracting spectrum metadata...", 0.8)

        # Extract spectrum metadata
        result.spectrum_data = extract_spectrum_metadata(exp)

        if progress_callback:
            progress_callback("Creating DataFrame...", 0.85)

        # Create main DataFrame
        if idx > 0:
            result.df = pd.DataFrame({"rt": rts, "mz": mzs, "intensity": intensities})
            if result.has_faims:
                result.df["cv"] = cvs
            result.df["log_intensity"] = np.log1p(result.df["intensity"])

            # Set bounds from peak data
            result.rt_min = float(result.df["rt"].min())
            result.rt_max = float(result.df["rt"].max())
            result.mz_min = float(result.df["mz"].min())
            result.mz_max = float(result.df["mz"].max())

            # Create per-CV DataFrames for FAIMS view
            if result.has_faims:
                for cv in result.faims_cvs:
                    cv_df = result.df[result.df["cv"] == cv].copy()
                    result.faims_data[cv] = cv_df
        else:
            # No regular peak data - create empty DataFrame
            result.df = pd.DataFrame({"rt": [], "mz": [], "intensity": [], "log_intensity": []})

        # Update mz bounds from IM data if not set
        if result.has_ion_mobility and result.im_df is not None:
            im_mz_min = float(result.im_df["mz"].min())
            im_mz_max = float(result.im_df["mz"].max())
            if result.mz_min == 0 or im_mz_min < result.mz_min:
                result.mz_min = im_mz_min
            if result.mz_max == 0 or im_mz_max > result.mz_max:
                result.mz_max = im_mz_max

            # Also update rt bounds from spectrum metadata if available
            if result.spectrum_data:
                rts_from_meta = [s["rt"] for s in result.spectrum_data if s["rt"] > 0]
                if rts_from_meta:
                    if result.rt_min == 0:
                        result.rt_min = min(rts_from_meta)
                    if result.rt_max <= result.rt_min:
                        result.rt_max = max(rts_from_meta)

        if progress_callback:
            progress_callback("Finalizing...", 0.95)

        return result

    except Exception as e:
        import traceback
        print(f"Error processing mzML: {e}")
        traceback.print_exc()
        return None


def load_mzml(
    filepath: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Optional[MzMLData]:
    """Load and process an mzML file.

    Args:
        filepath: Path to the mzML file
        progress_callback: Optional callback(message, progress) for progress updates

    Returns:
        MzMLData object or None if loading failed
    """
    exp = parse_mzml_file(filepath)
    if exp is None:
        return None
    return process_mzml_data(exp, filepath, progress_callback)


def load_featuremap(filepath: str) -> Optional[FeatureData]:
    """Load a featureXML file.

    Args:
        filepath: Path to the featureXML file

    Returns:
        FeatureData object or None if loading failed
    """
    try:
        filename = Path(filepath).name
        print(f"Loading features from {filename}...")

        feature_map = FeatureMap()
        FeatureXMLFile().load(filepath, feature_map)

        result = FeatureData(feature_map=feature_map, filepath=filepath)

        # Extract feature metadata
        for idx, feature in enumerate(feature_map):
            rt = feature.getRT()
            mz = feature.getMZ()
            intensity = feature.getIntensity()
            charge = feature.getCharge()

            # Get convex hull for RT/mz range
            hulls = feature.getConvexHulls()
            hull_points = []
            if hulls:
                pts = hulls[0].getHullPoints()
                # getHullPoints() returns a numpy array of [rt, mz] pairs
                for pt in pts:
                    hull_points.append((float(pt[0]), float(pt[1])))

            if hull_points:
                rt_min = min(p[0] for p in hull_points)
                rt_max = max(p[0] for p in hull_points)
                mz_min = min(p[1] for p in hull_points)
                mz_max = max(p[1] for p in hull_points)
                rt_width = rt_max - rt_min
                mz_width = mz_max - mz_min
            else:
                rt_width = 0
                mz_width = 0

            result.features.append({
                "idx": idx,
                "rt": round(rt, 2),
                "mz": round(mz, 4),
                "intensity": f"{intensity:.2e}",
                "charge": charge if charge > 0 else "-",
                "rt_width": round(rt_width, 2) if rt_width > 0 else "-",
                "mz_width": round(mz_width, 4) if mz_width > 0 else "-",
            })

        print(f"Loaded {len(result.features)} features")
        return result

    except Exception as e:
        print(f"Error loading featureXML: {e}")
        return None


def load_idxml(filepath: str) -> Optional[IdXMLData]:
    """Load an idXML file.

    Args:
        filepath: Path to the idXML file

    Returns:
        IdXMLData object or None if loading failed
    """
    try:
        filename = Path(filepath).name
        print(f"Loading identifications from {filename}...")

        peptide_ids = []
        protein_ids = []
        IdXMLFile().load(filepath, protein_ids, peptide_ids)

        result = IdXMLData(
            peptide_ids=peptide_ids,
            protein_ids=protein_ids,
            filepath=filepath,
        )

        # Discover meta value keys
        meta_keys = set()
        for pep_id in peptide_ids:
            for hit in pep_id.getHits():
                keys = []
                hit.getKeys(keys)
                meta_keys.update(keys)
        result.meta_keys = sorted(meta_keys)

        # Extract ID metadata
        for idx, pep_id in enumerate(peptide_ids):
            rt = pep_id.getRT()
            mz = pep_id.getMZ()
            hits = pep_id.getHits()

            if hits:
                best_hit = hits[0]
                sequence = str(best_hit.getSequence())
                score = best_hit.getScore()
                charge = best_hit.getCharge()

                result.id_data.append({
                    "idx": idx,
                    "rt": round(rt, 2),
                    "mz": round(mz, 4),
                    "sequence": sequence,
                    "score": round(score, 4) if score else "-",
                    "charge": charge if charge > 0 else "-",
                    "n_hits": len(hits),
                })

        print(f"Loaded {len(result.id_data)} peptide identifications")
        return result

    except Exception as e:
        print(f"Error loading idXML: {e}")
        return None
