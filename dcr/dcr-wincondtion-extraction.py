import json
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

import utils

# Load JSON file
with open("../rounds_data.json") as f:
    rounds_data = json.load(f)

# Helper function to create XES elements
def create_trace(round_number, events):
    trace = Element("trace")
    trace_round = SubElement(trace, "string", key="concept:name", value=str(round_number))
    win_condition = None
    for event in events:
        parsed = event["time"].replace("T:", "T")
        event_elem = SubElement(trace, "event")
        SubElement(event_elem, "string", key="concept:name", value=event["type"])
        SubElement(event_elem, "string", key="org:role", value=event["player"])
        if event["type"].startswith("Win"):
            win_condition = event["type"]
        SubElement(event_elem, "date", key="time:timestamp", value=parsed)
        if "victim" in event:
            SubElement(event_elem, "string", key="victim", value=event["victim"])
        if "weapon" in event:
            SubElement(event_elem, "string", key="weapon", value=event["weapon"])
        if "headshot" in event:
            SubElement(event_elem, "boolean", key="headshot", value=str(event["headshot"]).lower())

    return trace, win_condition

# Create XES root element
t_elim = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})
ct_elim = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})
time_out = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})
expl = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})
defuse = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})


# Convert rounds to XES traces
for round_info in rounds_data:
    round_number = round_info["round_number"]
    events = []
    # Process kill events
    if "kill_events" in round_info:
        for kill in round_info["kill_events"]:
            if kill["killer"] == "Unknown":
                events.append({
                    "type": "Bomb explosion kills " + kill["victim"].split(" ")[-1],
                    "time": kill["timestamp"],
                    "player": kill["killer"].split(" ")[-1],
                    "victim": kill["victim"].split(" ")[-1],
                    "weapon": kill["weapon"],
                    "headshot": kill["headshot"]
                })
            else:
                events.append({
                    "type": kill["killer"].split(" ")[-1]+" kills "+kill["victim"].split(" ")[-1],
                    "time": kill["timestamp"],
                    "player": utils.get_weapon_type(kill["weapon"]),
                    "victim": kill["killer"].split(" ")[-1],
                    "weapon": kill["weapon"],
                    "headshot": kill["headshot"]
                })
    if "grenade_events" in round_info and round_info["grenade_events"]:
        for grenade in round_info["grenade_events"]:
            events.append({
                "type": "grenade",
                "time": grenade["timestamp"],
                "player": grenade["player"].split(" ")[-1],
                "player_position": grenade["player_position"],
                "place": grenade["place"],
                "grenade": grenade["grenade"]
            })
    if "weapon_events" in round_info and round_info["weapon_events"]:
        for buy in round_info["weapon_events"]:
            events.append({
                "type": "buy",
                "time": round_info["timestamp"],
                "player": buy["player"].split(" ")[-1],
                "weapon": buy["weapons"]
            })
    if "change_location_events" in round_info and round_info["change_location_events"]:
        for location_change in round_info["change_location_events"]:
            events.append({
                "type": f"to {location_change['new_place']}",
                "time": location_change["timestamp"],
                "player": location_change["player"].split(" ")[-1],
            })
    # Process bomb events
    if "bomb_events" in round_info and round_info["bomb_events"]:
        for bomb in round_info["bomb_events"]:
            events.append({
                "type": f"bomb_{bomb['action']}",
                "time": bomb["timestamp"],
                "player": bomb["player"].split(" ")[-1]
            })
    events.append({
        "type": f"Win condition {round_info["end_reason"]}",
        "time": round_info["end_timestamp"],
        "player": round_info["winner"],
    })
    # Add trace to log
    trace, win_c = create_trace(round_number, events)
    if win_c == "Win condition BombDefused":
        defuse.append(trace)
    if win_c == "Win condition CTEliminated":
        ct_elim.append(trace)
    if win_c == "Win condition BombExploded":
        expl.append(trace)
    if win_c == "Win condition TimeExpired":
        time_out.append(trace)
    if win_c == "Win condition TEliminated":
        t_elim.append(trace)

# Save XES log to file

traces = {"def": defuse,"ct_elim": ct_elim,"expl": expl,"t_elim": t_elim, "time_out": time_out}
for name, t in traces.items():
    dom = xml.dom.minidom.parseString(tostring(t))
    pretty_xml_as_string = dom.toprettyxml()

    with open(f"{name}.xes", "w") as xes_file:
        xes_file.write(pretty_xml_as_string)

print("Conversion to XES completed. Saved as 'rounds_data.xes'.")