"""Tests for the MS data loader module."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_data_loader import (
    MzMLData,
    FeatureData,
    IdXMLData,
    load_mzml,
    load_featuremap,
    load_idxml,
    parse_mzml_file,
    process_mzml_data,
    extract_chromatograms,
    extract_ion_mobility_data,
    extract_spectrum_metadata,
)


# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
BSA_MZML = TEST_DATA_DIR / "BSA1_F1.mzML"
BSA_FEATUREXML = TEST_DATA_DIR / "BSA1_F1.featureXML"
BSA_IDXML = TEST_DATA_DIR / "BSA1_F1.idXML"
IMS_MZML = TEST_DATA_DIR / "ims_example.mzML"


class TestMzMLLoading:
    """Tests for mzML file loading."""

    def test_parse_mzml_file_success(self):
        """Test that a valid mzML file can be parsed."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        exp = parse_mzml_file(str(BSA_MZML))
        assert exp is not None
        assert exp.size() > 0

    def test_parse_mzml_file_not_found(self):
        """Test that parsing a non-existent file returns None."""
        exp = parse_mzml_file("/nonexistent/path/file.mzML")
        assert exp is None

    def test_load_mzml_returns_data(self):
        """Test that load_mzml returns a valid MzMLData object."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        data = load_mzml(str(BSA_MZML))
        assert data is not None
        assert isinstance(data, MzMLData)
        assert data.exp is not None
        assert data.df is not None
        assert len(data.df) > 0

    def test_load_mzml_has_bounds(self):
        """Test that loaded data has proper RT and m/z bounds."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        data = load_mzml(str(BSA_MZML))
        assert data is not None
        assert data.rt_min < data.rt_max
        assert data.mz_min < data.mz_max
        assert data.rt_min >= 0
        assert data.mz_min >= 0

    def test_load_mzml_has_tic(self):
        """Test that loaded data has TIC arrays."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        data = load_mzml(str(BSA_MZML))
        assert data is not None
        assert data.tic_rt is not None
        assert data.tic_intensity is not None
        assert len(data.tic_rt) > 0
        assert len(data.tic_rt) == len(data.tic_intensity)

    def test_load_mzml_has_spectrum_metadata(self):
        """Test that loaded data has spectrum metadata."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        data = load_mzml(str(BSA_MZML))
        assert data is not None
        assert data.spectrum_data is not None
        assert len(data.spectrum_data) > 0
        # Check required fields in spectrum metadata
        first_spec = data.spectrum_data[0]
        assert "idx" in first_spec
        assert "rt" in first_spec
        assert "ms_level" in first_spec
        assert "n_peaks" in first_spec


class TestIMSLoading:
    """Tests for ion mobility mzML file loading."""

    def test_load_ims_mzml_success(self):
        """Test that IMS mzML file can be loaded without errors."""
        assert IMS_MZML.exists(), f"Test file not found: {IMS_MZML}"
        data = load_mzml(str(IMS_MZML))
        assert data is not None
        assert isinstance(data, MzMLData)

    def test_load_ims_mzml_has_ion_mobility(self):
        """Test that IMS file is detected as having ion mobility data."""
        assert IMS_MZML.exists(), f"Test file not found: {IMS_MZML}"
        data = load_mzml(str(IMS_MZML))
        assert data is not None
        assert data.has_ion_mobility is True
        assert data.im_df is not None
        assert len(data.im_df) > 0

    def test_load_ims_mzml_has_im_bounds(self):
        """Test that IMS data has proper IM bounds."""
        assert IMS_MZML.exists(), f"Test file not found: {IMS_MZML}"
        data = load_mzml(str(IMS_MZML))
        assert data is not None
        assert data.has_ion_mobility
        assert data.im_min < data.im_max
        assert data.im_min >= 0

    def test_load_ims_mzml_has_mz_bounds(self):
        """Test that IMS data has proper m/z bounds (from IM dataframe)."""
        assert IMS_MZML.exists(), f"Test file not found: {IMS_MZML}"
        data = load_mzml(str(IMS_MZML))
        assert data is not None
        # Even if there's no regular peak data, mz bounds should be set from IM data
        assert data.mz_min < data.mz_max
        assert data.mz_min >= 0

    def test_load_ims_mzml_no_division_by_zero(self):
        """Test that loading IMS data doesn't cause division by zero.

        This test verifies that bounds are properly set even for IM-only data.
        """
        assert IMS_MZML.exists(), f"Test file not found: {IMS_MZML}"
        data = load_mzml(str(IMS_MZML))
        assert data is not None

        # Check that all ranges are non-zero to prevent division by zero
        mz_range = data.mz_max - data.mz_min
        assert mz_range > 0, f"mz_range is zero: {data.mz_min} - {data.mz_max}"

        im_range = data.im_max - data.im_min
        assert im_range > 0, f"im_range is zero: {data.im_min} - {data.im_max}"


class TestChromatogramExtraction:
    """Tests for chromatogram extraction."""

    def test_extract_chromatograms_from_bsa(self):
        """Test chromatogram extraction from BSA file."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        exp = parse_mzml_file(str(BSA_MZML))
        assert exp is not None
        chroms, chrom_data, has_chroms = extract_chromatograms(exp)
        # BSA file may or may not have chromatograms
        assert isinstance(chroms, list)
        assert isinstance(chrom_data, dict)

    def test_extract_chromatograms_metadata(self):
        """Test that chromatogram metadata has required fields."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        data = load_mzml(str(BSA_MZML))
        assert data is not None
        if data.has_chromatograms and data.chromatograms:
            first_chrom = data.chromatograms[0]
            assert "idx" in first_chrom
            assert "native_id" in first_chrom
            assert "is_tic" in first_chrom
            assert "type" in first_chrom


class TestFeatureXMLLoading:
    """Tests for featureXML file loading."""

    def test_load_featuremap_success(self):
        """Test that a valid featureXML file can be loaded."""
        assert BSA_FEATUREXML.exists(), f"Test file not found: {BSA_FEATUREXML}"
        data = load_featuremap(str(BSA_FEATUREXML))
        assert data is not None
        assert isinstance(data, FeatureData)
        assert data.feature_map is not None
        assert len(data.features) > 0

    def test_load_featuremap_metadata(self):
        """Test that feature metadata has required fields."""
        assert BSA_FEATUREXML.exists(), f"Test file not found: {BSA_FEATUREXML}"
        data = load_featuremap(str(BSA_FEATUREXML))
        assert data is not None
        if data.features:
            first_feat = data.features[0]
            assert "idx" in first_feat
            assert "rt" in first_feat
            assert "mz" in first_feat
            assert "intensity" in first_feat

    def test_load_featuremap_not_found(self):
        """Test that loading a non-existent file returns None."""
        data = load_featuremap("/nonexistent/path/file.featureXML")
        assert data is None


class TestIdXMLLoading:
    """Tests for idXML file loading."""

    def test_load_idxml_success(self):
        """Test that a valid idXML file can be loaded."""
        assert BSA_IDXML.exists(), f"Test file not found: {BSA_IDXML}"
        data = load_idxml(str(BSA_IDXML))
        assert data is not None
        assert isinstance(data, IdXMLData)
        assert len(data.peptide_ids) > 0

    def test_load_idxml_metadata(self):
        """Test that ID metadata has required fields."""
        assert BSA_IDXML.exists(), f"Test file not found: {BSA_IDXML}"
        data = load_idxml(str(BSA_IDXML))
        assert data is not None
        if data.id_data:
            first_id = data.id_data[0]
            assert "idx" in first_id
            assert "rt" in first_id
            assert "mz" in first_id
            assert "sequence" in first_id

    def test_load_idxml_not_found(self):
        """Test that loading a non-existent file returns None."""
        data = load_idxml("/nonexistent/path/file.idXML")
        assert data is None


class TestProgressCallback:
    """Tests for progress callback functionality."""

    def test_load_mzml_with_progress_callback(self):
        """Test that progress callback is called during loading."""
        assert BSA_MZML.exists(), f"Test file not found: {BSA_MZML}"
        progress_messages = []

        def progress_callback(message: str, progress: float):
            progress_messages.append((message, progress))

        data = load_mzml(str(BSA_MZML), progress_callback=progress_callback)
        assert data is not None
        assert len(progress_messages) > 0
        # Check that progress increases
        progress_values = [p[1] for p in progress_messages]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1], "Progress should not decrease"
