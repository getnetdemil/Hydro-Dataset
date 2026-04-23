# Contributing to Hydro-Dataset

We welcome contributions from researchers and developers focused on Nordic hydrology and environmental modeling.

## Contribution Guidelines

1. **Modular Scripts**: New extraction or derivation logic should be added to the appropriate directory in `src/`.
2. **Reproducibility**: Ensure all scripts are self-contained and document their dependencies.
3. **Data Integrity**: Validate output datasets against known reference points where possible.
4. **Documentation**: Update `DATA_SOURCES.md` or `DERIVATION_METHODS.md` if you add new logic.

## Developing a New Module

1. Create a script in `src/extraction/` (for new sources) or `src/derivation/` (for new parameters).
2. Follow the standard configuration pattern by using `src/common/config.py`.
3. Add a unit test in `tests/` to verify your logic.
4. Register your script in the `pipelines/Makefile` for pipeline orchestration.
