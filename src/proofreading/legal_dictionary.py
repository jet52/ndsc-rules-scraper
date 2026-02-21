"""
Legal dictionary supplement for spell-checking North Dakota court rules.
Provides terms that are valid in legal text but absent from standard dictionaries,
plus regex patterns for content that spell-checkers should skip entirely.
"""

import re

# Words valid in legal text but not in standard English dictionaries.
# All lowercase — pyspellchecker normalizes to lowercase before lookup.
LEGAL_TERMS = {
    # Latin legal terms
    'ab', 'initio', 'ad', 'hoc', 'litem', 'amicus', 'curiae', 'bona', 'fide',
    'certiorari', 'coram', 'nobis', 'de', 'facto', 'jure', 'novo', 'duces',
    'tecum', 'en', 'banc', 'et', 'al', 'seq', 'ex', 'parte', 'rel',
    'habeas', 'corpus', 'ibid', 'idem', 'in', 'camera', 'forma', 'pauperis',
    'limine', 'personam', 'rem', 'situ', 'inter', 'alia', 'sua', 'sponte',
    'mandamus', 'mens', 'rea', 'moot', 'nisi', 'nolle', 'prosequi',
    'nolo', 'contendere', 'nunc', 'pro', 'tunc', 'obiter', 'dictum',
    'pendens', 'pendente', 'lite', 'prima', 'facie', 'quo', 'warranto',
    'res', 'judicata', 'ipsa', 'loquitur', 'stare', 'decisis',
    'subpoena', 'supersedeas', 'venire', 'voir', 'dire', 'voire',
    'quash', 'quashed', 'quashing',

    # Legal terminology
    'abatement', 'adjudicatory', 'admissibility', 'affiant', 'affidavit',
    'aggrieved', 'allocution', 'amend', 'appellant', 'appellate', 'appellee',
    'appellees', 'appellants', 'arraignment', 'arrearage', 'bifurcate',
    'bifurcated', 'bifurcation', 'certifiable', 'chattel', 'chattels',
    'codefendant', 'codefendants', 'collateral', 'compulsory',
    'continuance', 'contemnor', 'counterclaim', 'counterclaims',
    'crossclaim', 'crossclaims', 'decedent', 'declarant', 'declaratory',
    'defeasance', 'deponent', 'depose', 'deposed', 'deposing',
    'discoverable', 'docketing', 'docketed', 'ejectment', 'eminent',
    'empanel', 'empaneled', 'empaneling', 'enjoin', 'enjoined',
    'estop', 'estoppel', 'evidentiary', 'exculpatory', 'exigent',
    'expunge', 'expunged', 'expungement', 'extradition', 'fiduciary',
    'garnish', 'garnished', 'garnishee', 'garnishment', 'guardianship',
    'hearsay', 'impanel', 'impaneled', 'impleader', 'inculpatory',
    'indemnify', 'indemnification', 'indictment', 'injunctive',
    'interlocutory', 'interpleader', 'interrogatories', 'interrogatory',
    'joinder', 'judgeship', 'judicature', 'jurisdictional',
    'lien', 'lienholder', 'lis', 'magistrate', 'malfeasance',
    'mandated', 'misdemeanor', 'misdemeanors', 'mitigating',
    'movant', 'multiparty', 'noncompliance', 'nonparty', 'nonsuit',
    'notarize', 'notarized', 'obiter', 'offeree', 'offeror',
    'pendency', 'peremptory', 'pleading', 'pleadings', 'postjudgment',
    'postconviction', 'posttrial', 'praecipe', 'prejudgment',
    'preponderance', 'pretrial', 'probative', 'procedendo',
    'promissory', 'prosecutorial', 'quorum', 'recusal', 'recuse',
    'recused', 'remand', 'remanded', 'remittitur', 'replevin',
    'respondent', 'respondents', 'restitutionary', 'retrial',
    'revocable', 'sequester', 'sequestered', 'sequestration',
    'severability', 'stipulate', 'stipulated', 'stipulation',
    'subparagraph', 'subparagraphs', 'subpart', 'subparts',
    'subsection', 'subsections', 'substantive', 'subchapter',
    'summons', 'surety', 'sureties', 'taxable',
    'testamentary', 'tortfeasor', 'tortious', 'tribunal',
    'unavailability', 'unsworn', 'vacate', 'vacated', 'vacatur',
    'venireman', 'veniremen', 'venireperson', 'venirepersons',
    'verdicts', 'vexatious', 'voir', 'waivable', 'writ', 'writs',

    # Court and procedural terms
    'adjudicate', 'adjudicated', 'adjudication', 'adjudicative',
    'calendared', 'calendaring', 'clerked', 'confer', 'conferee',
    'consolidable', 'coparty', 'cosigned', 'docket', 'dockets',
    'effectuate', 'effectuated', 'exparte', 'filings', 'forfeitable',
    'intervenor', 'intervenors', 'magistrates', 'nondispositive',
    'nonprobate', 'nonresident', 'pendente', 'postremand',
    'postsentencing', 'prehearing', 'presentence', 'presentencing',
    'reassignment', 'reargument', 'rebriefing', 'recalendar',
    'recommitment', 'redact', 'redacted', 'redaction', 'refiled',
    'refiling', 'rehearing', 'remandment', 'resentence',
    'resentencing', 'reviewable', 'rulemaking', 'sua',
    'telefacsimile', 'transcriber', 'uncontested', 'undertaking',
    'unpublished', 'unsealed', 'untimely',

    # ND-specific abbreviations and terms (lowercase forms)
    'ndcc', 'ndrct', 'ndrappp', 'ndrcivp', 'ndrcrimp', 'ndrjuvp', 'ndrev',
    'ndsupctadminr', 'ndsupctadminorder',
    'admissiontopracticer', 'ndrcontinuinglegaled', 'ndrprofconduct',
    'ndrlawyerdiscipl', 'ndstdsimposinglawyersanctions',
    'ndcodejudconduct', 'rjudconductcomm', 'ndrprocr', 'ndrlocalctpr',
    'rltdpracticeoflawbylawstudents',

    # Common legal abbreviations (lowercase)
    'subd', 'subdiv', 'supp', 'rev', 'stat', 'ann', 'const', 'amend',
    'dept', 'govt', 'natl', 'intl', 'assn', 'commn', 'regl',
    'civ', 'crim', 'juv', 'evid', 'proc', 'app', 'dist', 'mun',

    # Document and filing terms
    'efiled', 'efile', 'efiling', 'eservice', 'eserved', 'eserve',
    'pdf', 'pdfs', 'url', 'urls', 'webpage', 'webpages',
    'fax', 'faxed', 'faxing', 'facsimile',

    # Numbers/ordinals commonly seen in rules
    'th', 'st', 'nd', 'rd',
}

# Regex patterns for content that should be skipped entirely during spell-check.
# Each pattern matches a span of text that should not be split into words for checking.
IGNORE_PATTERNS = [
    # URLs
    re.compile(r'https?://\S+'),
    # Email addresses
    re.compile(r'[\w.+-]+@[\w.-]+\.\w+'),
    # ND citation patterns: § 28-32-01, §§ 28-32-01 through 28-32-05
    re.compile(r'§§?\s*[\d][\d.-]*'),
    # Rule cross-references: Rule 28(b)(2), Rule 6.1(a)
    re.compile(r'Rule\s+[\d]+(?:[.-]\d+)*(?:\([a-zA-Z0-9]+\))*'),
    # ND abbreviations with periods: N.D.R.Civ.P., N.D.C.C., N.D.R.Crim.P.
    re.compile(r'N\.D\.(?:[A-Z][a-z]*\.)*(?:[A-Z]\.)*'),
    # General dotted abbreviations: U.S.C., F.R.D., etc.
    re.compile(r'(?:[A-Z]\.){2,}\w*\.?'),
    # Case citations: 2024 ND 123, 456 N.W.2d 789
    re.compile(r'\d{4}\s+ND\s+\d+'),
    re.compile(r'\d+\s+N\.W\.\d*d?\s+\d+'),
    # Markdown formatting: **bold**, *italic*, [links](url)
    re.compile(r'\[([^\]]+)\]\([^)]+\)'),
    # Markdown headers (the # characters)
    re.compile(r'^#{1,6}\s', re.MULTILINE),
    # Numeric patterns with hyphens/dots: dates, phone numbers, section refs
    re.compile(r'\b\d[\d./-]+\d\b'),
]
