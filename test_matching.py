import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "custom_components")
from storm_warnings import matching, parse_meteoalarm, parse_nws

now = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
day = timedelta(hours=24)
types = ["wind", "rain", "thunder", "snow", "ice", "storm", "tornado", "hurricane", "blizzard", "winter"]


def at(h):
    return (now + timedelta(hours=h)).isoformat()


def w(level="yellow", type_="Wind", regions=("EI04",), onset_h=10, expiry_h=20):
    return {"level": level, "type": type_, "regions": list(regions), "headline": "x",
            "onset": at(onset_h), "expiry": at(expiry_h)}


# matching
assert matching([w()], ["EI04"], now, day, "yellow", types)                       # due within 24h
assert not matching([w(onset_h=30, expiry_h=40)], ["EI04"], now, day)             # too far ahead
assert matching([w(onset_h=-5, expiry_h=1)], ["EI04"], now, day)                  # in progress
assert not matching([w(onset_h=-5, expiry_h=0)], ["EI04"], now, day)              # just ended
assert not matching([w(regions=["EI07"])], ["EI04"], now, day)                    # other county
assert matching([w(regions=[])], ["EI04"], now, day)                              # nationwide
assert not matching([w(type_="Fog")], ["EI04"], now, day, "yellow", types)        # not a storm type
assert not matching([w()], ["EI04"], now, day, "orange")                          # below min level
assert matching([w(level="red")], ["EI04"], now, day, "orange")

# MeteoAlarm
ma = {"warnings": [{"alert": {"info": [{
    "parameter": [{"valueName": "awareness_level", "value": "3; orange; Severe"},
                  {"valueName": "awareness_type", "value": "1; Wind"}],
    "area": [{"areaDesc": "Cork", "geocode": [{"valueName": "EMMA_ID", "value": "EI04"}]}],
    "onset": at(2), "effective": at(0), "expires": at(8), "headline": "Orange wind"}]}}]}
[m] = parse_meteoalarm(ma)
assert (m["level"], m["type"], m["regions"], m["onset"]) == ("orange", "Wind", ["EI04"], at(2))
assert matching([m], ["EI04"], now, day, "yellow", types)

# NWS
nws = {"features": [
    {"properties": {"severity": "Severe", "event": "High Wind Warning", "onset": at(3), "effective": at(0),
                    "ends": at(30), "expires": at(4), "headline": "HWW"}},
    {"properties": {"severity": "Minor", "event": "High Surf Advisory", "onset": at(0), "effective": at(0),
                    "ends": None, "expires": at(4), "headline": None}},
]}
hww, surf = parse_nws(nws)
assert (hww["level"], hww["expiry"]) == ("orange", at(30))                        # uses ends, not expires
assert surf["level"] is None and surf["expiry"] == at(4) and surf["headline"] == "High Surf Advisory"
assert matching([hww, surf], [], now, day, "yellow", types) == [hww]
print("ok")
