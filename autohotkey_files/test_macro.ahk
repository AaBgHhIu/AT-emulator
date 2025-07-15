; Script: test_macro.ahk
; Press Ctrl + J to send a batch of AT commands

^j:: ; Hotkey: Ctrl + J
Send AT{Enter}
Sleep 1000
Send ATI{Enter}
Sleep 1000
Send AT+CSQ{Enter}
Sleep 1000
Send AT+CPIN?{Enter}
return
