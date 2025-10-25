"""
GLPI Agent Task Deploy UserCheck WTS Module

Windows Terminal Services user interaction check.
"""

import time
from typing import Dict, Optional


# Button ID constants (from Windows)
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

# Mapping of button IDs to event names
SUPPORTED_EVENTS = {
    IDOK: 'ok',
    IDCANCEL: 'cancel',
    IDABORT: 'abort',
    IDRETRY: 'retry',
    IDIGNORE: 'ignore',
    IDYES: 'yes',
    IDNO: 'no',
    IDTRYAGAIN: 'tryagain',
    IDCONTINUE: 'continue',
    IDTIMEOUT: 'timeout',
    IDASYNC: 'async'
}


class WTS:
    """Windows Terminal Services user check handler"""
    
    def __init__(self, logger=None, title=None, text=None, icon=None, 
                 buttons=None, timeout=None, wait=None):
        """Initialize WTS user check"""
        self.logger = logger
        self.title = title
        self.text = text
        self.icon = icon
        self.buttons = buttons
        self.timeout = timeout
        self.wait = wait
        self.user = None
    
    def debug(self, msg: str) -> None:
        """Log debug message"""
        if self.logger:
            self.logger.debug(msg)
    
    def debug2(self, msg: str) -> None:
        """Log debug2 message"""
        if self.logger and hasattr(self.logger, 'debug2'):
            self.logger.debug2(msg)
    
    def set_user(self, user: str) -> None:
        """Set current user"""
        self.user = user
    
    def always_ask_users(self) -> bool:
        """Check if all users should be asked"""
        # Override in subclass if needed
        return False
    
    def handle_event(self, event: str, msg: str = None) -> bool:
        """
        Handle a user event.
        
        Args:
            event: Event name (e.g., 'on_ok', 'on_cancel')
            msg: Optional message
        
        Returns:
            True to stop processing, False to continue
        """
        # Override in subclass to handle specific events
        if msg:
            self.debug(msg)
        return False
    
    def tell_users(self) -> None:
        """Send message to active WTS users"""
        # 1. Get global WTS sessions list
        try:
            # Would import WTS tools
            # from GLPI.Agent.Tools.Win32.WTS import WTSEnumerateSessions, WTSSendMessage
            sessions = []  # Placeholder: WTSEnumerateSessions()
        except Exception:
            sessions = []
        
        if not sessions:
            self.handle_event("on_nouser", "No WTS session found")
            return
        
        # 2. Find active users in WTS sessions list
        users = {}
        for session in sessions:
            name = session.get('name', '')
            user = session.get('user', '')
            
            if 'sid' not in session or 'state' not in session:
                continue
            
            sessionid = session['sid']
            state = session['state']
            
            self.debug2(
                f"Found WTS session: #{sessionid}, session '{name}' for " +
                (f"'{user}'" if user else "no user") +
                f" (state={state})"
            )
            
            if not (name and user):
                continue
            
            # WTS Session state is defined by WTS_CONNECTSTATE_CLASS enumeration
            # See https://msdn.microsoft.com/en-us/library/aa383860(v=vs.85).aspx
            # 0 = Active, 1 = Connected
            if state not in (0, 1):
                continue
            
            users[sessionid] = user
        
        session_ids = sorted(users.keys())
        
        if not session_ids:
            self.handle_event("on_nouser", "No active user session found")
            return
        
        if len(session_ids) > 1 and not self.always_ask_users():
            self.handle_event("on_multiusers", "Multiple user sessions found")
            return
        
        # 3. Send message to each active user using WTS message
        for sid in session_ids:
            message = {
                'title': self.title or 'No title',
                'text': self.text or 'Sorry, message is missing',
                'icon': self.icon or 'none',
                'buttons': self.buttons or 'ok',
                'timeout': self.timeout,
                'wait': self.wait
            }
            
            # Keep user for reported event
            self.set_user(users[sid])
            
            # Support %u replacement in text and title
            message['title'] = message['title'].replace('%u', users[sid])
            message['text'] = message['text'].replace('%u', users[sid])
            
            sending = 'Sending' if self.wait else 'Async'
            self.debug2(
                f"WTS session #{sid}: {sending} message to {users[sid]} " +
                f"with '{message['title']}' title"
            )
            
            # Send message with WTS API
            asked = time.time()
            # answer = WTSSendMessage(sid, message)
            answer = IDOK  # Placeholder
            
            support = SUPPORTED_EVENTS.get(answer, 'unknown')
            elapsed = time.time() - asked
            self.debug2(
                f"WTS session #{sid}: Got {answer} as {support} answer code " +
                f"after {elapsed:.0f} seconds"
            )
            
            if self.handle_event(f'on_{support}'):
                break
