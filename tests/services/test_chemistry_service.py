import pytest

from app.services import chemistry_service
from app.services.chemistry_service import ChemistryService


@pytest.fixture(name="service")
def service_fixture() -> ChemistryService:
    return ChemistryService()


class TestSmilesToSvg:
    def test_valid_smiles_produces_non_empty_svg(
        self, service: ChemistryService
    ) -> None:
        # given
        smiles = "CCO"

        # when
        svg = service.smiles_to_svg(smiles)

        # then
        assert svg is not None
        assert svg.strip() != ""
        assert "<svg" in svg
        assert svg.rstrip().endswith("</svg>")

    def test_invalid_smiles_returns_none(self, service: ChemistryService) -> None:
        # when
        svg = service.smiles_to_svg("not-a-valid-smiles")

        # then
        assert svg is None

    def test_blank_smiles_returns_none(self, service: ChemistryService) -> None:
        # when
        svg = service.smiles_to_svg("")

        # then
        assert svg is None

    def test_returns_none_when_rdkit_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # given
        monkeypatch.setattr(chemistry_service, "_RDKIT_AVAILABLE", False)
        service = ChemistryService()

        # when
        svg = service.smiles_to_svg("CCO")

        # then
        assert svg is None
