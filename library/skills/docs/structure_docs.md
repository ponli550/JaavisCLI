---
name: Documentation Structure
description: Standard Tiered Documentation Architecture for One-Army projects.
grade: A
tags: docs, structure, standard
pros:
  - "Scalable from Day 1 to Day 1000"
  - "Clear separation of concerns (Tutorials vs Reference)"
  - "Onboarding-friendly"
cons:
  - "Slight overhead for very small scripts"
---

# Documentation Structure

## Best Practice
Adopts the Diátaxis framework (Tutorials, How-To Guides, Explanation, Reference) adapted for "One-Army" teams.

### Tier 1: Onboarding (Root)
- `00-start-here.md`: The single entry point for new developers.
- `README.md`: High-level overview and badges.

### Tier 2: Explanation & Reference (Architecture)
- `docs/architecture/`: Long-term design docs.
- `docs/reference/`: API specs, Database schemas.

### Tier 3: How-To Guides (Operations)
- `docs/guides/`: Recipe-style guides (Deployment, Debugging).

## Snippet

```python
import os

def create_docs_structure():
    base = "docs"
    structure = {
        "": ["00-start-here.md"],
        "architecture": ["overview.md", "decisions/001-init.md"],
        "guides": ["deployment.md", "debugging.md"],
        "reference": ["api.md", "database.md"]
    }

    for folder, files in structure.items():
        path = os.path.join(base, folder)
        os.makedirs(path, exist_ok=True)
        for f in files:
            filepath = os.path.join(path, f)
            # Ensure directory for file exists (e.g. decisions/)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'a') as file:
                file.write(f"# {os.path.basename(f).replace('.md', '').capitalize()}\n\nTODO: Description\n")

    print(f"Documentation structure created in {base}/")

if __name__ == "__main__":
    create_docs_structure()
```
