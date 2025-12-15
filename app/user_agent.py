"""
User-Agent Parser - Extract device model from User-Agent string
IMPROVED: Better handling of Build/ pattern and model extraction
"""
import re
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ParsedDevice:
    """Parsed device information from User-Agent"""
    model_code: str
    os_type: str  # android, ios, windows, macos, linux, other
    os_version: Optional[str] = None
    browser: Optional[str] = None
    raw_user_agent: str = ""
    

class UserAgentParser:
    """Parse User-Agent strings to extract device information"""
    
    # Improved regex patterns
    # Pattern 1: Match "Android XX; MODEL Build/" - most common format
    ANDROID_BUILD_PATTERN = re.compile(
        r'Android\s*[\d.]+;\s*([^)]+?)\s*Build/',
        re.IGNORECASE
    )
    
    # Pattern 2: Match "Android XX; MODEL)" - for browsers that don't include Build
    ANDROID_PAREN_PATTERN = re.compile(
        r'Android\s*[\d.]+;\s*([A-Za-z0-9][A-Za-z0-9_\-\s]+?)(?:\s*\)|;)',
        re.IGNORECASE
    )
    
    # Pattern 3: Extract from MIUI browser format
    ANDROID_MIUI_PATTERN = re.compile(
        r'Android\s*[\d.]+;\s*(?:wv;\s*)?([A-Za-z0-9][A-Za-z0-9_\-\s]+?)\s*MIUI',
        re.IGNORECASE
    )
    
    ANDROID_VERSION_PATTERN = re.compile(
        r'Android\s*([\d.]+)',
        re.IGNORECASE
    )
    
    IOS_PATTERN = re.compile(
        r'(iPhone|iPad|iPod)',
        re.IGNORECASE
    )
    
    IOS_VERSION_PATTERN = re.compile(
        r'(?:iPhone|iPad|iPod).*?OS\s*([\d_]+)',
        re.IGNORECASE
    )
    
    WINDOWS_PATTERN = re.compile(
        r'Windows\s*(?:NT)?\s*([\d.]+)',
        re.IGNORECASE
    )
    
    MAC_PATTERN = re.compile(
        r'Macintosh.*Mac OS X\s*([\d_]+)',
        re.IGNORECASE
    )
    
    def parse(self, user_agent: str) -> ParsedDevice:
        """
        Parse User-Agent string and extract device information
        """
        if not user_agent:
            return ParsedDevice(
                model_code="Unknown",
                os_type="unknown",
                raw_user_agent=user_agent or ""
            )
        
        # Check for Android
        if 'android' in user_agent.lower():
            return self._parse_android(user_agent)
        
        # Check for iOS
        if any(x in user_agent.lower() for x in ['iphone', 'ipad', 'ipod']):
            return self._parse_ios(user_agent)
        
        # Check for Windows
        if 'windows' in user_agent.lower():
            return self._parse_windows(user_agent)
        
        # Check for Mac
        if 'macintosh' in user_agent.lower():
            return self._parse_mac(user_agent)
        
        # Check for Linux
        if 'linux' in user_agent.lower():
            return ParsedDevice(
                model_code="Linux Device",
                os_type="linux",
                raw_user_agent=user_agent
            )
        
        return ParsedDevice(
            model_code="Unknown",
            os_type="other",
            raw_user_agent=user_agent
        )
    
    def _parse_android(self, user_agent: str) -> ParsedDevice:
        """Parse Android User-Agent - IMPROVED"""
        model_code = "Android Device"
        os_version = None
        
        # Try multiple patterns in order of specificity
        
        # Pattern 1: "Android XX; MODEL Build/" - most reliable
        match = self.ANDROID_BUILD_PATTERN.search(user_agent)
        if match:
            model_code = match.group(1).strip()
        else:
            # Pattern 2: "Android XX; MODEL)" 
            match = self.ANDROID_PAREN_PATTERN.search(user_agent)
            if match:
                model_code = match.group(1).strip()
            else:
                # Pattern 3: MIUI browser
                match = self.ANDROID_MIUI_PATTERN.search(user_agent)
                if match:
                    model_code = match.group(1).strip()
        
        # Clean up model code
        if model_code and model_code != "Android Device":
            # Remove common suffixes
            model_code = re.sub(r'\s*Build$', '', model_code, flags=re.IGNORECASE)
            model_code = re.sub(r'\s*MIUI.*$', '', model_code, flags=re.IGNORECASE)
            # Remove "wv;" prefix if present
            model_code = re.sub(r'^wv;\s*', '', model_code, flags=re.IGNORECASE)
            # Skip Chrome's privacy placeholder
            if model_code.strip() == 'K':
                model_code = "Android Device"
        
        # Extract OS version
        version_match = self.ANDROID_VERSION_PATTERN.search(user_agent)
        if version_match:
            os_version = version_match.group(1)
        
        # Detect browser
        browser = self._detect_browser(user_agent)
        
        return ParsedDevice(
            model_code=model_code.strip() if model_code else "Android Device",
            os_type="android",
            os_version=os_version,
            browser=browser,
            raw_user_agent=user_agent
        )
    
    def _parse_ios(self, user_agent: str) -> ParsedDevice:
        """Parse iOS User-Agent"""
        model_code = "iPhone"
        os_version = None
        
        ios_match = self.IOS_PATTERN.search(user_agent)
        if ios_match:
            model_code = ios_match.group(1)
        
        version_match = self.IOS_VERSION_PATTERN.search(user_agent)
        if version_match:
            os_version = version_match.group(1).replace('_', '.')
        
        browser = self._detect_browser(user_agent)
        
        return ParsedDevice(
            model_code=model_code,
            os_type="ios",
            os_version=os_version,
            browser=browser,
            raw_user_agent=user_agent
        )
    
    def _parse_windows(self, user_agent: str) -> ParsedDevice:
        """Parse Windows User-Agent"""
        os_version = None
        
        version_match = self.WINDOWS_PATTERN.search(user_agent)
        if version_match:
            os_version = version_match.group(1)
        
        windows_versions = {
            '10.0': 'Windows 10/11',
            '6.3': 'Windows 8.1',
            '6.2': 'Windows 8',
            '6.1': 'Windows 7',
            '6.0': 'Windows Vista',
            '5.1': 'Windows XP',
        }
        
        model_code = windows_versions.get(os_version, f'Windows {os_version}' if os_version else 'Windows PC')
        browser = self._detect_browser(user_agent)
        
        return ParsedDevice(
            model_code=model_code,
            os_type="windows",
            os_version=os_version,
            browser=browser,
            raw_user_agent=user_agent
        )
    
    def _parse_mac(self, user_agent: str) -> ParsedDevice:
        """Parse macOS User-Agent"""
        os_version = None
        
        version_match = self.MAC_PATTERN.search(user_agent)
        if version_match:
            os_version = version_match.group(1).replace('_', '.')
        
        browser = self._detect_browser(user_agent)
        
        return ParsedDevice(
            model_code="MacBook/iMac",
            os_type="macos",
            os_version=os_version,
            browser=browser,
            raw_user_agent=user_agent
        )
    
    def _detect_browser(self, user_agent: str) -> str:
        """Detect browser from User-Agent"""
        ua_lower = user_agent.lower()
        
        if 'miuibrowser' in ua_lower:
            return 'MIUI Browser'
        if 'edg/' in ua_lower:
            return 'Edge'
        if 'chrome' in ua_lower and 'safari' in ua_lower:
            return 'Chrome'
        if 'firefox' in ua_lower:
            return 'Firefox'
        if 'safari' in ua_lower and 'chrome' not in ua_lower:
            return 'Safari'
        if 'opera' in ua_lower or 'opr/' in ua_lower:
            return 'Opera'
        
        return 'Unknown'
    
    def extract_model_codes(self, user_agent: str) -> List[str]:
        """
        Extract all possible model codes from User-Agent
        Returns multiple candidates for matching
        """
        codes = []
        parsed = self.parse(user_agent)
        
        # Add parsed model code
        if parsed.model_code and parsed.model_code not in ['Unknown', 'Android Device', 'K']:
            codes.append(parsed.model_code)
            
            # Add without spaces
            if ' ' in parsed.model_code:
                codes.append(parsed.model_code.replace(' ', ''))
            
            # Add uppercase version
            codes.append(parsed.model_code.upper())
            
            # Add lowercase version
            codes.append(parsed.model_code.lower())
        
        return list(dict.fromkeys(codes))  # Remove duplicates, preserve order
