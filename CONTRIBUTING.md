# Contributing Guidelines — GRC-DEVSECOPS-PFS

Thank you for contributing to **GRC-DEVSECOPS-PFS**! To maintain code quality, security, and traceability across our microservices (`auth_service`, `task_service`), `frontend`, and `infra/terraform` stack, please follow the workflow below.

---

## 1. Branching Strategy & Naming Convention

* **Protected Branches:** Direct pushes and force pushes to `main` are **strictly prohibited**. All changes must go through a Pull Request (PR).
* **Base Branch:** Always create your working branch from the latest `develop` branch:
  ```bash
  git checkout develop
  git pull origin develop
  git checkout -b scrum-<ticket-number>