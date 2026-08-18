# Rule Catalog

## Dispositions
| Disposition | Meaning |
|---|---|
| `auto_fix` | Verified exact replacement candidate; execution requires preflight. |
| `comment` | Unresolved editorial issue; comment only after eligibility and anchor preflight. |
| `report_only` | Retained in JSON but never comments automatically. |
| `disabled` | Not run operationally because the program cannot verify it. |
| `manual` | Human QC outside automated audit scope. |

## Initial Operational Policy
| Rule | Guide area | Disposition | Comment behavior |
|---|---|---|---|
| `Clinical.UnitNonbreakingSpace` | 8.3 | auto_fix | one summary after verified fixes |
| `Clinical.MathOperatorSpacing` | 8.1 | auto_fix | one summary after verified fixes |
| `Clinical.DottedAbbreviations` | 1/Appendix | auto_fix candidate | summary after verification |
| `Clinical.LabelCapitalization` | 4.0 | report_only | no Word edit until reliable anchor policy exists |
| `Clinical.EndOfTrial` | 3.1 | comment | aggregate at first eligible body occurrence |
| `Clinical.TrialIntervention` | 3.1 | comment | aggregate at first eligible body occurrence |
| `Clinical.AbbreviationUndefinedAtFirstUse` | 1.1 | comment | only eligible narrative locations |
| `Clinical.ForwardSlashReview` | 5.0 | report_only | no automatic comment |
| `Clinical.PlainLanguageAbbreviations` | 1/Appendix | report_only | no automatic comment |
| `Clinical.FigureVisualReview` | 9.2 | disabled | manual visual QC only |

The machine-readable authority remains `config/commentpolicy.json`.
