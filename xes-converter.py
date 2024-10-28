import json
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import xml.dom.minidom
from datetime import date, datetime, time, timedelta, timezone

# Load JSON file
with open("rounds_data.json") as f:
    rounds_data = json.load(f)

# Helper function to create XES elements
def create_trace(round_number, events):
    trace = Element("trace")
    trace_round = SubElement(trace, "string", key="concept:name", value=str(round_number))

    for event in events:
        event_elem = SubElement(trace, "event")
        SubElement(event_elem, "string", key="concept:name", value=event["type"])
        SubElement(event_elem, "string", key="org:role", value=event["player"])
        minutes,secs = event["time"].split(":")
        dt = datetime.combine(date.today(), time(hour=0,minute=int(minutes), second=int(secs),tzinfo=datetime.now().astimezone().tzinfo))
        dt = dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        SubElement(event_elem, "date", key="time:timestamp", value=dt)
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
            events.append({
                "type": "kill",
                "time": kill["time"],
                "player": kill["killer"],
                "victim": kill["victim"],
                "weapon": kill["weapon"],
                "headshot": kill["headshot"]
            })

    # Process bomb events
    if "bomb_events" in round_info and round_info["bomb_events"]:
        for bomb in round_info["bomb_events"]:
            events.append({
                "type": f"bomb_{bomb['action']}",
                "time": bomb["time"],
                "player": bomb["player"]
            })

    # Add trace to log
    trace = create_trace(round_number, events)
    xes_log.append(trace)

# Save XES log to file
dom = xml.dom.minidom.parseString(tostring(xes_log))
pretty_xml_as_string = dom.toprettyxml()

with open("rounds_data.xes", "w") as xes_file:
    xes_file.write(pretty_xml_as_string)

print("Conversion to XES completed. Saved as 'rounds_data.xes'.")