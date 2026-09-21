from src.domain.ai.spec import StructuredSpecification, TaskType


def classify_task(spec: StructuredSpecification) -> TaskType:
    """Prefer parametric CAD whenever the user gave exact dimensions.

    Generative 3D is reserved for requests with no precise dimensional
    requirement (ARCHITECTURE.md, section 10) — a generative model can look
    good but won't hit an exact measurement, so it never gets picked when a
    box/plate/keychain-shaped spec with real numbers is available.
    """
    if spec.dimensions.is_fully_specified():
        return TaskType.PARAMETRIC_CAD
    return TaskType.TEXT_TO_GENERATIVE_3D
