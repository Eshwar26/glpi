import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_country_mcc(mcc):
    # Mock implementation - in real, would use GLPI::Agent::Tools::Standards::MobileCountryCode
    mock_countries = {'310': 'US', '311': 'US', '312': 'US'}  # Example
    return mock_countries.get(mcc, 'Unknown')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.16378.10000.3.16.0': 'FW 1.2.3',  # sarianSystem .16.0 (firmware)
            '.1.3.6.1.4.1.16378.10000.3.15.0': 'SN123456789',  # sarianSystem .15.0 (serial)
        }
        return mock_values.get(oid, None)

    def walk(self, oid):
        # Mock SNMP walk; returns dict of index: value
        if oid == '.1.3.6.1.4.1.16378.10000.3':  # sarianSystem
            return {
                '14.0': 'Digi Transport WR21',  # sarianSystem .14.0 (description?)
                '19.0': 'WR21',  # sarianSystem .19.0 (model)
                '20.0': 'Modem FW 4.5',  # sarianSystem .20.0 (modem firmware version)
            }
        elif oid == '.1.3.6.1.4.1.16378.10000.2':  # sarianGPRS
            return {
                '21.0': '123456789012345',  # gprsIMSI
                '20.0': '89812345678901234567',  # gprsICCID
                '22.0': 'Operator Name, 310, 120',  # gprsNetwork
                '26.0': 'Active',  # gprsSIMStatus
                '30.0': '1',  # gprsCurrentSIM
                '19.0': 'IMEI12345678901234',  # gprsIMEI
                '7.0': '3',  # gprsNetworkTechnology (edge)
            }
        return {}

# Mock Device class for compatibility
class MockDevice:
    def __init__(self):
        self.simcards = []
        self.modems = []
        self.firmwares = []

    def add_simcard(self, simcard):
        self.simcards.append(simcard)
        print(f"Added simcard: {simcard}")

    def add_modem(self, modem):
        self.modems.append(modem)
        print(f"Added modem: {modem}")

    def add_firmware(self, firmware):
        self.firmwares.append(firmware)
        print(f"Added firmware: {firmware}")

# Constants
SARIAN_MONITOR = ".1.3.6.1.4.1.16378.10000"
SARIAN_GPRS = SARIAN_MONITOR + ".2"
SARIAN_SYSTEM = SARIAN_MONITOR + ".3"

gprs_network_technology = ['-', 'unknown', 'gprs', 'edge', 'umts', 'hsdpa', 'hsupa', 'hspa', 'lte']  # Index 0 unused, starts from 1

mib_support = [
    {
        'name': "sarianMonitor",
        'oid': SARIAN_MONITOR
    }
]

class Digi(MibSupportTemplate):
    def get_firmware(self):
        return self.get(SARIAN_SYSTEM + '.16.0')

    def get_serial(self):
        return self.get(SARIAN_SYSTEM + '.15.0')

    def run(self):
        device = self.device
        if not device:
            return

        sarian_system = self.walk(SARIAN_SYSTEM)

        # Handle modem Digi private OIDs if found
        if sarian_system:
            modem = {
                'NAME': "Digi modem",
                'DESCRIPTION': sarian_system.get('14.0', ''),
                'MODEL': sarian_system.get('19.0', ''),
                'MANUFACTURER': "Digi",
            }

            # Handle SIM card looking for GRPS status
            sarian_gprs = self.walk(SARIAN_GPRS)
            if sarian_gprs:
                simcard = {
                    'IMSI': sarian_gprs.get('21.0'),  # gprsIMSI
                    'ICCID': sarian_gprs.get('20.0'),  # gprsICCID
                }

                operator = sarian_gprs.get('22.0')  # gprsNetwork
                if operator:
                    match = re.match(r'^(.*),\s*(\d{3})(\d+)$', operator)
                    if match:
                        name, mcc, mnc = match.groups()
                        simcard['OPERATOR_NAME'] = name
                        if mcc:
                            simcard['OPERATOR_CODE'] = f"{mcc}.{mnc}" if mnc else None
                            simcard['COUNTRY'] = get_country_mcc(mcc)

                # Include used SIM in STATE
                sim_status = sarian_gprs.get('26.0')  # gprsSIMStatus
                sim_number = sarian_gprs.get('30.0')  # gprsCurrentSIM
                simcard['STATE'] = (f"SIM{sim_number} - " if sim_number else "") + (sim_status or "")

                device.add_simcard(simcard)

                # use IMEI as modem serial
                modem['SERIAL'] = sarian_gprs.get('19.0')  # gprsIMEI

                # set modem type
                techno = sarian_gprs.get('7.0')  # gprsNetworkTechnology
                if techno and int(techno) <= len(gprs_network_technology):
                    modem['TYPE'] = gprs_network_technology[int(techno)]

            device.add_modem(modem)

            # Add modem firmware
            modem_firmware = {
                'NAME': "Digi modem",
                'DESCRIPTION': f"Digi {sarian_system.get('19.0', '')} modem",
                'TYPE': "modem",
                'VERSION': sarian_system.get('20.0'),
                'MANUFACTURER': "Digi"
            }

            device.add_firmware(modem_firmware)

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device for testing
    mock_device = MockDevice()

    # Test instantiation
    digi = Digi()
    digi.device = mock_device
    print("Firmware:", digi.get_firmware())
    print("Serial:", digi.get_serial())
    print("Before run - Simcards:", len(mock_device.simcards))
    print("Before run - Modems:", len(mock_device.modems))
    print("Before run - Firmwares:", len(mock_device.firmwares))
    digi.run()
    print("After run - Simcards:", len(mock_device.simcards))
    print("After run - Modems:", len(mock_device.modems))
    print("After run - Firmwares:", len(mock_device.firmwares))
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Digi - Inventory module for Digi modems and associated sim cards & firmwares

The module adds SIMCARDS, MODEMS & FIRMWARES support for Digi devices
"""
