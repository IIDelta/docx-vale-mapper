# Rule Catalog

## Dispositions
| Disposition | Meaning |
|---|---|
| `auto_fix` | Deterministic exact replacement candidate; execution requires preflight verification. |
| `comment` | Unresolved editorial issue; comment inserted only after eligibility and anchor preflight. |
| `report_only` | Contextually dependent warnings that are retained in JSON but never auto-fixed or commented. |
| `disabled` | Not run operationally because the rule overlaps or cannot be fully verified. |
| `manual` | Human QC outside automated audit scope. |
| `deferred_scope` | Larger architectural validations deferred to future phases. |

## Complete Operational Policy

| Rule ID | Guide Section | Disposition | Severity | Test Coverage | Documented Rationale |
|---|---|---|---|---|---|
| `Clinical.DashSpacing` | 5.0 | auto_fix | error | Full | Enforces standard unspaced em-dash or spaced en-dash |
| `Clinical.DottedAbbreviations` | 1.0 | auto_fix | error | Full | Enforces standard un-dotted abbreviations |
| `Clinical.MathOperatorSpacing` | 8.0 | auto_fix | error | Full | Math operators should have spaces around them |
| `Clinical.MultiplePunctuationSpaces` | 5.0 | auto_fix | error | Full | Ensures no double spaces between sentences |
| `Clinical.UnitNonbreakingSpace` | 8.0 | auto_fix | error | Full | Adds non-breaking spaces between values and units |
| `Clinical.AbbreviationMissingFromList` | 1.0 | comment | error | Full | Abbreviations used must appear in the abbreviation list |
| `Clinical.AbbreviationUndefinedAtFirstUse` | 1.0 | comment | error | Full | First uses must be expanded |
| `Clinical.DateMonthAbbreviation` | 3.0 | comment | error | Full | Month should be 3 letters |
| `Clinical.DateMonthFirst` | 3.0 | comment | error | Full | Date should be DD MMM YYYY format |
| `Clinical.EndOfTrial` | 3.0 | comment | error | Full | Standard 'End of Trial' terminology required |
| `Clinical.LatinExpressions` | 10.0 | comment | error | Full | Latin abbreviations should not be italicized |
| `Clinical.ListCapitalization` | 6.0 | comment | error | Full | List items should start with uppercase |
| `Clinical.ListIntroduction` | 6.0 | comment | error | Full | Lists must be introduced with a colon |
| `Clinical.Participant` | 3.0 | comment | error | Full | 'Participant' instead of 'Subject' |
| `Clinical.PreferredWordChoices` | Appendix C | comment | error | Full | Enforces preferred clinical vocabulary |
| `Clinical.RadiolabelFormat` | 10.0 | comment | error | Full | Proper radiolabel superscripting |
| `Clinical.ScientificSpecies` | 10.0 | comment | error | Full | Species names must be italicized |
| `Clinical.TableHeadingCapitalization` | 9.0 | comment | error | Full | Table headings should be capitalized correctly |
| `Clinical.TableZeroFormat` | 9.0 | comment | error | Full | Tables should format zero correctly |
| `Clinical.TimeFormat` | 3.0 | comment | error | Full | Standard 24-hour time format required |
| `Clinical.TrialIntervention` | 3.0 | comment | error | Full | Use 'study intervention' terminology |
| `Clinical.AgeExpressions` | 7.0 | report_only | warning | Full | Age formats |
| `Clinical.AmericanSpellingReview` | 2.0 | report_only | warning | Full | Highlights British spellings |
| `Clinical.Ampersand` | 8.0 | report_only | warning | Full | Ampersands should be avoided in text |
| `Clinical.AppendixBReview` | Appendix B | report_only | warning | Full | Redundancy checks |
| `Clinical.AppendixCReview` | Appendix C | report_only | warning | Full | Word choice review |
| `Clinical.AppendixDReview` | Appendix D | report_only | warning | Full | Commonly misused words |
| `Clinical.BenefitRisk` | Appendix C | report_only | warning | Full | Benefit-risk terminology |
| `Clinical.CitationPlacement` | 11.0 | report_only | warning | Full | Citations before punctuation |
| `Clinical.ClinicalDescriptorCase` | 4.0 | report_only | warning | Full | Descriptor capitalization |
| `Clinical.CompoundFormatting` | 5.0 | report_only | warning | Full | Hyphenation of compounds |
| `Clinical.CompriseUsage` | Appendix D | report_only | warning | Full | 'Comprised of' is incorrect |
| `Clinical.ConfidenceIntervals` | 7.0 | report_only | warning | Full | Confidence interval spacing |
| `Clinical.DateNumeric` | 3.0 | report_only | warning | Full | Numeric date formats |
| `Clinical.EmailFormat` | 5.0 | report_only | warning | Full | Email addresses should be lowercase |
| `Clinical.Eponyms` | 2.0 | report_only | warning | Full | Nonpossessive eponyms |
| `Clinical.ForwardSlashReview` | 5.0 | report_only | warning | Full | Slashes require context review |
| `Clinical.GenericReferenceCase` | 4.0 | report_only | warning | Full | Generic references should be lowercase |
| `Clinical.HeadingTitleCase` | 4.0 | report_only | warning | Full | Headings should use Title Case |
| `Clinical.InclusiveLanguageReview` | 3.0 | report_only | warning | Full | Inclusive language guidelines |
| `Clinical.LabelCapitalization` | 4.0 | report_only | warning | Full | Labels followed by numbers |
| `Clinical.LeanPhrases` | Appendix B | report_only | warning | Full | Wordiness review |
| `Clinical.NumberGrouping` | 7.0 | report_only | warning | Full | Large numbers should use commas |
| `Clinical.NumeralApostrophes` | 5.0 | report_only | warning | Full | No apostrophes for decades |
| `Clinical.NumeralAtSentenceStart` | 7.0 | report_only | warning | Full | Sentences should not start with numbers |
| `Clinical.NumericRatioFormat` | 7.0 | report_only | warning | Full | Ratios should use colon |
| `Clinical.PersonFirstLanguage` | 3.0 | report_only | warning | Full | Use person-first language |
| `Clinical.PlainLanguageAbbreviations` | 1.0 | report_only | warning | Full | Plain language terms |
| `Clinical.ProseRanges` | 7.0 | report_only | warning | Full | 'to' instead of hyphen in prose ranges |
| `Clinical.PValueFormat` | 7.0 | report_only | warning | Full | p-values should be italicized |
| `Clinical.Redundancy` | Appendix B | report_only | warning | Full | Avoid redundant phrases |
| `Clinical.ReferenceLabels` | 11.0 | report_only | warning | Full | Reference labeling |
| `Clinical.ScheduleOfActivities` | Appendix C | report_only | warning | Full | SOA terminology |
| `Clinical.SexIdentityReview` | 3.0 | report_only | warning | Full | Sex vs gender terms |
| `Clinical.SymbolSpacing` | 8.0 | report_only | warning | Full | Spacing around symbols |
| `Clinical.TrademarkSymbols` | 8.0 | report_only | warning | Full | First-use trademarking |
| `Clinical.TreatmentFailure` | 3.0 | report_only | warning | Full | Do not use 'treatment failure' |
| `Clinical.TrialAliasFormat` | 11.0 | report_only | warning | Full | Trial alias formats |
| `Clinical.TrialNumber` | Appendix C | report_only | warning | Full | Trial number formatting |

The machine-readable authority remains `config/commentpolicy.json`.
