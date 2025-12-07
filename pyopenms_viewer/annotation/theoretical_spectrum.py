"""Theoretical spectrum generation for peptide annotation."""

from pyopenms import AASequence, MSSpectrum, TheoreticalSpectrumGenerator


def generate_theoretical_spectrum(
    sequence: AASequence,
    charge: int,
) -> dict[str, list[tuple[float, str]]]:
    """Generate theoretical b/y ion spectrum for annotation.

    Uses pyOpenMS TheoreticalSpectrumGenerator to create a theoretical
    spectrum with b and y ions for the given peptide sequence.

    Args:
        sequence: AASequence object representing the peptide
        charge: Precursor charge state

    Returns:
        Dictionary with keys "b", "y", "other" containing lists of
        (m/z, ion_name) tuples for each ion type
    """
    tsg = TheoreticalSpectrumGenerator()
    spec = MSSpectrum()

    # Configure for b and y ions
    params = tsg.getParameters()
    params.setValue("add_b_ions", "true")
    params.setValue("add_y_ions", "true")
    params.setValue("add_a_ions", "false")
    params.setValue("add_c_ions", "false")
    params.setValue("add_x_ions", "false")
    params.setValue("add_z_ions", "false")
    params.setValue("add_metainfo", "true")
    tsg.setParameters(params)

    # Generate spectrum with charge states up to min(charge, 2)
    tsg.getSpectrum(spec, sequence, 1, min(charge, 2))

    ions = {"b": [], "y": [], "other": []}

    for i in range(spec.size()):
        mz = spec[i].getMZ()

        # Get ion annotation from metadata
        ion_name = ""
        if spec[i].metaValueExists("IonName"):
            ion_name = spec[i].getMetaValue("IonName")

        if ion_name.startswith("b"):
            ions["b"].append((mz, ion_name))
        elif ion_name.startswith("y"):
            ions["y"].append((mz, ion_name))
        else:
            ions["other"].append((mz, ion_name))

    return ions
