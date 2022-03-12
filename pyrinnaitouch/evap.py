"""Evap unit handling"""
import logging

from .util import get_attribute, y_n_to_bool

_LOGGER = logging.getLogger(__name__)

def HandleEvapMode(j,brivisStatus):
    cfg = get_attribute(j[1].get("ECOM"),"CFG",None)
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

    gso = get_attribute(j[1].get("ECOM"),"GSO",None)
    if not gso:
        _LOGGER.error("No GSO here")
    else:
        #_LOGGER.debug("Looking at: {}".format(gso))
        switch = get_attribute(gso,"SW", None)
        if switch == "N":
            opmode = get_attribute(gso, "OP", None)
            #_LOGGER.debug("setting opmode: {}".format(opmode))
            brivisStatus.evapStatus.SetMode(opmode)

            _LOGGER.debug("EVAP is ON")
            brivisStatus.systemOn = True
            brivisStatus.evapStatus.evapOn = True

            if opmode == "M":
                # Evap is on and manual - what is the fan speed
                evapFan = get_attribute(gso,"FS",None)
                _LOGGER.debug("Fan is: %s", evapFan)
                brivisStatus.evapStatus.FanOn(evapFan)
            
                fanSpeed = get_attribute(gso,"FL",None)
                _LOGGER.debug("Fan Speed is: %s", fanSpeed)
                brivisStatus.evapStatus.FanSpeed(int(fanSpeed))

                waterPump = get_attribute(gso,"PS",None)
                _LOGGER.debug("Water Pump is: %s", waterPump)
                brivisStatus.evapStatus.WaterPumpOn(waterPump)

                brivisStatus.evapStatus.zoneA = y_n_to_bool(get_attribute(gso,"ZAUE",False))
                brivisStatus.evapStatus.zoneB = y_n_to_bool(get_attribute(gso,"ZBUE",False))
                brivisStatus.evapStatus.zoneC = y_n_to_bool(get_attribute(gso,"ZCUE",False))
                brivisStatus.evapStatus.zoneD = y_n_to_bool(get_attribute(gso,"ZDUE",False))

            else:
                # Evap is on and auto - look for comfort level
                comfort = get_attribute(gso, "SP", 0)
                _LOGGER.debug("Comfort Level is: %s", comfort)
                brivisStatus.evapStatus.Comfort(comfort)

                brivisStatus.evapStatus.zoneA = False
                brivisStatus.evapStatus.zoneB = False
                brivisStatus.evapStatus.zoneC = False
                brivisStatus.evapStatus.zoneD = False

            gss = get_attribute(j[1].get("ECOM"),"GSS",None)
            if not gss:
                _LOGGER.error("No GSS here")
            else:
                brivisStatus.evapStatus.commonAuto = y_n_to_bool(get_attribute(gss,"ZUAE",False))
                brivisStatus.evapStatus.zoneAAuto = y_n_to_bool(get_attribute(gss,"ZAAE",False))
                brivisStatus.evapStatus.zoneBAuto = y_n_to_bool(get_attribute(gss,"ZBAE",False))
                brivisStatus.evapStatus.zoneCAuto = y_n_to_bool(get_attribute(gss,"ZCAE",False))
                brivisStatus.evapStatus.zoneDAuto = y_n_to_bool(get_attribute(gss,"ZDAE",False))
                
                brivisStatus.evapStatus.prewetting = y_n_to_bool(get_attribute(gss,"PW",False))
                brivisStatus.evapStatus.coolerBusy = y_n_to_bool(get_attribute(gss,"BY",False))


        elif switch == "F":
            # Evap is off
            _LOGGER.debug("EVAP is OFF")
            brivisStatus.systemOn = False
            brivisStatus.evapStatus.evapOn = False

            brivisStatus.evapStatus.zoneA = False
            brivisStatus.evapStatus.zoneB = False
            brivisStatus.evapStatus.zoneC = False
            brivisStatus.evapStatus.zoneD = False

            brivisStatus.evapStatus.commonAuto = False
            brivisStatus.evapStatus.zoneAAuto = False
            brivisStatus.evapStatus.zoneBAuto = False
            brivisStatus.evapStatus.zoneCAuto = False
            brivisStatus.evapStatus.zoneDAuto = False

class EvapStatus():
    """Evap function status"""
    evapOn = False
    manualMode = False
    autoMode = False
    fanOn = False
    fanSpeed = 0
    waterPumpOn = False
    comfort = 0
    commonAuto = False
    temperature = 999
    prewetting = False
    coolerBusy = False

    #zones
    zones = []
    zoneA = False
    zoneAAuto = False
    zoneB = False
    zoneBAuto = False
    zoneC = False
    zoneCAuto = False
    zoneD = False
    zoneDAuto = False

    def FanOn(self,statusStr):
        # N = On, F = Off
        if statusStr == "N":
            self.fanOn = True
        else:
            self.fanOn = False

    def FanSpeed(self,speedInt):
        self.fanSpeed = speedInt

    def WaterPumpOn(self,statusStr):
        # N = On, F = Off
        if statusStr == "N":
            self.waterPumpOn = True
        else:
            self.waterPumpOn = False

    def SetMode(self,mode):
        # A = Auto Mode and M = Manual Mode
        if mode == "A":
            self.autoMode = True
            self.manualMode = False
        elif mode == "M":
            self.autoMode = False
            self.manualMode = True

    def Comfort(self, comfort):
        self.comfort = comfort

