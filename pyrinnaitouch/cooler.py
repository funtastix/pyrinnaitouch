"""Cooling unit handling"""
import logging

from .util import get_attribute, y_n_to_bool

_LOGGER = logging.getLogger(__name__)

def HandleCoolingMode(j,brivisStatus):
    cfg = get_attribute(j[1].get("CGOM"),"CFG",None)
    if not cfg:
        # Probably an error
        _LOGGER.error("No CFG - Not happy, Jan")

    else:
        if y_n_to_bool(get_attribute(cfg, "ZAIS", None)):
            brivisStatus.coolingStatus.zones.append("A")
        if y_n_to_bool(get_attribute(cfg, "ZBIS", None)):
            brivisStatus.coolingStatus.zones.append("B")
        if y_n_to_bool(get_attribute(cfg, "ZCIS", None)):
            brivisStatus.coolingStatus.zones.append("C")
        if y_n_to_bool(get_attribute(cfg, "ZDIS", None)):
            brivisStatus.coolingStatus.zones.append("D")

    oop = get_attribute(j[1].get("CGOM"),"OOP",None)
    if not oop:
        # Probably an error
        _LOGGER.error("No OOP - Not happy, Jan")

    else:
        switch = get_attribute(oop,"ST",None)
        if switch == "N":
            _LOGGER.debug("Cooling is ON")
            brivisStatus.systemOn = True
            brivisStatus.coolingStatus.coolingOn = True
            brivisStatus.coolingStatus.CirculationFanOn(switch)

            # Cooling is on - get attributes
            fanSpeed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fanSpeed)
            brivisStatus.coolingStatus.fanSpeed = int(fanSpeed) # Should catch errors!

            # GSO should be there
            gso = get_attribute(j[1].get("CGOM"),"GSO",None)
            if not gso:
                # Probably an error
                _LOGGER.error("No GSO when cooling on. Not happy, Jan")
            else:
                # Cooling is on - get attributes
                opMode = get_attribute(gso,"OP",None)
                _LOGGER.debug("Cooling OpMode is: %s", opMode) # A = Auto, M = Manual
                brivisStatus.coolingStatus.SetMode(opMode)

                # Set temp?
                setTemp = get_attribute(gso,"SP",None)
                _LOGGER.debug("Cooling set temp is: %s", setTemp)
                brivisStatus.coolingStatus.setTemp = int(setTemp)

        elif switch == "Y":
            # Cooling is off
            _LOGGER.debug("Cooling is OFF")
            brivisStatus.systemOn = False
            brivisStatus.coolingStatus.coolingOn = False
            brivisStatus.coolingStatus.CirculationFanOn(switch)

        elif switch == "Z":
            _LOGGER.debug("Circulation Fan is: %s", switch)
            brivisStatus.systemOn = True
            brivisStatus.coolingStatus.CirculationFanOn(switch)

            fanSpeed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fanSpeed)
            brivisStatus.coolingStatus.fanSpeed = int(fanSpeed) # Should catch errors!

        za = zb = zc = zd = None
        z = get_attribute(j[1].get("CGOM"),"ZAO",None)
        if z:
            za = get_attribute(z,"UE",None)
            brivisStatus.coolingStatus.zoneAsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("CGOM"),"ZBO",None)
        if z:
            zb = get_attribute(z,"UE",None)
            brivisStatus.coolingStatus.zoneBsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("CGOM"),"ZCO",None)
        if z:
            zc = get_attribute(z,"UE",None)
            brivisStatus.coolingStatus.zoneCsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("CGOM"),"ZDO",None)
        if z:
            zd = get_attribute(z,"UE",None)
            brivisStatus.coolingStatus.zoneDsetTemp = get_attribute(z,"SP", 999)
        brivisStatus.coolingStatus.SetZones(za,zb,zc,zd)

        z = get_attribute(j[1].get("CGOM"),"ZAS",None)
        if z:
            brivisStatus.coolingStatus.zoneAAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.coolingStatus.zoneAtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("CGOM"),"ZBS",None)
        if z:
            brivisStatus.coolingStatus.zoneBAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.coolingStatus.zoneBtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("CGOM"),"ZCS",None)
        if z:
            brivisStatus.coolingStatus.zoneCAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.coolingStatus.zoneCtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("CGOM"),"ZDS",None)
        if z:
            brivisStatus.coolingStatus.zoneDAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.coolingStatus.zoneDtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("CGOM"),"ZUS",None)
        if z:
            brivisStatus.coolingStatus.commonAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.coolingStatus.temperature = get_attribute(z,"MT", 999)

class CoolingStatus():
    """Cooling function status"""
    coolingOn = False
    fanSpeed = 0
    circulationFanOn = False
    manualMode = False
    autoMode = False
    setTemp = 0
    commonAuto = False
    temperature = 999

    #zones
    zones = []
    zoneA = False
    zoneAAuto = False
    zoneAtemp = 999
    zoneAsetTemp = 999
    zoneB = False
    zoneBAuto = False
    zoneBtemp = 999
    zoneBsetTemp = 999
    zoneC = False
    zoneCAuto = False
    zoneCtemp = 999
    zoneCsetTemp = 999
    zoneD = False
    zoneDAuto = False
    zoneDtemp = 999
    zoneDsetTemp = 999

    def SetMode(self,mode):
        # A = Auto Mode and M = Manual Mode
        if mode == "A":
            self.autoMode = True
            self.manualMode = False
        elif mode == "M":
            self.autoMode = False
            self.manualMode = True

    def SetZones(self,za,zb,zc,zd):
        # Y = On, N = off
        self.zoneA = y_n_to_bool(za)
        self.zoneB = y_n_to_bool(zb)
        self.zoneC = y_n_to_bool(zc)
        self.zoneD = y_n_to_bool(zd)

    def CirculationFanOn(self,statusStr):
        # Z = On, N = Off
        if statusStr == "Z":
            self.circulationFanOn = True
        else:
            self.circulationFanOn = False
