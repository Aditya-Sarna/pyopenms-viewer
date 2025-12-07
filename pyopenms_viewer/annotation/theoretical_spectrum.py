"""Theoretical spectrum generation for peptide annotation."""

from pyopenms import AASequence, MSSpectrum, TheoreticalSpectrumGenerator


def generate_theoretical_spectrum(
    sequence: AASequence,
    charge: int,
) -> dict[str, list[tuple[float, str]]]:
    """Generate theoretical b/y/a ion spectrum for annotation.

    Uses pyOpenMS TheoreticalSpectrumGenerator to create a theoretical
    spectrum with b, y, and a ions for the given peptide sequence.

    Args:
        sequence: AASequence object representing the peptide
        charge: Precursor charge state

    Returns:
        Dictionary with keys "b", "y", "a", "other" containing lists of
        (m/z, ion_name) tuples for each ion type
    """
    tsg = TheoreticalSpectrumGenerator()
    spec = MSSpectrum()

    # Configure for b, y, and a ions
    params = tsg.getParameters()
    params.setValue("add_b_ions", "true")
    params.setValue("add_y_ions", "true")
    params.setValue("add_a_ions", "true")
    params.setValue("add_c_ions", "false")
    params.setValue("add_x_ions", "false")
    params.setValue("add_z_ions", "false")
    params.setValue("add_metainfo", "true")
    tsg.setParameters(params)

    # Generate spectrum with charge states up to min(charge, 2)
    tsg.getSpectrum(spec, sequence, 1, min(charge, 2))

    ions = {"b": [], "y": [], "a": [], "other": []}

    # Get ion names from string data arrays
    ion_names = []
    string_arrays = spec.getStringDataArrays()
    for arr in string_arrays:
        arr_name = arr.getName()
        if arr_name == "IonNames" or arr_name == b"IonNames":
            for name in arr:
                if isinstance(name, bytes):
                    ion_names.append(name.decode("utf-8", errors="ignore"))
                else:
                    ion_names.append(name)
            break

    for i in range(spec.size()):
        mz = spec[i].getMZ()
        ion_name = ion_names[i] if i < len(ion_names) else ""

        if ion_name.startswith("b"):
            ions["b"].append((mz, ion_name))
        elif ion_name.startswith("y"):
            ions["y"].append((mz, ion_name))
        elif ion_name.startswith("a"):
            ions["a"].append((mz, ion_name))
        elif ion_name:
            ions["other"].append((mz, ion_name))

    return ions
