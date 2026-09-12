from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_business_concept_service,
    get_current_user,
    require_admin,
    require_admin_role,
)
from app.models.user import User
from app.schemas.business_concept import (
    BusinessConceptCreate,
    BusinessConceptAssetRead,
    BusinessConceptRead,
    BusinessConceptUpdate,
    ConceptRelationCreate,
    ConceptRelationRead,
)
from app.services.business_concept_service import BusinessConceptService

router = APIRouter(prefix="/business-concepts", tags=["business-concepts"])


@router.get("", response_model=list[BusinessConceptRead])
def list_business_concepts(
    include_inactive: bool = Query(default=False, alias="includeInactive"),
    _: User = Depends(get_current_user),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.list(include_inactive=include_inactive)


@router.get("/{concept_id}", response_model=BusinessConceptRead)
def get_business_concept(
    concept_id: str,
    _: User = Depends(get_current_user),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.get(concept_id)


@router.get("/{concept_id}/assets", response_model=list[BusinessConceptAssetRead])
def list_business_concept_assets(
    concept_id: str,
    _: User = Depends(require_admin_role),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.list_assets(concept_id)


@router.post("", response_model=BusinessConceptRead, status_code=status.HTTP_201_CREATED)
def create_business_concept(
    payload: BusinessConceptCreate,
    _: User = Depends(require_admin),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.create(payload)


@router.patch("/{concept_id}", response_model=BusinessConceptRead)
def update_business_concept(
    concept_id: str,
    payload: BusinessConceptUpdate,
    _: User = Depends(require_admin),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.update(concept_id, payload)


@router.post(
    "/{concept_id}/relations",
    response_model=ConceptRelationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_concept_relation(
    concept_id: str,
    payload: ConceptRelationCreate,
    _: User = Depends(require_admin),
    service: BusinessConceptService = Depends(get_business_concept_service),
):
    return service.add_relation(concept_id, payload)
