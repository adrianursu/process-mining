import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from alive_progress import alive_bar
 
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
ZONE = "+00:00"

# Function to create XML element with namespaces
def create_event_element(attributes):
    event_elem = ET.Element("event")
    for key, value in attributes.items():
        if key == "time:timestamp":
            ET.SubElement(event_elem, "date", key=key, value=value)
        elif key == "money" or key == "total_dmg":
            ET.SubElement(event_elem, "int", key=key, value=str(value))
        else:
            ET.SubElement(event_elem, "string", key=key, value=str(value))
    return event_elem

def normalize_timestamp(timestamp: str, reference: str):
    dt = datetime.fromisoformat(timestamp)
    ref = datetime.fromisoformat(reference)

    diff = dt - ref

    new = datetime(1970, 1, 1, 0, 0, 0) + diff

    return new.strftime(TIME_FORMAT)[:-3] + ZONE

# Main conversion function
def json_log_to_xes(json_data):
    # Define the XES namespaces and root element
    xes_ns = "http://www.xes-standard.org/"
    root = ET.Element("log", xmlns=xes_ns)
    ET.SubElement(root, "string", key="concept:name", value="round-based-cs-game")
    
    match_no = 0

    with alive_bar(len(json_data), bar="bubbles", spinner="dots", title="Convert JSON to XES", 
                   length=60, max_cols=130, force_tty=True) as bar:
        # Loop over each round in JSON, treating each as a trace
        for round_data in json_data:
            trace = ET.SubElement(root, "trace")
            round_time = round_data["timestamp"]

            if round_data["round_number"] == 1:
                match_no += 1

            if round_data["kill_events"] == None:
                continue

            # Define the general attributes for the round
            ET.SubElement(trace, "string", key="concept:name", value=f"round-{round_data['round_number']}-{match_no}")
            ET.SubElement(trace, "string", key="winner", value=round_data["winner"])
            ET.SubElement(trace, "string", key="end_reason", value=round_data["end_reason"])
            ET.SubElement(trace, "int", key="t_score", value=str(round_data["t_score"]))
            ET.SubElement(trace, "int", key="ct_score", value=str(round_data["ct_score"]))
            
            # Add timestamp attributes for the round's start and end
            ET.SubElement(trace, "date", key="time:timestamp", value=round_data["timestamp"] + ZONE)
            ET.SubElement(trace, "date", key="time:end_timestamp", value=round_data["end_timestamp"] + ZONE)

            # Consolidate all events and sort by timestamp
            events = []
            filter_out_team = "[CT]"

            # Add kill events
            if round_data["kill_events"] and len(round_data["kill_events"]) > 0:
                for kill in round_data.get("kill_events", []):
                    if filter_out_team in kill["killer"]:
                        event_attrs = {
                            "org:resource": f"Death",
                            "time:timestamp": normalize_timestamp(kill["timestamp"], round_time),
                            "concept:name": kill["victim"],
                            "killer_place": kill["killer_place"],
                            "killer": kill["killer"],
                            "victim_place": kill["victim_place"],
                            "weapon": kill["weapon"],
                            "headshot": str(kill["headshot"]),
                        }
                        events.append((event_attrs["time:timestamp"], event_attrs))
                        continue
                    event_attrs = {
                        "concept:name": f"Kill {kill["victim"][-4:]}",
                        "time:timestamp": kill["timestamp"],
                        "org:role": kill["killer"],
                        "killer_place": kill["killer_place"],
                        "victim": kill["victim"],
                        "victim_place": kill["victim_place"],
                        "weapon": kill["weapon"],
                        "headshot": str(kill["headshot"]),
                    }
                    events.append((event_attrs["time:timestamp"], event_attrs))

            # Add bomb events
            if round_data["bomb_events"]:
                for bomb_event in round_data.get("bomb_events", []):
                    if filter_out_team in bomb_event["player"]:
                        continue
                    event_attrs = {
                        "org:resource": f"Bomb-{bomb_event["action"]}",
                        "time:timestamp": normalize_timestamp(bomb_event["timestamp"], round_time),
                        "concept:name": bomb_event["player"],
                        "bomb_place": bomb_event["bomb_place"],
                        "action": bomb_event["action"],
                        "success": str(bomb_event["success"]),
                    }
                    events.append((event_attrs["time:timestamp"], event_attrs))

            # Add grenade events
            if round_data["grenade_events"]:
                for grenade_event in round_data.get("grenade_events", []):
                    if filter_out_team in grenade_event["player"]:
                        continue
                    event_attrs = {
                        "org:resource": f"Throw-{grenade_event["grenade"]}-{grenade_event["place"]}",
                        "time:timestamp": normalize_timestamp(grenade_event["timestamp"], round_time),
                        "concept:name": grenade_event["player"],
                        "player_place": grenade_event["place"],
                        "grenade_type": grenade_event["grenade"],
                    }
                    events.append((event_attrs["time:timestamp"], event_attrs))

            # Finalize the trace with a round end event with the available details
            if round_data["winner"] == "CT":
                round_won = "(Win)"
            else:
                round_won = "(Lose)"

            round_end_event = {
                "concept:name": "Round End -" + round_won,
                "time:timestamp": normalize_timestamp(round_data["end_timestamp"], round_time),
                "org:resource": "game",
                "winner": round_data["winner"],
                "reason": round_data["end_reason"]
            }

            events.append((round_end_event["time:timestamp"], round_end_event))

            # Sort events by timestamp and append to trace
            events.sort(key=lambda x: x[0])  # Sort by timestamp
            for _, event_attrs in events:
                trace.append(create_event_element(event_attrs))
            
            bar()

    # Return the XML as a string
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")

# Load the JSON data
with open("navi_demo_data.json") as f:
    json_data = json.load(f)

# Convert JSON to XES format and pretty-print the XML DOM
xes_output = json_log_to_xes(json_data)
xmlstr = minidom.parseString(xes_output).toprettyxml(indent="   ")

# Save to XES file
with open("navi-social-network-terro.xes", "wb") as f:
    f.write(xmlstr.encode("utf-8"))
