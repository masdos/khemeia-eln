from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D

    _RDKIT_AVAILABLE = True
except ImportError:
    _RDKIT_AVAILABLE = False

_SVG_WIDTH = 400
_SVG_HEIGHT = 300


class ChemistryService:
    """Renders chemical structures from SMILES strings as inline SVG."""

    def smiles_to_svg(self, smiles: str) -> str | None:
        """Return an SVG rendering of a SMILES string, or None if unavailable."""
        if not _RDKIT_AVAILABLE:
            logger.warning("RDKit unavailable smiles_to_svg degraded smiles=%s", smiles)
            return None

        if not smiles or not smiles.strip():
            logger.debug("Blank SMILES ignored smiles=%s", smiles)
            return None

        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            logger.debug("Invalid SMILES ignored smiles=%s", smiles)
            return None

        rdDepictor.Compute2DCoords(molecule)
        drawer = rdMolDraw2D.MolDraw2DSVG(_SVG_WIDTH, _SVG_HEIGHT)
        rdMolDraw2D.PrepareAndDrawMolecule(drawer, molecule)
        drawer.FinishDrawing()

        svg = drawer.GetDrawingText()
        logger.debug("SMILES rendered as SVG smiles=%s", smiles)
        return svg
