import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from alive_progress import alive_bar
 
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"

# Function to create XML element with namespaces
def create_event_element(attributes):
    event_elem = ET.Element("event")
    for key, value in attributes.items():
        ET.SubElement(event_elem, "string", key=key, value=str(value))
    return event_elem

# Main conversion function
def json_log_to_xes(json_data):
    # Define the XES namespaces and root element
    xes_ns = "http://www.xes-standard.org/"
    root = ET.Element("log", xmlns=xes_ns)
    ET.SubElement(root, "string", key="concept:name", value="round-based-cs-game")
    
    
    with alive_bar(len(json_data), bar="bubbles", spinner="dots", title="Convert JSON to XES", 
                   length=60, max_cols=130, force_tty=True) as bar:
        # Loop over each round in JSON, treating each as a trace
        for round_data in json_data:
            trace = ET.SubElement(root, "trace")
            
            # Define the general attributes for the round
            ET.SubElement(trace, "string", key="concept:name", value=f"round-{round_data['round_number']}")
            ET.SubElement(trace, "string", key="winner", value=round_data["winner"])
            ET.SubElement(trace, "string", key="end_reason", value=round_data["end_reason"])
            ET.SubElement(trace, "int", key="t_score", value=str(round_data["t_score"]))
            ET.SubElement(trace, "int", key="ct_score", value=str(round_data["ct_score"]))
            
            # Add timestamp attributes for the round's start and end
            ET.SubElement(trace, "date", key="time:timestamp", value=round_data["timestamp"])
            ET.SubElement(trace, "date", key="time:end_timestamp", value=round_data["end_timestamp"])

            # Consolidate all events and sort by timestamp
            events = []
            
            # Add kill events
            if "kill_events" in round_data and len(round_data["kill_events"]) > 0:    
                for kill in round_data.get("kill_events", []):
                    event_attrs = {
                        "concept:name": f"Kill {kill['victim'][-4:]}",
                        "time:timestamp": kill["timestamp"],
                        "org:role": kill['killer'],
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
                    event_attrs = {
                        "concept:name": f"Bomb-{bomb_event['action']}",
                        "time:timestamp": bomb_event["timestamp"],
                        "player": bomb_event["player"],
                        "bomb_place": bomb_event["bomb_place"],
                        "action": bomb_event["action"],
                        "success": str(bomb_event["success"]),
                    }
                    events.append((event_attrs["time:timestamp"], event_attrs))

            # Add grenade events
            if round_data["grenade_events"]:
                for grenade_event in round_data.get("grenade_events", []):
                    event_attrs = {
                        "concept:name": f"Throw-{grenade_event['grenade']}",
                        "time:timestamp": grenade_event["timestamp"],
                        "org:role": grenade_event["player"],
                        "player_place": grenade_event["place"],
                        "grenade_type": grenade_event["grenade"],
                    }
                    events.append((event_attrs["time:timestamp"], event_attrs))

            # Add weapon events without timestamps (default to start time if applicable)
            start_timestamp = round_data["timestamp"]
            for weapon_event in round_data.get("weapon_events", []):
                event_attrs = {
                    "concept:name": f"Inventory Check",
                    "time:timestamp": start_timestamp,
                    "org:role": weapon_event["player"],
                    "primary_weapon": weapon_event.get("primary", ""),
                    "secondary_weapon": weapon_event["secondary"],
                    "other_equip": ", ".join(weapon_event["other_equip"]),
                    "org:resource": str(weapon_event["money_left"]),
                }
                events.append((start_timestamp, event_attrs))

            # Sort events by timestamp and append to trace
            events.sort(key=lambda x: x[0])  # Sort by timestamp
            for _, event_attrs in events:
                trace.append(create_event_element(event_attrs))
            
            bar()

    # Return the XML as a string
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")

# Load the JSON data
with open("rounds_data.json") as f:
    json_data = json.load(f)

# Convert JSON to XES format and pretty-print the XML DOM
xes_output = json_log_to_xes(json_data)
xmlstr = minidom.parseString(xes_output).toprettyxml(indent="   ")

# Save to XES file
with open("game_round_log.xes", "wb") as f:
    f.write(xmlstr.encode("utf-8"))