"""
backend/services/multimodal/image_catalog.py

Pathology Image Catalog & Metadata Registry.
Indexes reference histology slides, immunohistochemistry panels, and gross pathology specimens.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from backend.services.multimodal.models import (
    MagnificationLevel,
    PathologyImageAsset,
    StainType,
)


class PathologyImageCatalog:
    """
    Registry and retrieval engine for pathology histology images.
    """

    def __init__(self):
        self._catalog: Dict[str, PathologyImageAsset] = {}
        self._seed_default_catalog()

    def _seed_default_catalog(self):
        """Seeds canonical Robbins pathology reference image assets."""
        seeds = [
            PathologyImageAsset(
                image_id="img-breast-her2-3plus",
                title="Invasive Breast Carcinoma — HER2/neu 3+ Overexpression",
                file_path="/assets/images/pathology/breast/her2_3plus_ihc.png",
                stain_type=StainType.IHC_HER2,
                magnification=MagnificationLevel.HIGH_40X,
                organ_system="Breast",
                diagnosis="Invasive Ductal Carcinoma (HER2-positive)",
                source_citation="Robbins & Cotran Pathologic Basis of Disease, 11th Ed., p. 961, Fig. 23.19",
                caption="Intense, circumferential, complete membranous staining in >10% of invasive tumor cells (IHC Score 3+). Confirmatory ISH is not required.",
                diagnostic_features=[
                    "Circumferential membrane staining",
                    "Strong intensity (3+)",
                    ">10% contiguous invasive cells",
                    "Candidate for targeted anti-HER2 trastuzumab therapy",
                ],
            ),
            PathologyImageAsset(
                image_id="img-hodgkin-reed-sternberg",
                title="Classical Hodgkin Lymphoma — Diagnostic Reed-Sternberg Cell",
                file_path="/assets/images/pathology/hematolymphoid/reed_sternberg_he.png",
                stain_type=StainType.HE,
                magnification=MagnificationLevel.HIGH_40X,
                organ_system="Hematolymphoid",
                diagnosis="Classical Hodgkin Lymphoma (Nodular Sclerosis)",
                source_citation="Robbins & Cotran Pathologic Basis of Disease, 11th Ed., p. 582, Fig. 13.15",
                caption="Binucleated Reed-Sternberg cell displaying prominent inclusion-like owl-eye eosinophilic nucleoli surrounded by reactive inflammatory infiltrate of lymphocytes, eosinophils, and plasma cells.",
                diagnostic_features=[
                    "Binucleated mirror-image 'owl-eye' morphology",
                    "Eosinophilic macronucleoli with clear halo",
                    "CD30+ and CD15+ on immunohistochemistry",
                    "Abundant reactive inflammatory background",
                ],
            ),
            PathologyImageAsset(
                image_id="img-amyloid-congo-red-polarized",
                title="Renal Amyloidosis — Congo Red Apple-Green Birefringence",
                file_path="/assets/images/pathology/renal/amyloid_congo_red_polarized.png",
                stain_type=StainType.CONGO_RED,
                magnification=MagnificationLevel.MED_20X,
                organ_system="Kidney",
                diagnosis="Renal Amyloidosis (AL / AA)",
                source_citation="Robbins & Cotran Pathologic Basis of Disease, 11th Ed., p. 240, Fig. 6.30",
                caption="Glomerular and arteriolar amyloid deposits demonstrating pathognomonic apple-green birefringence under cross-polarized light microscopy following Congo Red staining.",
                diagnostic_features=[
                    "Amorphous acellular eosinophilic deposits on H&E",
                    "Salmon-pink on routine light Congo Red",
                    "Apple-green birefringence under polarized light",
                    "Cross-beta pleated sheet fibrillar ultrastructure",
                ],
            ),
            PathologyImageAsset(
                image_id="img-cml-bone-marrow-hypercellular",
                title="Chronic Myeloid Leukemia — Hypercellular Bone Marrow",
                file_path="/assets/images/pathology/hematolymphoid/cml_bone_marrow.png",
                stain_type=StainType.HE,
                magnification=MagnificationLevel.LOW_10X,
                organ_system="Bone Marrow",
                diagnosis="Chronic Myeloid Leukemia (Chronic Phase)",
                source_citation="Robbins & Cotran Pathologic Basis of Disease, 11th Ed., p. 595, Fig. 13.24",
                caption="100% cellular bone marrow with marked granulocytic proliferation, increased dwarf megakaryocytes with hypolobated nuclei, and <5% myeloblasts.",
                diagnostic_features=[
                    "Marked myeloid hyperplasia with left shift",
                    "Small dwarf hypolobated megakaryocytes",
                    "Sea-blue histiocytes (Gaucher-like cells)",
                    "t(9;22)(q34;q11.2) BCR::ABL1 fusion hallmark",
                ],
            ),
        ]
        for asset in seeds:
            self._catalog[asset.image_id] = asset

    def get_image(self, image_id: str) -> Optional[PathologyImageAsset]:
        return self._catalog.get(image_id)

    def list_images(
        self,
        organ_system: Optional[str] = None,
        stain_type: Optional[StainType] = None,
        search: Optional[str] = None,
    ) -> List[PathologyImageAsset]:
        results = list(self._catalog.values())

        if organ_system:
            results = [img for img in results if img.organ_system.lower() == organ_system.lower()]

        if stain_type:
            results = [img for img in results if img.stain_type == stain_type]

        if search:
            q = search.lower()
            results = [
                img for img in results
                if q in img.title.lower() or q in img.diagnosis.lower() or q in img.caption.lower()
            ]

        return results

    def register_image(self, asset: PathologyImageAsset) -> None:
        self._catalog[asset.image_id] = asset


_catalog_instance: Optional[PathologyImageCatalog] = None


def get_image_catalog() -> PathologyImageCatalog:
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = PathologyImageCatalog()
    return _catalog_instance
