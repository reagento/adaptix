import pytest

from dataclass_factory_30.feature_requirement import HAS_ANNOTATED, PythonVersionRequirement


class PytestVersionMarker:
    def __init__(self, requirement: PythonVersionRequirement):
        self.requirement = requirement

    def __call__(self, func):
        ver_str = '.'.join(map(str, self.requirement.min_version))

        return pytest.mark.skipif(
            not self.requirement,
            reason=f'Need Python >= {ver_str}'
        )(func)


requires_annotated = PytestVersionMarker(HAS_ANNOTATED)
