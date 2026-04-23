# GitHub Collaboration & Workflow Rules

This document outlines the branching strategy and collaboration rules for the **Hydro-Dataset** project to ensure a stable, reproducible, and clean codebase.

## 1. Branching Strategy

The project uses a three-tier branching model:

### 1.1 `main` (Production Branch)
- **Purpose**: This is the "stable" and "production-ready" version of the dataset pipeline.
- **Protection**: 
    - **No direct pushes allowed.**
    - All changes must arrive via a Pull Request (PR) from the `experiment` branch.
    - Code in `main` should always be in a runnable state and correspond to published results or workshop submissions.

### 1.2 `experiment` (Integration Branch)
- **Purpose**: A medium-stability branch where features are integrated and tested together before moving to `main`.
- **Workflow**:
    - Acts as the staging area for the next "release."
    - Pull Requests from `feature/*` branches are merged here first.
    - Integration tests and data validation checks are performed here.

### 1.3 `feature/*` (Development Branches)
- **Purpose**: All new development, bug fixes, or new data source extractions.
- **Naming Convention**: `feature/name-of-task` (e.g., `feature/smhi-api-fix`, `feature/derive-swe-model`).
- **Workflow**: 
    - Create a new feature branch for every task.
    - Push code frequently to your feature branch.
    - Once the feature is complete and local tests pass, open a PR to merge into `experiment`.

---

## 2. Collaboration Workflow (Step-by-Step)

1.  **Start a Task**: Synchronize your local repo and create a new branch from `experiment`.
    ```bash
    git checkout experiment
    git pull origin experiment
    git checkout -b feature/your-feature-name
    ```
2.  **Develop & Commit**: Follow the project's modular standards. Ensure your code is documented.
3.  **Push Changes**: 
    ```bash
    git push origin feature/your-feature-name
    ```
4.  **Open a Pull Request**:
    - Targeted branch: **`experiment`** (NOT `main`).
    - Describe what the change does and provide a sample of the output data if applicable.
5.  **Review & Merge**: At least one other collaborator should review the PR. Once approved, it is merged into `experiment`.
6.  **Promotion to Main**: Periodically, once `experiment` is deemed stable and verified, a PR will be opened from `experiment` to `main`.

---

## 3. Code Quality Rules

- **Modular Logic**: Never mix data extraction logic with parameter derivation in the same script.
- **Documentation**: Every new script must have a docstring explaining its purpose, inputs, and outputs.
- **No Large Data in Git**: Never commit raw data files (`.csv`, `.grib`, `.nc`) to the repository. Use the `data/sample/` folder for tiny test files only.
- **Environment Variables**: Never commit `.env` files. Always update `.env.example` if you add new configuration keys.

---

## 4. Protected Branch Settings (GitHub UI)
*Administrators should enforce the following in GitHub Repository Settings:*
- **Require pull request reviews before merging.**
- **Require status checks to pass before merging** (once CI/CD is implemented).
- **Restrict pushes** to `main` and `experiment`.
