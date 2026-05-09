# Maintainability Audit Standard

This project uses ISO/IEC 25010 maintainability as the category model.

## Definition

Maintainability is the degree to which a system can be effectively and efficiently modified to improve it, correct it, or adapt it to changes in environment and requirements.

## Categories

| Category | Audit Question |
|---|---|
| Modularity | Can changes stay local, or does one change ripple through unrelated areas? |
| Reusability | Are useful components reusable without dragging along accidental coupling? |
| Analyzability | Can a developer quickly understand impact, diagnose issues, and find what must change? |
| Modifiability | Can changes be made without introducing defects or degrading quality? |
| Testability | Can meaningful behavior be verified with local, repeatable tests? |

## Scoring

Each category can be scored from 0 to 5 during a human audit.

| Score | Meaning |
|---:|---|
| 5 | Strong. Change is localized, tested, and easy to reason about. |
| 4 | Good. Minor issues exist but do not materially slow normal changes. |
| 3 | Usable. Change is possible, but developers need caution or repo-specific knowledge. |
| 2 | Fragile. Changes are slow, risky, or require broad context. |
| 1 | Poor. Frequent regressions, unclear ownership, weak tests, or heavy coupling. |
| 0 | Unmaintainable in this area. Safe change is not realistic without remediation. |

## CI Role

CI should not pretend to fully grade maintainability by itself.

CI should:

- detect obvious hotspots
- enforce hard gates
- produce a report for review
- stop new severe maintainability regressions

Human review should:

- judge architecture fit
- judge whether complexity is accidental or inherent
- judge whether tests cover meaningful behavior
- decide remediation priority

## References

- ISO/IEC 25010 maintainability: https://iso25000.com/index.php/en/iso-25000standards/iso-25010/57-maintainability
- SonarQube metrics: https://docs.sonarsource.com/sonarqube/latest/user-guide/code-metrics/metrics-definition/
- Code Climate maintainability: https://docs.codeclimate.com/docs/maintainability
- Code Climate default thresholds: https://docs.codeclimate.com/docs/default-analysis-configuration
- ESLint complexity rule: https://eslint.org/docs/latest/rules/complexity
- Radon metrics: https://radon.readthedocs.io/en/latest/intro.html
- Semgrep docs: https://semgrep.dev/docs/
