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
| `Clinical.AbbreviationDeprecated` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AbbreviationListDuplicate` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AbbreviationListMissingDefinition` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AbbreviationListOrder` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AbbreviationMissingFromList` | 1.0 | comment | error | Full | Abbreviations used must appear in the abbreviation list |
| `Clinical.AbbreviationRedefinedInText` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AbbreviationUndefinedAtFirstUse` | 1.0 | comment | error | Full | First uses must be expanded |
| `Clinical.ActiveExternalLink` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AgeExpressions` | 7.0 | comment | warning | Full | Age formats |
| `Clinical.AmericanSpellingReview` | 2.0 | comment | warning | Full | Highlights British spellings |
| `Clinical.Ampersand` | 8.0 | comment | warning | Full | Ampersands should be avoided in text |
| `Clinical.AppendixBReview` | Appendix B | comment | warning | Full | Redundancy checks |
| `Clinical.AppendixCReview` | Appendix C | comment | warning | Full | Word choice review |
| `Clinical.AppendixDReview` | Appendix D | comment | warning | Full | Commonly misused words |
| `Clinical.AppendixElementPrefix` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.AppendixElementSequence` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.BenefitRisk` | Appendix C | comment | warning | Full | Benefit-risk terminology |
| `Clinical.CitationPlacement` | 11.0 | comment | warning | Full | Citations before punctuation |
| `Clinical.ClinicalDescriptorCase` | 4.0 | comment | warning | Full | Descriptor capitalization |
| `Clinical.CompoundFormatting` | 5.0 | comment | warning | Full | Hyphenation of compounds |
| `Clinical.CompriseUsage` | Appendix D | comment | warning | Full | 'Comprised of' is incorrect |
| `Clinical.ConfidenceIntervals` | 7.0 | comment | warning | Full | Confidence interval spacing |
| `Clinical.DashSpacing` | 5.0 | auto_fix | error | Full | Enforces standard unspaced em-dash or spaced en-dash |
| `Clinical.DateMonthAbbreviation` | 3.0 | comment | error | Full | Month should be 3 letters |
| `Clinical.DateMonthFirst` | 3.0 | comment | error | Full | Date should be DD MMM YYYY format |
| `Clinical.DateNumeric` | 3.0 | comment | warning | Full | Numeric date formats |
| `Clinical.DottedAbbreviations` | 1.0 | auto_fix | error | Full | Enforces standard un-dotted abbreviations |
| `Clinical.EmailFormat` | 5.0 | comment | warning | Full | Email addresses should be lowercase |
| `Clinical.EndOfTrial` | 3.0 | comment | error | Full | Standard 'End of Trial' terminology required |
| `Clinical.Eponyms` | 2.0 | comment | warning | Full | Nonpossessive eponyms |
| `Clinical.FigureCaptionMissing` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FigureDuplicateLabel` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FigureLabelPeriod` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FigureLabelSequence` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FigureTitleBelow` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteDesignatorSpacing` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteEndPunctuation` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteLetterSequence` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteOrder` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteSourceColon` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.FootnoteSymbolDesignator` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.ForwardSlashReview` | 5.0 | comment | warning | Full | Slashes require context review |
| `Clinical.GenericReferenceCase` | 4.0 | comment | warning | Full | Generic references should be lowercase |
| `Clinical.InclusiveLanguageReview` | 3.0 | comment | warning | Full | Inclusive language guidelines |
| `Clinical.ItalicRequired` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.LabelCapitalization` | 4.0 | comment | warning | Full | Labels followed by numbers |
| `Clinical.LeanPhrases` | Appendix B | comment | warning | Full | Wordiness review |
| `Clinical.ListIntroductionColon` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.ListItemCapitalization` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.ListItemEndPunctuation` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.MathOperatorSpacing` | 8.0 | auto_fix | error | Full | Math operators should have spaces around them |
| `Clinical.MultiplePunctuationSpaces` | 5.0 | auto_fix | error | Full | Ensures no double spaces between sentences |
| `Clinical.NumberGrouping` | 7.0 | comment | warning | Full | Large numbers should use commas |
| `Clinical.NumeralApostrophes` | 5.0 | comment | warning | Full | No apostrophes for decades |
| `Clinical.NumeralAtSentenceStart` | 7.0 | comment | warning | Full | Sentences should not start with numbers |
| `Clinical.NumericRatioFormat` | 7.0 | comment | warning | Full | Ratios should use colon |
| `Clinical.PValueFormat` | 7.0 | comment | warning | Full | p-values should be italicized |
| `Clinical.Participant` | 3.0 | comment | error | Full | 'Participant' instead of 'Subject' |
| `Clinical.PersonFirstLanguage` | 3.0 | comment | warning | Full | Use person-first language |
| `Clinical.PlainLanguageAbbreviations` | 1.0 | comment | warning | Full | Plain language terms |
| `Clinical.PreferredWordChoices` | Appendix C | comment | error | Full | Enforces preferred clinical vocabulary |
| `Clinical.ProseRanges` | 7.0 | comment | warning | Full | 'to' instead of hyphen in prose ranges |
| `Clinical.PunctuationInsideQuotes` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.RadiolabelSpacing` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.RadiolabelSuperscript` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.RawExternalURL` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.Redundancy` | Appendix B | comment | warning | Full | Avoid redundant phrases |
| `Clinical.ReferenceLabels` | 11.0 | comment | warning | Full | Reference labeling |
| `Clinical.RomanRequired` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.ScheduleOfActivities` | Appendix C | comment | warning | Full | SOA terminology |
| `Clinical.SexIdentityReview` | 3.0 | comment | warning | Full | Sex vs gender terms |
| `Clinical.SingleItemList` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.SymbolSpacing` | 8.0 | comment | warning | Full | Spacing around symbols |
| `Clinical.TableCaptionOutsideCell` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableDuplicateLabel` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableHeadingSentenceCase` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableLabelPeriod` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableLabelSequence` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableMissingDataDefinition` | Various | comment | warning | Full | Added via mass promotion |
| `Clinical.TableZeroFormat` | 9.0 | comment | error | Full | Tables should format zero correctly |
| `Clinical.TimeFormat` | 3.0 | comment | error | Full | Standard 24-hour time format required |
| `Clinical.TrademarkSymbols` | 8.0 | comment | warning | Full | First-use trademarking |
| `Clinical.TreatmentFailure` | 3.0 | comment | warning | Full | Do not use 'treatment failure' |
| `Clinical.TrialAliasFormat` | 11.0 | comment | warning | Full | Trial alias formats |
| `Clinical.TrialIntervention` | 3.0 | comment | error | Full | Use 'study intervention' terminology |
| `Clinical.TrialNumber` | Appendix C | comment | warning | Full | Trial number formatting |
| `Clinical.UnitNonbreakingSpace` | 8.0 | auto_fix | error | Full | Adds non-breaking spaces between values and units |

The machine-readable authority remains `config/commentpolicy.json`.