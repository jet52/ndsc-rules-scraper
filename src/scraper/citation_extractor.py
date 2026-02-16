"""
Citation extractor for the ND Court Rules Scraper.
Generates proper legal citations for North Dakota court rules.
"""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse


class CitationExtractor:
    """Extracts and generates proper citations for North Dakota court rules."""
    
    def __init__(self, logger=None):
        """
        Initialize the citation extractor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Citation patterns for different rule types
        self.citation_patterns = {
            'appellate': {
                'prefix': 'N.D.R.App.P.',
                'patterns': [r'appellate', r'app\.', r'appp']
            },
            'civil': {
                'prefix': 'N.D.R.Civ.P.',
                'patterns': [r'civil', r'civ\.', r'civp']
            },
            'criminal': {
                'prefix': 'N.D.R.Crim.P.',
                'patterns': [r'criminal', r'crim\.', r'crimp']
            },
            'juvenile': {
                'prefix': 'N.D.R.Juv.P.',
                'patterns': [r'juvenile', r'juv\.', r'juvp']
            },
            'evidence': {
                'prefix': 'N.D.R.Evid.',
                'patterns': [r'evidence', r'evid\.', r'evid']
            },
            'court': {
                'prefix': 'N.D.R.Ct.',
                'patterns': [r'court', r'ct\.', r'ct']
            },
            'professional_conduct': {
                'prefix': 'N.D.R.Prof.Conduct',
                'patterns': [r'professional', r'conduct', r'prof\.', r'profconduct']
            },
            'disciplinary': {
                'prefix': 'N.D.R.LawyerDiscipl.',
                'patterns': [r'disciplinary', r'discipline', r'discipl']
            },
            'admission': {
                'prefix': 'N.D.R.Admission',
                'patterns': [r'admission', r'admit', r'adm']
            },
            'continuing_education': {
                'prefix': 'N.D.R.ContinuingLegalEduc.',
                'patterns': [r'continuing', r'education', r'cle', r'continuinglegal']
            },
            'judicial_conduct': {
                'prefix': 'N.D.R.Jud.Conduct',
                'patterns': [r'judicial', r'jud\.', r'judconduct']
            },
            'administrative': {
                'prefix': 'N.D.Admin.R.',
                'patterns': [r'administrative', r'admin\.', r'admin']
            }
        }
    
    def generate_citation(self, rule_number: str, source_url: str) -> Optional[str]:
        """
        Generate a proper citation for a rule.
        
        Args:
            rule_number: The rule number (e.g., "1", "1A", "2")
            source_url: The source URL to determine rule type
        
        Returns:
            Proper citation string or None if unable to determine
        """
        if not rule_number:
            return None
        
        # Determine rule type from URL
        rule_type = self._determine_rule_type(source_url)
        
        if rule_type and rule_type in self.citation_patterns:
            prefix = self.citation_patterns[rule_type]['prefix']
            citation = f"{prefix} {rule_number}"
            
            if self.logger:
                self.logger.debug(f"Generated citation: {citation} for rule {rule_number}")
            
            return citation
        
        # Fallback: try to determine from URL path
        fallback_citation = self._generate_fallback_citation(rule_number, source_url)
        if fallback_citation:
            return fallback_citation
        
        if self.logger:
            self.logger.warning(f"Unable to generate citation for rule {rule_number} from URL: {source_url}")
        
        return None
    
    def _determine_rule_type(self, url: str) -> Optional[str]:
        """
        Determine the type of rule from the URL.
        
        Args:
            url: The source URL
        
        Returns:
            Rule type key or None if unable to determine
        """
        url_lower = url.lower()
        path = urlparse(url).path.lower()
        
        # Check each rule type pattern
        for rule_type, config in self.citation_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, url_lower) or re.search(pattern, path):
                    if self.logger:
                        self.logger.debug(f"Determined rule type '{rule_type}' from URL pattern '{pattern}'")
                    return rule_type
        
        return None
    
    def _generate_fallback_citation(self, rule_number: str, url: str) -> Optional[str]:
        """
        Generate a fallback citation when rule type cannot be determined.
        
        Args:
            rule_number: The rule number
            url: The source URL
        
        Returns:
            Fallback citation or None
        """
        # Look for common patterns in the URL
        url_lower = url.lower()
        
        # Check for specific rule categories in URL
        if 'appellate' in url_lower or 'app.' in url_lower:
            return f"N.D.R.App.P. {rule_number}"
        elif 'civil' in url_lower or 'civ.' in url_lower:
            return f"N.D.R.Civ.P. {rule_number}"
        elif 'criminal' in url_lower or 'crim.' in url_lower:
            return f"N.D.R.Crim.P. {rule_number}"
        elif 'evidence' in url_lower or 'evid.' in url_lower:
            return f"N.D.R.Evid. {rule_number}"
        elif 'juvenile' in url_lower or 'juv.' in url_lower:
            return f"N.D.R.Juv.P. {rule_number}"
        elif 'professional' in url_lower or 'conduct' in url_lower:
            return f"N.D.R.Prof.Conduct {rule_number}"
        elif 'disciplinary' in url_lower or 'discipline' in url_lower:
            return f"N.D.R.LawyerDiscipl. {rule_number}"
        elif 'administrative' in url_lower or 'admin.' in url_lower:
            return f"N.D.Admin.R. {rule_number}"
        elif 'court' in url_lower or 'ct.' in url_lower:
            return f"N.D.R.Ct. {rule_number}"
        
        return None
    
    def extract_citation_from_text(self, text: str) -> Optional[str]:
        """
        Extract citation from text content.
        
        Args:
            text: Text content to search for citations
        
        Returns:
            Extracted citation or None
        """
        # Common citation patterns
        citation_patterns = [
            r'N\.D\.R\.App\.P\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Civ\.P\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Crim\.P\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Evid\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Juv\.P\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Prof\.Conduct\s*(\d+[A-Z]*)',
            r'N\.D\.R\.LawyerDiscipl\.\s*(\d+[A-Z]*)',
            r'N\.D\.Admin\.R\.\s*(\d+[A-Z]*)',
            r'N\.D\.R\.Ct\.\s*(\d+[A-Z]*)',
            r'Rule\s+(\d+[A-Z]*)',
            r'§\s*(\d+[A-Z]*)'
        ]
        
        for pattern in citation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                citation = match.group(0)
                if self.logger:
                    self.logger.debug(f"Extracted citation from text: {citation}")
                return citation
        
        return None
    
    def validate_citation(self, citation: str) -> bool:
        """
        Validate if a citation follows proper format.
        
        Args:
            citation: Citation to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not citation:
            return False
        
        # Check if citation matches any known pattern
        valid_patterns = [
            r'^N\.D\.R\.App\.P\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Civ\.P\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Crim\.P\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Evid\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Juv\.P\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Prof\.Conduct\s+\d+[A-Z]*$',
            r'^N\.D\.R\.LawyerDiscipl\.\s+\d+[A-Z]*$',
            r'^N\.D\.Admin\.R\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Ct\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Admission\s+\d+[A-Z]*$',
            r'^N\.D\.R\.ContinuingLegalEduc\.\s+\d+[A-Z]*$',
            r'^N\.D\.R\.Jud\.Conduct\s+\d+[A-Z]*$'
        ]
        
        for pattern in valid_patterns:
            if re.match(pattern, citation, re.IGNORECASE):
                return True
        
        return False
    
    def get_citation_info(self, citation: str) -> Dict[str, Any]:
        """
        Get detailed information about a citation.
        
        Args:
            citation: The citation to analyze
        
        Returns:
            Dictionary with citation information
        """
        info = {
            "citation": citation,
            "is_valid": False,
            "rule_type": None,
            "rule_number": None,
            "prefix": None,
            "full_name": None
        }
        
        if not citation:
            return info
        
        # Extract rule number
        rule_number_match = re.search(r'\s+(\d+[A-Z]*)$', citation)
        if rule_number_match:
            info["rule_number"] = rule_number_match.group(1)
        
        # Determine rule type and prefix
        for rule_type, config in self.citation_patterns.items():
            if citation.startswith(config['prefix']):
                info["rule_type"] = rule_type
                info["prefix"] = config['prefix']
                info["is_valid"] = True
                break
        
        # Get full name
        full_names = {
            'appellate': 'North Dakota Rules of Appellate Procedure',
            'civil': 'North Dakota Rules of Civil Procedure',
            'criminal': 'North Dakota Rules of Criminal Procedure',
            'juvenile': 'North Dakota Rules of Juvenile Procedure',
            'evidence': 'North Dakota Rules of Evidence',
            'court': 'North Dakota Rules of Court',
            'professional_conduct': 'North Dakota Rules of Professional Conduct',
            'disciplinary': 'North Dakota Rules for Lawyer Discipline',
            'admission': 'North Dakota Rules for Admission to the Bar',
            'continuing_education': 'North Dakota Rules for Continuing Legal Education',
            'judicial_conduct': 'North Dakota Code of Judicial Conduct',
            'administrative': 'North Dakota Administrative Rules'
        }
        
        if info["rule_type"] in full_names:
            info["full_name"] = full_names[info["rule_type"]]
        
        return info 