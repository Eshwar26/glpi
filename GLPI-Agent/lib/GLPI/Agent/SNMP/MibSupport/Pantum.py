# pantum_mib.py
from typing import Optional

from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match, is_integer

# MIB constants
MIB2 = '.1.3.6.1.2.1'
ENTERPRISES = '.1.3.6.1.4.1'

# Pantum private
PANTUM = ENTERPRISES + '.40093'
PANTUM_PRINTER = PANTUM + '.1.1'
PANTUM_FW_VERSION = PANTUM_PRINTER + '.1.1'
PANTUM_RAM = PANTUM_PRINTER + '.1.2'
PANTUM_SERIAL_NUMBER1 = PANTUM_PRINTER + '.1.5'
PANTUM_SERIAL_NUMBER2 = PANTUM + '.6.1.2'
PANTUM_SERIAL_NUMBER3 = PANTUM + '.10.1.1.4'
PANTUM_COUNTERS = PANTUM_PRINTER + '.3'

# Printer-MIB
PRINTMIB = MIB2 + '.43'
PRT_GENERAL_PRINTER_NAME = PRINTMIB + '.5.1.1.16.1'
PRT_MARKER_SUPPLIES_ENTRY = PRINTMIB + '.11.1.1'
PRT_MARKER_COLORANT_ENTRY = PRINTMIB + '.12.1.1'


class Pantum(MibSupportTemplate):
    mib_support = [
        {"name": "pantum-printer", "sysobjectid": get_regexp_oid_match(PANTUM_PRINTER)}
    ]

    def get_model(self) -> Optional[str]:
        return self.get(PRT_GENERAL_PRINTER_NAME)

    @staticmethod
    def get_manufacturer() -> str:
        return "Pantum"

    def get_serial(self) -> Optional[str]:
        return self.get(PANTUM_SERIAL_NUMBER1) \
               or self.get(PANTUM_SERIAL_NUMBER2) \
               or self.get(PANTUM_SERIAL_NUMBER3)

    def run(self):
        device = self.device
        if not device:
            return

        # Consumable types mapping
        consumable_types = {
            3: 'TONER', 4: 'WASTETONER', 5: 'CARTRIDGE', 6: 'CARTRIDGE', 8: 'WASTETONER',
            9: 'DRUM', 10: 'DEVELOPER', 12: 'CARTRIDGE', 15: 'FUSERKIT', 18: 'MAINTENANCEKIT',
            20: 'TRANSFERKIT', 21: 'TONER', 32: 'STAPLES'
        }

        max_val = self.get(PRT_MARKER_SUPPLIES_ENTRY + '.8.1')
        current_val = self.get(PRT_MARKER_SUPPLIES_ENTRY + '.9.1')

        if max_val is not None and current_val is not None:
            type_id = self.get(PRT_MARKER_SUPPLIES_ENTRY + '.5.1')
            description = get_canonical_string(self.get(PRT_MARKER_SUPPLIES_ENTRY + '.6.1') or '')

            type_name = consumable_types.get(type_id) if type_id and type_id != 1 else None

            if not type_name:
                desc_lower = description.lower()
                if 'maintenance' in desc_lower:
                    type_name = 'MAINTENANCEKIT'
                elif 'fuser' in desc_lower:
                    type_name = 'FUSERKIT'
                elif 'transfer' in desc_lower:
                    type_name = 'TRANSFERKIT'

            if type_name in ['TONER', 'DRUM', 'CARTRIDGE', 'DEVELOPER']:
                color = get_canonical_string(self.get(PRT_MARKER_COLORANT_ENTRY + '.4.1'))
                if not color:
                    desc_lower = description.lower()
                    if 'cyan' in desc_lower:
                        color = 'cyan'
                    elif 'magenta' in desc_lower:
                        color = 'magenta'
                    elif 'yellow' in desc_lower or 'jaune' in desc_lower:
                        color = 'yellow'
                    else:
                        color = 'black'
                type_name += color.upper()

            # Compute consumable value
            if current_val == -2:
                value = 'WARNING'
            elif current_val == -3:
                value = 'OK'
            elif is_integer(max_val) and max_val >= 0:
                value = int((100 * current_val) / max_val) if is_integer(current_val) and max_val > 0 else None
            else:
                unit_id = self.get(PRT_MARKER_SUPPLIES_ENTRY + '.7.1')
                if unit_id == 19:
                    value = current_val
                elif unit_id == 18:
                    value = f"{current_val} items"
                elif unit_id == 17:
                    value = f"{current_val} m"
                elif unit_id == 16:
                    value = f"{current_val} feet"
                elif unit_id == 15:
                    value = f"{current_val / 10} ml"
                elif unit_id == 13:
                    value = f"{current_val / 10} g"
                elif unit_id == 11:
                    value = f"{current_val} hours"
                elif unit_id == 8:
                    value = f"{current_val} sheets"
                elif unit_id == 7:
                    value = f"{current_val} impressions"
                elif unit_id == 4:
                    value = f"{current_val / 1000} mm"
                else:
                    value = current_val

            if type_name and value is not None:
                device.CARTRIDGES[type_name] = value

        ram_val = self.get(PANTUM_RAM)
        if ram_val is not None and is_integer(ram_val):
            device.INFO['RAM'] = ram_val

        counters = self.walk(PANTUM_COUNTERS) or {}
        if counters:
            total = 0
            mapping = {1: 'DUPLEX', 9: 'COPYTOTAL', 12: 'PRINTTOTAL'}
            for key, name in mapping.items():
                count = counters.get(key)
                if count is not None and is_integer(count):
                    device.PAGECOUNTERS[name] = count
                    total += count
            device.PAGECOUNTERS['TOTAL'] = total

        version = get_canonical_string(self.get(PANTUM_FW_VERSION))
        if version:
            firmware = {
                "NAME": f"Pantum {device.MODEL} firmware",
                "DESCRIPTION": f"Pantum {device.MODEL} firmware version",
                "TYPE": "printer",
                "VERSION": version,
                "MANUFACTURER": "Pantum"
            }
            device.add_firmware(firmware)
