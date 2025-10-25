#!/usr/bin/env python3
"""
GLPI Agent Win32 Users - Python Implementation

Windows user profile and account management functions.
"""

import re
from typing import List, Dict, Optional

__all__ = ['get_system_user_profiles', 'get_profile_username', 'get_users']


def get_system_user_profiles() -> List[Dict]:
    """
    Get list of Windows user profiles from WMI.
    
    Returns:
        List of user profile dictionaries containing SID, PATH, and LOADED status
    """
    profiles = []
    
    try:
        # Import WMI functions (these would need to be implemented in Win32.py)
        from GLPI.Agent.Tools.Win32 import get_wmi_objects, get_local_codepage
        
        for userprofile in get_wmi_objects(
            query="SELECT * FROM Win32_UserProfile WHERE LocalPath IS NOT NULL AND Special=FALSE",
            properties=['Sid', 'Loaded', 'LocalPath']
        ):
            sid = userprofile.get('Sid')
            if not sid or not re.match(r'^S-\d+-(5-21|12-1)(-\d+)+$', sid):
                continue
            
            loaded = userprofile.get('Loaded')
            local_path = userprofile.get('LocalPath')
            
            if loaded is None or local_path is None:
                continue
            
            # Convert backslashes to forward slashes
            local_path = local_path.replace('\\', '/')
            
            # Encode to local codepage
            try:
                codepage = get_local_codepage()
                if codepage and codepage != 'utf-8':
                    local_path = local_path.encode(codepage, errors='ignore').decode(codepage)
            except Exception:
                pass
            
            profiles.append({
                'SID': sid,
                'PATH': local_path,
                'LOADED': 1 if str(loaded).lower() in ['1', 'true'] else 0
            })
    
    except ImportError:
        # WMI not available (non-Windows or missing dependencies)
        pass
    
    return profiles


def get_profile_username(user: Dict) -> Optional[str]:
    """
    Get username for a user profile.
    
    Args:
        user: User profile dictionary with SID and PATH
        
    Returns:
        Username or None
    """
    sid = user.get('SID')
    if not sid:
        return None
    
    try:
        from GLPI.Agent.Tools.Win32 import (
            get_registry_key, run_powershell, get_local_codepage
        )
        
        # First try to get username from volatile environment
        userenvkey = get_registry_key(
            path=f"HKEY_USERS/{sid}/Volatile Environment/",
            required=['USERNAME']
        )
        if userenvkey and userenvkey.get('/USERNAME'):
            return userenvkey['/USERNAME']
        
        # Try PowerShell
        script = f'''
            # Setup encoding to UTF-8
            $PreviousEncoding = [console]::OutputEncoding
            $OutputEncoding   = [console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding
            
            try {{
                ((New-Object System.Security.Principal.SecurityIdentifier("{sid}")).Translate([System.Security.Principal.NTAccount])).Value
            }}
            catch {{
                Write-Output "Exception: $($PSItem.FullyQualifiedErrorId)"
            }}
            
            # Restore encoding
            $OutputEncoding = [console]::InputEncoding = [console]::OutputEncoding = $PreviousEncoding
        '''
        
        results = run_powershell(script=script)
        if results:
            ntaccount = results[0] if isinstance(results, list) else results
            
            if ntaccount:
                if ntaccount.startswith('Exception: '):
                    exception = ntaccount.replace('Exception: ', '')
                    if exception == 'IdentityNotMappedException':
                        return "Domain deleted account"
                    return "Unknown account"
                
                # Extract username from DOMAIN\username format
                match = re.match(r'^[^\\]*\\(.*)$', ntaccount)
                if match and match.group(1):
                    return match.group(1)
        
        # Try Group Policy Caching
        cacheentry = get_registry_key(
            path=f"HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows/CurrentVersion/Group Policy/DataStore/{sid}/0",
            required=['szTargetName']
        )
        if cacheentry and cacheentry.get('/szTargetName'):
            target_name = cacheentry['/szTargetName']
            try:
                codepage = get_local_codepage()
                if codepage != 'utf-8':
                    target_name = target_name.encode(codepage, errors='ignore').decode('utf-8')
            except Exception:
                pass
            return target_name
        
        # Try LogonUI session data
        sessiondata = get_registry_key(
            path="HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows/CurrentVersion/Authentication/LogonUI/SessionData",
            required=['LoggedOnUserSID', 'LoggedOnUser']
        )
        if sessiondata:
            for key, value in sessiondata.items():
                if not key.endswith('/'):
                    continue
                
                if not isinstance(value, dict):
                    continue
                
                usersid = value.get('/LoggedOnUserSID')
                if usersid != sid:
                    continue
                
                account = value.get('/LoggedOnUser')
                if account:
                    match = re.match(r'^[^\\]*\\(.*)$', account)
                    if match and match.group(1):
                        username = match.group(1)
                        try:
                            codepage = get_local_codepage()
                            if codepage != 'utf-8':
                                username = username.encode(codepage, errors='ignore').decode('utf-8')
                        except Exception:
                            pass
                        return username
        
        # Try WMI request
        users = get_users(sid=sid)
        if users and users[0].get('NAME'):
            return users[0]['NAME']
    
    except ImportError:
        pass
    
    # Fall back to extracting from profile path
    path = user.get('PATH', '')
    match = re.search(r'/([^/]+)$', path)
    if match:
        username = match.group(1)
        try:
            from GLPI.Agent.Tools.Win32 import get_local_codepage
            codepage = get_local_codepage()
            if codepage != 'utf-8':
                username = username.encode(codepage, errors='ignore').decode('utf-8')
        except Exception:
            pass
        return username
    
    return None


def get_users(localusers: bool = False, sid: Optional[str] = None, 
              login: Optional[str] = None, logger=None) -> List[Dict]:
    """
    Get list of Windows user accounts from WMI.
    
    Args:
        localusers: Only return local user accounts
        sid: Filter by specific SID
        login: Filter by specific login name
        logger: Logger object
        
    Returns:
        List of user account dictionaries
    """
    users = []
    
    try:
        from GLPI.Agent.Tools.Win32 import get_wmi_objects
        
        # Build WMI query conditions
        conditions = [
            "Disabled='False'",
            "Lockout='False'"
        ]
        
        if localusers:
            conditions.append("LocalAccount='True'")
        
        if sid:
            conditions.append(f"SID='{sid}'")
        
        if login:
            # Escape single quotes
            escaped_login = login.replace("'", "\\'")
            conditions.append(f"Name='{escaped_login}'")
        
        query = f"SELECT * FROM Win32_UserAccount WHERE {' AND '.join(conditions)}"
        
        # Warning: On a large network, this WMI call can negatively affect
        # performance and may fail with a timeout
        for obj in get_wmi_objects(
            moniker='winmgmts:\\\\.\\root\\CIMV2',
            query=query,
            properties=['Domain', 'Name', 'SID'],
            logger=logger
        ):
            users.append({
                'DOMAIN': obj.get('Domain'),
                'NAME': obj.get('Name'),
                'ID': obj.get('SID')
            })
    
    except ImportError:
        pass
    
    return users


if __name__ == '__main__':
    print("GLPI Agent Win32 Users Module")
    print("Windows user profile and account management")
