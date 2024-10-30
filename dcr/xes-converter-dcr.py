import json
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

from dcr import utils

# Load JSON file
with open("../rounds_data.json") as f:
    rounds_data = json.load(f)

# Helper function to create XES elements
def create_trace(round_number, events):
    trace = Element("trace")
    trace_round = SubElement(trace, "string", key="concept:name", value=str(round_number))

    for event in events:
        parsed = event["time"].replace("T:", "T")
        event_elem = SubElement(trace, "event")
        SubElement(event_elem, "string", key="concept:name", value=event["type"])
        SubElement(event_elem, "string", key="org:role", value=event["player"])

        SubElement(event_elem, "date", key="time:timestamp", value=parsed)
        if "victim" in event:
            SubElement(event_elem, "string", key="victim", value=event["victim"])
        if "weapon" in event:
            SubElement(event_elem, "string", key="weapon", value=event["weapon"])
        if "headshot" in event:
            SubElement(event_elem, "boolean", key="headshot", value=str(event["headshot"]).lower())

    return trace

# Create XES root element
xes_log = Element("log", {"xes.version": "1.0", "xes.features": "", "openxes.version": "1.0RC7", "xmlns": "http://www.xes-standard.org/"})

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
    trace = create_trace(round_number, events)
    xes_log.append(trace)

# Save XES log to file
dom = xml.dom.minidom.parseString(tostring(xes_log))
pretty_xml_as_string = dom.toprettyxml()

with open("../rounds_data.xes", "w") as xes_file:
    xes_file.write(pretty_xml_as_string)

print("Conversion to XES completed. Saved as 'rounds_data.xes'.")