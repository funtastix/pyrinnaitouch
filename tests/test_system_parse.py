from pyrinnaitouch.system import RinnaiSystem

def get_test_json():
    """Fixture to return a sample JSON response str"""
    return '[{"SYST": {"CFG": {"MTSP": "N", "NC": "00", "DF": "N", "TU": "C", "CF": "1", "VR": "0183", "CV": "0010", "CC": "043", "ZA": " ", "ZB": " ", "ZC": " ", "ZD": " " }, "AVM": {"HG": "Y", "EC": "N", "CG": "Y", "RA": "N", "RH": "N", "RC": "N" }, "OSS": {"DY": "TUE", "TM": "16:45", "BP": "Y", "RG": "Y", "ST": "N", "MD": "C", "DE": "N", "DU": "N", "AT": "999", "LO": "N" }, "FLT": {"AV": "N", "C3": "000" } } },{"CGOM": {"CFG": {"ZUIS": "N", "ZAIS": "Y", "ZBIS": "Y", "ZCIS": "N", "ZDIS": "N", "CF": "N", "PS": "Y", "DG": "W" }, "OOP": {"ST": "F", "CF": "N", "FL": "00", "SN": "Y" }, "GSS": {"CC": "N", "FS": "N", "CP": "N" }, "APS": {"AV": "N" }, "ZUS": {"AE": "N", "MT": "999" }, "ZAS": {"AE": "N", "MT": "999" }, "ZBS": {"AE": "N", "MT": "999" }, "ZCS": {"AE": "N", "MT": "999" }, "ZDS": {"AE": "N", "MT": "999" } } }]'

def test_zones(self):
    system = RinnaiSystem.getInstance("10.0.0.1")
    assert system
