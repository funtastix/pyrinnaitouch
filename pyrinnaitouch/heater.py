"""Heater unit handling"""
import logging

from .util import get_attribute, y_n_to_bool

_LOGGER = logging.getLogger(__name__)

def HandleHeatingMode(j,brivisStatus):
    cfg = get_attribute(j[1].get("HGOM"),"CFG",None)
    if not cfg:
        # Probably an error
        _LOGGER.error("No CFG - Not happy, Jan")

    else:
        if y_n_to_bool(get_attribute(cfg, "ZAIS", None)):
            brivisStatus.heaterStatus.zones.append("A")
        if y_n_to_bool(get_attribute(cfg, "ZBIS", None)):
            brivisStatus.heaterStatus.zones.append("B")
        if y_n_to_bool(get_attribute(cfg, "ZCIS", None)):
            brivisStatus.heaterStatus.zones.append("C")
        if y_n_to_bool(get_attribute(cfg, "ZDIS", None)):
            brivisStatus.heaterStatus.zones.append("D")

    oop = get_attribute(j[1].get("HGOM"),"OOP",None)
    if not oop:
        # Probably an error
        _LOGGER.error("No OOP - Not happy, Jan")

    else:
        switch = get_attribute(oop,"ST",None)
        if switch == "N":
            _LOGGER.debug("Heater is ON")
            brivisStatus.systemOn = True
            brivisStatus.heaterStatus.heaterOn = True
            brivisStatus.heaterStatus.CirculationFanOn(switch)

            # Heater is on - get attributes
            fanSpeed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fanSpeed)
            brivisStatus.heaterStatus.fanSpeed = int(fanSpeed) # Should catch errors!

            # GSO should be there
            gso = get_attribute(j[1].get("HGOM"),"GSO",None)
            if not gso:
                # Probably an error
                _LOGGER.error("No GSO when heater on. Not happy, Jan")
            else:
                # Heater is on - get attributes
                opMode = get_attribute(gso,"OP",None)
                _LOGGER.debug("Heat OpMode is: %s", opMode) # A = Auto, M = Manual
                brivisStatus.heaterStatus.SetMode(opMode)

                # Set temp?
                setTemp = get_attribute(gso,"SP",None)
                _LOGGER.debug("Heat set temp is: %s", setTemp)
                brivisStatus.heaterStatus.setTemp = int(setTemp)

                gss = get_attribute(j[1].get("HGOM"),"GSS",None)
                if not gss:
                    _LOGGER.error("No GSS here")
                else:
                    brivisStatus.heaterStatus.preheating = y_n_to_bool(get_attribute(gss,"PH",False))

        elif switch == "F":
            # Heater is off
            _LOGGER.debug("Heater is OFF")
            brivisStatus.systemOn = False
            brivisStatus.heaterStatus.heaterOn = False
            brivisStatus.heaterStatus.CirculationFanOn(switch)

        elif switch == "Z":
            _LOGGER.debug("Circulation Fan is: %s", switch)
            brivisStatus.systemOn = True
            brivisStatus.heaterStatus.heaterOn = False
            brivisStatus.heaterStatus.CirculationFanOn(switch)

            fanSpeed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fanSpeed)
            brivisStatus.heaterStatus.fanSpeed = int(fanSpeed) # Should catch errors!

        za = zb = zc = zd = None
        z = get_attribute(j[1].get("HGOM"),"ZAO",None)
        if z:
            za = get_attribute(z,"UE",None)
            brivisStatus.heaterStatus.zoneAsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("HGOM"),"ZBO",None)
        if z:
            zb = get_attribute(z,"UE",None)
            brivisStatus.heaterStatus.zoneBsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("HGOM"),"ZCO",None)
        if z:
            zc = get_attribute(z,"UE",None)
            brivisStatus.heaterStatus.zoneCsetTemp = get_attribute(z,"SP", 999)
        z = get_attribute(j[1].get("HGOM"),"ZDO",None)
        if z:
            zd = get_attribute(z,"UE",None)
            brivisStatus.heaterStatus.zoneDsetTemp = get_attribute(z,"SP", 999)
        brivisStatus.heaterStatus.SetZones(za,zb,zc,zd)

        z = get_attribute(j[1].get("HGOM"),"ZAS",None)
        if z:
            brivisStatus.heaterStatus.zoneAAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.heaterStatus.zoneAtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("HGOM"),"ZBS",None)
        if z:
            brivisStatus.heaterStatus.zoneBAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.heaterStatus.zoneBtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("HGOM"),"ZCS",None)
        if z:
            brivisStatus.heaterStatus.zoneCAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.heaterStatus.zoneCtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("HGOM"),"ZDS",None)
        if z:
            brivisStatus.heaterStatus.zoneDAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.heaterStatus.zoneDtemp = get_attribute(z,"MT", 999)
        z = get_attribute(j[1].get("HGOM"),"ZUS",None)
        if z:
            brivisStatus.heaterStatus.commonAuto = y_n_to_bool(get_attribute(z,"AE",None))
            brivisStatus.heaterStatus.temperature = get_attribute(z,"MT", 999)

class HeaterStatus():
    """Heater function status"""
    heaterOn = False
    fanSpeed = 0
    circulationFanOn = False
    manualMode = False
    autoMode = False
    setTemp = 0
    commonAuto = False
    temperature = 999
    preheating = False

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


