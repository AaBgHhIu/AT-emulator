import serial

# === CONFIGURATION ===
PORT = 'COM10'
BAUDRATE = 9600
TIMEOUT = 1

# === STATE VARIABLES ===
command_buffer = ""
verbose_errors = False
sms_send_mode = False
sms_number = ""
sms_memory = {}
response_mode = 'OK'

try:
    ser = serial.Serial(PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
    print(f"📡 AT Emulator running on {PORT}")
except Exception as e:
    print(f"❌ Could not open {PORT}: {e}")
    exit()

# === DEFINED COMMAND RESPONSES ===
at_responses = {
    # Basic
    "AT": "OK",
    "ATE0": "OK",
    "ATE1": "OK",
    "ATZ": "Modem reset\nOK",
    "AT&F": "Factory settings loaded\r\nOK",
    "AT&W": "Settings saved\r\nOK",
    
    # Device Info
    "ATI": "CelerFake v1.0\r\nManufacturer: CelerLab\r\nRevision: 2025.01\r\nOK",
    "AT+CGMI": "CelerLab\r\nOK",
    "AT+CGMM": "Celer900\r\nOK",
    "AT+CGMR": "Revision 2025.01\r\nOK",
    "AT+CGSN": "867530900123456\r\nOK",
    
    # SIM & Network
    "AT+CPIN?": "+CPIN: READY\rOK",
    "AT+CSQ?": "+CSQ: 23,99\rOK",
    "AT+CSQ=?": "+CSQ: (0-31,99),(0-7,99)\nOK",
    "AT+CREG?": "+CREG: 0,1\nOK",
    "AT+COPS?": "+COPS: 0,0,\"DTRI Network\",2\r\nOK",
    "AT+COPS=?": "+COPS: (0,0,\"DTRI Network\")\r\nOK",
    "AT+CLCK=?": "+CLCK: (\"SC\")\nOK",
    "AT+CLCK=\"SC\",2": "+CLCK: 0\nOK",
    "AT+CLCK=\"SC\",0,\"0000\"": "OK",
    
    # SMS
    "AT+CMGF=1": "OK",
    "AT+CMGF=0": "OK",
    "AT+CMGF=?": "+CMGF: (0,1)\r\nOK",

    "AT+CSCA?": "+CSCA: \"+1234567890\",145\r\nOK",
    "AT+CSMP?": "+CSMP: 17,167,0,0\nOK",
    "AT+CMGD=1": "OK",
    "AT+CMGL=\"ALL\"": "+CMGL: 1,\"REC READ\",\"+12345\",\"22/07/16,12:00:00+00\"\r\nHello\r\nOK",
    
    # GPRS / PDP
   'AT+CGDCONT=1,"IP","internet"': "\rOK",

    "AT+CGDCONT?": "+CGDCONT: 1,\"IP\",\"internet\"\r\nOK",
    "AT+CGDCONT=?": '+CGDCONT: (1-5),"IP","<APN>"\rOK',

    "AT+CGATT?": "+CGATT: 1\nOK",
    "AT+CGACT?": "+CGACT: 1,1\nOK",
    "AT+CGACT=1,1": "OK",
    "AT+CGPADDR": "+CGPADDR: 1,10.30.20.5\r\nOK",

    # Network & RAT
    "AT+CFUN=1": "OK",
    "AT+CFUN=0": "OK",
    "AT+CNMP?": "+CNMP: 13\nOK",
    "AT+CNMP=13": "OK",
    "AT+CNSMOD?": "+CNSMOD: 3,1\nOK",

    # Call Commands (simulate)
    "ATD100;": "OK",  # Dial
    "ATH": "OK",      # Hang up
    "ATA": "OK",      # Answer
    "AT+CLIP=1": "OK",
    "AT+CLIR=1": "OK",
    "AT+COLP=1": "OK",

    # TCP/IP Simulated
    "AT+QIOPEN": "OK",
    "AT+QISEND": "> ",
    "AT+QICLOSE": "CLOSED\r\nOK",

    # Echo / Debug / CMEE
    "AT+CMEE=2": "OK",
    "AT+CMEE=1": "OK",
    "AT+CMEE=0": "OK",
    
    # Custom (Cavli-style)
    "AT+CAVLIINFO": "+CAVLIINFO: Device=C20QS, FW=1.2.3\r\nOK",
    "AT+CAVLISTATE": "+CAVLISTATE: RUNNING\r\nOK",
    "AT+CAVLITEMP?": "+CAVLITEMP: 37.2C\r\nOK",
    
    # GPIO Simulation
    "AT+GPIO=1,1": "OK",
    "AT+GPIO=1,0": "OK",
    "AT+GPIOREAD=1": "+GPIO: 1,1\r\nOK",
    
    # Power/Sleep Control
    "AT+CSCLK=1": "OK",
    "AT+CSCLK=0": "OK",
    
    # Extended Info
    "AT+CGATT=1": "OK",
    "AT+CGATT=0": "OK",
    
    # Storage
    "AT+CPMS?": "+CPMS: \"ME\",10,20,\"ME\",10,20,\"ME\",10,20\r\nOK",

    # USSD
    "AT+CUSD=1": "OK",
    "AT+CUSD=2": "OK",
    
    # Time & Clock
    "AT+CCLK?": "+CCLK: \"25/07/16,12:34:56+00\"\r\nOK",

    # Misc (Padding to hit ~100)
    "AT+FCLASS?": "+FCLASS: 0\r\nOK",
    "AT+VTD?": "+VTD: 5\r\nOK",
    "AT+COLP?": "+COLP: 1\r\nOK",
    "AT+CR=1": "OK",
    "AT+CRC=1": "OK",
    "AT+ILRR?": "+ILRR: 0\r\nOK",
    "AT+VTS=5": "OK",
    "AT+CLIR?": "+CLIR: 1,1\r\nOK",
    "AT+CLIP?": "+CLIP: 1,1\r\nOK",
}

# === MAIN LOOP ===
while True:
    try:
        byte = ser.read()
        if not byte:
            continue

        char = byte.decode("utf-8", errors="ignore")

        if char in ['\r', '\n']:
            command = command_buffer.strip()

            if command:
                print(f"> {command}")

                # Handle SMS send mode
                if sms_send_mode:
                    sms_memory[1] = f"TO:{sms_number}, TEXT:{command}"
                    sms_send_mode = False
                    ser.write(b'\r\n+CMGS: 1\r\nOK\r\n')
                    command_buffer = ""
                    continue

                # Handle CMGS separately
                if command.upper().startswith("AT+CMGS="):
                    try:
                        sms_number = command.split('=')[1].strip('"')
                    except:
                        sms_number = "Unknown"
                    sms_send_mode = True
                    ser.write(b'> ')
                    command_buffer = ""
                    continue

                # Handle CMGR
                elif command.upper().startswith("AT+CMGR=1"):
                    if 1 in sms_memory:
                        message = sms_memory[1]
                        ser.write(f'+CMGR: "REC READ","{sms_number}",,"25/07/16,12:00:00"\r\n{message}\r\nOK\r\n'.encode())
                    else:
                        ser.write(b'+CMGR: 0\r\nOK\r\n')
                    command_buffer = ""
                    continue

                # Normal command responses
                response = at_responses.get(command.upper(), None)
                if response is not None:
                    ser.write((response + '\r\n').encode())
                else:
                    if verbose_errors:
                        ser.write(b'+CME ERROR: invalid command\r\n')
                    else:
                        ser.write(b'ERROR\r\n')

            command_buffer = ""

        else:
            command_buffer += char

    except Exception as e:
        print("Error", e)
        break
