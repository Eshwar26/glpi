#!/usr/bin/env python3
"""
GLPI Agent Win32 WTS - Python Implementation

Windows Terminal Services (WTS) API wrapper for session management and messaging.
"""

from typing import List, Dict, Optional

__all__ = [
    'wts_enumerate_sessions',
    'wts_send_message',
    'IDOK', 'IDCANCEL', 'IDABORT', 'IDRETRY',
    'IDIGNORE', 'IDYES', 'IDNO', 'IDTRYAGAIN',
    'IDCONTINUE', 'IDTIMEOUT', 'IDASYNC'
]


# Constants for WTS API
WTS_CURRENT_SERVER_HANDLE = 0x00000000

# Message box response constants (from winuser.h)
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDTRYAGAIN = 10
IDCONTINUE = 11
IDTIMEOUT = 32000
IDASYNC = 32001

# WTS Information Class constants
WTS_USERNAME = 5


# Message box button constants
MB_BUTTONS = {
    'ok': 0x00000000,
    'okcancel': 0x00000001,
    'abortretryignore': 0x00000002,
    'yesnocancel': 0x00000003,
    'yesno': 0x00000004,
    'retrycancel': 0x00000005,
    'canceltrycontinue': 0x00000006
}

# Message box icon constants
MB_ICONS = {
    'none': 0x00000000,
    'error': 0x00000010,
    'question': 0x00000020,
    'warn': 0x00000030,
    'info': 0x00000040
}


def wts_enumerate_sessions() -> List[Dict]:
    """
    Enumerate Windows Terminal Services sessions.
    
    Returns:
        List of session dictionaries containing:
            - sid: Session ID
            - name: Station name
            - state: Connection state
            - user: Username
    """
    sessions = []
    
    try:
        # This requires Win32 API bindings (win32ts module or ctypes)
        # For now, provide the interface structure
        import ctypes
        from ctypes import wintypes
        
        # Load wtsapi32.dll
        wtsapi32 = ctypes.windll.wtsapi32
        
        # Define structures and function signatures
        # WTS_SESSION_INFO structure
        class WTS_SESSION_INFO(ctypes.Structure):
            _fields_ = [
                ("SessionId", wintypes.DWORD),
                ("pWinStationName", wintypes.LPWSTR),
                ("State", wintypes.DWORD)
            ]
        
        ppSessionInfo = ctypes.POINTER(WTS_SESSION_INFO)()
        pCount = wintypes.DWORD()
        
        # Call WTSEnumerateSessions
        if wtsapi32.WTSEnumerateSessionsW(
            WTS_CURRENT_SERVER_HANDLE,
            0,  # Reserved
            1,  # Version
            ctypes.byref(ppSessionInfo),
            ctypes.byref(pCount)
        ):
            # Process sessions
            for i in range(pCount.value):
                session_info = ppSessionInfo[i]
                
                sessions.append({
                    'sid': session_info.SessionId,
                    'name': session_info.pWinStationName or '',
                    'state': session_info.State,
                    'user': _wts_query_session_information(session_info.SessionId, WTS_USERNAME)
                })
            
            # Free memory
            wtsapi32.WTSFreeMemory(ppSessionInfo)
    
    except (ImportError, OSError, AttributeError):
        # Win32 API not available or not on Windows
        pass
    
    return sessions


def wts_send_message(sid: int, message: Optional[Dict] = None) -> int:
    """
    Send a message box to a Windows Terminal Services session.
    
    Args:
        sid: Session ID to send message to
        message: Dictionary with message parameters:
            - title: Message box title (default: "Notification")
            - text: Message text (default: "About to proceed...")
            - buttons: Button style (default: "ok")
            - icon: Icon style (default: "info")
            - timeout: Timeout in seconds (default: 60)
            - wait: Wait for response (default: True)
    
    Returns:
        Response ID (one of the ID constants)
    """
    # Setup defaults
    message = message or {}
    title = message.get('title', 'Notification')
    text = message.get('text', 'About to proceed...')
    buttons = message.get('buttons', 'ok')
    icon = message.get('icon', 'info')
    timeout = message.get('timeout', 60)
    wait = message.get('wait', True)
    
    # Convert boolean wait to integer
    if isinstance(wait, str):
        wait = wait.lower() not in ['0', 'no', 'false']
    elif not isinstance(wait, bool):
        wait = bool(wait)
    wait = 1 if wait else 0
    
    # Prepare message box style
    style = MB_BUTTONS.get(buttons, MB_BUTTONS['ok'])
    if icon in MB_ICONS:
        style |= MB_ICONS[icon]
    
    response = IDOK
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # Load wtsapi32.dll
        wtsapi32 = ctypes.windll.wtsapi32
        
        # Encode strings
        title_w = title.encode('utf-16-le') + b'\x00\x00'
        text_w = text.encode('utf-16-le') + b'\x00\x00'
        
        pResponse = wintypes.DWORD()
        
        # Call WTSSendMessage
        if wtsapi32.WTSSendMessageW(
            WTS_CURRENT_SERVER_HANDLE,
            sid,
            title_w,
            len(title_w),
            text_w,
            len(text_w),
            style,
            timeout,
            ctypes.byref(pResponse),
            wait
        ):
            response = pResponse.value
    
    except (ImportError, OSError, AttributeError):
        # Win32 API not available or not on Windows
        pass
    
    return response


def _wts_query_session_information(sid: int, info_class: int) -> str:
    """
    Query session information using WTSQuerySessionInformation.
    
    Args:
        sid: Session ID
        info_class: Information class to query
        
    Returns:
        Queried information as string
    """
    buffer = ""
    
    try:
        import ctypes
        from ctypes import wintypes
        
        wtsapi32 = ctypes.windll.wtsapi32
        
        pBuffer = ctypes.c_void_p()
        pBytesReturned = wintypes.DWORD()
        
        if wtsapi32.WTSQuerySessionInformationW(
            WTS_CURRENT_SERVER_HANDLE,
            sid,
            info_class,
            ctypes.byref(pBuffer),
            ctypes.byref(pBytesReturned)
        ):
            if pBytesReturned.value > 0:
                # Read string from memory
                buffer = ctypes.wstring_at(pBuffer.value)
            
            # Free memory
            wtsapi32.WTSFreeMemory(pBuffer)
    
    except (ImportError, OSError, AttributeError):
        pass
    
    return buffer


if __name__ == '__main__':
    print("GLPI Agent Win32 WTS Module")
    print("Windows Terminal Services API wrapper")
    print(f"\nConstants:")
    print(f"  IDOK={IDOK}, IDCANCEL={IDCANCEL}, IDYES={IDYES}, IDNO={IDNO}")
