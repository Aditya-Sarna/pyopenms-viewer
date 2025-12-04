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


class TestExternalFragmentAnnotations:
    """Tests for external fragment annotation parsing."""

    def test_parse_external_annotations_basic(self):
        """Test parsing basic fragment annotations."""
        import numpy as np
        from pyopenms_viewer import parse_external_fragment_annotations

        # Sample m/z array (experimental peaks)
        exp_mz = np.array([201.09, 272.12, 387.15, 501.19])

        # Sample fragment_annotation string (like from idXML)
        ann_str = '201.0867919921875,1.0,1,"b2+"|272.1239013671875,0.143,1,"b3+"'

        annotations = parse_external_fragment_annotations(ann_str, exp_mz, tolerance_da=0.05)

        assert len(annotations) == 2
        # First annotation should match peak at index 0 (201.09)
        assert annotations[0][0] == 0  # peak_index
        assert annotations[0][1] == "b2+"  # ion_name
        assert annotations[0][2] == "b"  # ion_type

        # Second annotation should match peak at index 1 (272.12)
        assert annotations[1][0] == 1
        assert annotations[1][1] == "b3+"
        assert annotations[1][2] == "b"

    def test_parse_external_annotations_various_ion_types(self):
        """Test parsing annotations with various ion types."""
        import numpy as np
        from pyopenms_viewer import parse_external_fragment_annotations

        exp_mz = np.array([147.11, 201.09, 712.36, 112.05])

        ann_str = (
            '147.112884521484375,0.075,1,"y1+"|'
            '201.0867919921875,1.0,1,"b2+"|'
            '712.36236572265625,0.394,1,"y5+U\'-H2O+"|'
            '112.050621032714844,0.028,1,"MI:C\'+"|'
        )

        annotations = parse_external_fragment_annotations(ann_str, exp_mz, tolerance_da=0.05)

        assert len(annotations) == 4

        # Check ion types are correctly identified
        ion_types = {ann[1]: ann[2] for ann in annotations}
        assert ion_types["y1+"] == "y"
        assert ion_types["b2+"] == "b"
        assert ion_types["y5+U'-H2O+"] == "y"  # Modified y-ion
        assert ion_types["MI:C'+"] == "unknown"  # Immonium ion

    def test_parse_external_annotations_empty_input(self):
        """Test parsing with empty inputs."""
        import numpy as np
        from pyopenms_viewer import parse_external_fragment_annotations

        exp_mz = np.array([100.0, 200.0])

        # Empty string
        assert parse_external_fragment_annotations("", exp_mz) == []

        # Empty m/z array
        assert parse_external_fragment_annotations("100.0,1.0,1,\"b1+\"", np.array([])) == []

    def test_parse_external_annotations_tolerance(self):
        """Test that tolerance is respected."""
        import numpy as np
        from pyopenms_viewer import parse_external_fragment_annotations

        exp_mz = np.array([200.0, 300.0])

        ann_str = '200.1,1.0,1,"b2+"'  # 0.1 Da away from 200.0

        # With 0.05 Da tolerance - should NOT match
        annotations = parse_external_fragment_annotations(ann_str, exp_mz, tolerance_da=0.05)
        assert len(annotations) == 0

        # With 0.15 Da tolerance - should match
        annotations = parse_external_fragment_annotations(ann_str, exp_mz, tolerance_da=0.15)
        assert len(annotations) == 1
        assert annotations[0][0] == 0  # Matched to first peak

    def test_get_external_peak_annotations_from_idxml(self):
        """Test getting external annotations using getPeakAnnotations() API from real idXML data."""
        import numpy as np
        from pyopenms import IdXMLFile
        from pyopenms_viewer import get_external_peak_annotations

        # Load test file with external fragment annotations
        external_ann_idxml = TEST_DATA_DIR / "external_fragment_annotations.idXML"
        assert external_ann_idxml.exists(), f"Test file not found: {external_ann_idxml}"

        pep_ids = []
        prot_ids = []
        IdXMLFile().load(str(external_ann_idxml), prot_ids, pep_ids)

        assert len(pep_ids) > 0, "Should have peptide IDs"

        hits = pep_ids[0].getHits()
        assert len(hits) > 0, "Should have peptide hits"

        best_hit = hits[0]

        # Create a mock experimental m/z array based on known annotation m/z values
        # from the test file (b2+ at 201.087, y1+ at 147.113, etc.)
        exp_mz = np.array([112.05, 147.11, 201.09, 272.12, 387.15, 712.36])

        annotations = get_external_peak_annotations(best_hit, exp_mz, tolerance_da=0.05)

        # Should have matched some annotations
        assert len(annotations) > 0, "Should have found external annotations"

        # Check we got expected ion types
        ion_types = set(ann[2] for ann in annotations)
        assert "b" in ion_types or "y" in ion_types, "Should have b or y ions"

        # Check annotation names are extracted correctly
        ion_names = [ann[1] for ann in annotations]
        assert any("b2+" in name for name in ion_names), "Should have b2+ annotation"
