from __future__ import annotations
import pythoncom
import win32com.client
from typing import Any

class WordAppSession:
    """
    A robust context manager for interacting with Word COM objects.
    Ensures safe initialization, cleanup, and error handling.
    """
    def __init__(self, visible: bool = False, screen_updating: bool = True):
        self.visible = visible
        self.screen_updating = screen_updating
        self.word: Any = None
        self.owns_com = False

    def __enter__(self) -> Any:
        # Initialize COM in this thread
        pythoncom.CoInitialize()
        self.owns_com = True
        
        try:
            self.word = win32com.client.DispatchEx("Word.Application")
            self.word.Visible = self.visible
            if not self.screen_updating:
                self.word.ScreenUpdating = False
        except Exception as e:
            if self.owns_com:
                pythoncom.CoUninitialize()
            raise RuntimeError(f"Failed to initialize Word Application: {e}") from e
            
        return self.word

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.word is not None:
            try:
                # Always ensure ScreenUpdating is restored
                if not self.screen_updating:
                    self.word.ScreenUpdating = True
            except Exception:
                pass
                
            try:
                self.word.Quit()
            except Exception as e:
                print(f"Word application cleanup warning: {e}")
                
        if self.owns_com:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
