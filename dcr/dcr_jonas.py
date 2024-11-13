import pm4py
import warnings
import os
import pandas as pd
import numpy as np
import ast
from pm4py.objects.dcr.exporter import exporter as dcr_exporter
from pm4py.objects.dcr.importer import importer as dcr_importer

warnings.filterwarnings("ignore", category=DeprecationWarning) 


def load_all_logs(path):
    log = pd.DataFrame([])
    case_id = 0
    current_case_id = case_id
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        temp_log = pm4py.read_xes(file_path)
        case_id += 1
        for i,row in temp_log.iterrows():
            if row["case:concept:name"] != current_case_id:
                current_case_id = row["case:concept:name"]
                case_id += 1
            temp_log.loc[i,"case:concept:name"] = case_id
        log = pd.concat([log,temp_log],ignore_index=True)

    log.reset_index()

    file_path = path+"/collected.xes"
    pm4py.write_xes(log,file_path)


def check_buying_amount(log,amount):
    log = log[log["concept:name"] == "Inventory Check"]
    
    log = log[log["org:resource"] >= str(1000)]   
    new_log = {"concept:name":[], "org:role":[],"time:timestamp":[],"case:concept:name":[]}

    for key,i in log.iterrows():
        weapons = i["primary_weapon"].split(",")
        weapons.extend(i["secondary_weapon"].split(","))
#        weapons.extend(i["other_equip"].split(","))
        for j in weapons:
            if j == '':
                continue

            new_log["concept:name"].append("buy "+j)
            new_log["org:role"].append(i["org:role"].split(" ")[-1])
            new_log["time:timestamp"].append(i["time:timestamp"])
            new_log["case:concept:name"].append(str(key))
    
    
    new_log = pd.DataFrame(new_log)


    graph, _ = pm4py.discover_dcr(new_log,post_process=["pending","nesting","roles"],resource_key="org:role",group_key="org:role")

    path = 'dcr-graphs/amount1.xml'
    pm4py.write_dcr_xml(graph, path, variant=dcr_exporter.XML_SIMPLE, dcr_title='dcrgraph', replace_whitespace=' ')


def check_path_player(log):
    log = log[(log["concept:name"] != "Inventory Check")
                  & (~log["concept:name"].str.contains("Throw"))
                  & (log["concept:name"] != "Kill  [T]")]

    bomb_plants = log[(log["concept:name"]=="Bomb-plant") & (log["bomb_place"]=="BombsiteB") ]
    players = log[log["org:role"].str.endswith("[CT]")]["org:role"].unique()
    case_id = 0
    new_log = pd.DataFrame([])
    for index, row in bomb_plants.iterrows():
        temp_row = log[(log["concept:name"] == row["concept:name"]) & (log["case:concept:name"] == row["case:concept:name"])]
        for player in players:

            temp = log[(log["time:timestamp"]>row["time:timestamp"])
                       &(log["case:concept:name"]==row["case:concept:name"])
                       &(log["org:role"] == player)]
            temp["case:concept:name"] = temp["case:concept:name"].apply(lambda x: case_id)
            temp_row["case:concept:name"] = temp_row["case:concept:name"].apply(lambda x: case_id)
            new_log = pd.concat([new_log,temp_row,temp],ignore_index=True)
            case_id += 1

    log = new_log

    bomb_defused = log[(log["concept:name"]=="Bomb-defuse")]

    new_log = pd.DataFrame([])
    for index, row in bomb_defused.iterrows():
        temp = log[(log["time:timestamp"]<=row["time:timestamp"])
                   &(log["case:concept:name"]==row["case:concept:name"])]

        new_log = pd.concat([new_log,temp],ignore_index=True)

    for index, row in new_log.iterrows():
        new_log.loc[index,"org:role"] = row["org:role"].split(" ")[-1]
    
    new_log = new_log.reset_index()
    graph, _ = pm4py.discover_dcr(new_log,post_process=["pending","roles"],resource_key="org:role",group_key="org:role")
    
    pm4py.view_dcr(graph)
    
    path = 'dcr-graphs/plantResponse2.xml'
    #pm4py.save_vis_dcr(graph,file_path=path)
    #pm4py.write_dcr_xml(graph, path, variant=dcr_exporter.XML_SIMPLE, dcr_title='dcrgraph', replace_whitespace=' ')
    #print(log["case:concept:name"].unique())


def check_bombing_path(log):
    #log = log[log["case:end_reason"] == "BombExploded"]
    
    log = log[(log["concept:name"] != "Inventory Check")
                  & (~log["concept:name"].str.contains("Throw"))
                  & (log["concept:name"] != "Kill [CT]")]

    killer_place = log[(log["concept:name"]=="Kill  [T]") & (log["killer_place"]=="BombsiteA")]
    pd.set_option('display.max_rows', None)  # Show all rows
    pd.set_option('display.max_columns', None)  # Show all columns
    pd.set_option('display.width', None)  # Prevent line wrapping
    pd.set_option('display.max_colwidth', None)  # Show full column content (if applicable)

    log = log[log["org:role"].str.contains("[T]")]
    players = log[(log["org:role"].str.endswith("[T]"))&(log["concept:name"]=="Bomb-plant")]["org:role"].unique()
    case_id = 0

    new_log = pd.DataFrame([])
    for index, row in killer_place.iterrows():
        temp_row = log[(log["concept:name"] == row["concept:name"]) & (log["case:concept:name"] == row["case:concept:name"])]
        
        for player in players:
            temp = log[(log["time:timestamp"]>row["time:timestamp"])
                       &(log["case:concept:name"]==row["case:concept:name"])
                       &(log["org:role"] == player)]
            if (temp == "Bomb-plant").any().any():
                print(temp_row[["case:concept:name","concept:name","time:timestamp"]])
                print(temp[["case:concept:name","concept:name","time:timestamp"]])
                new_log = pd.concat([new_log,temp_row,temp],ignore_index=True)
                case_id += 1


    log = new_log

    bomb_plant = log[(log["concept:name"]=="Bomb-plant")]

    new_log = pd.DataFrame([])
    for index, row in bomb_plant.iterrows():
        temp = log[(log["time:timestamp"]<=row["time:timestamp"])
                   &(log["case:concept:name"]==row["case:concept:name"])]
        new_log = pd.concat([new_log,temp],ignore_index=True)

    for index, row in new_log.iterrows():
        new_log.loc[index,"org:role"] = row["org:role"].split(" ")[-1]
    
    pd.set_option('display.max_rows', None)  # Show all rows
    pd.set_option('display.max_columns', None)  # Show all columns
    pd.set_option('display.width', None)  # Prevent line wrapping
    pd.set_option('display.max_colwidth', None)  # Show full column content (if applicable)
    print(new_log[["case:concept:name","concept:name","org:role","victim"]])

    new_log = new_log.reset_index()
    graph, _ = pm4py.discover_dcr(new_log,post_process=["pending","roles"],resource_key="org:role",group_key="org:role")
    pm4py.view_dcr(graph)
    #path = 'dcr-graphs/path.xml'
    #pm4py.write_dcr_xml(graph, path, variant=dcr_exporter.DCR_JS_PORTAL, dcr_title='dcrgraph', replace_whitespace=' ')

def check_molotov_response(log):

    molotov_events = log[(log["concept:name"] == "Throw-Molotov") & (log["player_place"] == "BackAlley")]

    new_log = pd.DataFrame([])
    for index, row in molotov_events.iterrows():
        temp_row = log[(log["concept:name"] == row["concept:name"]) & (log["case:concept:name"] == row["case:concept:name"])]
        temp = log[(log["time:timestamp"]>row["time:timestamp"])
                   &(log["time:timestamp"]<row["time:timestamp"] + pd.Timedelta(seconds=2))
                   &(log["case:concept:name"]==row["case:concept:name"])]
        print(row["time:timestamp"])
        print(temp["time:timestamp"])
        new_log = pd.concat([new_log,temp_row,temp],ignore_index=True)

    for index, row in new_log.iterrows():
        new_log.loc[index,"org:role"] = row["org:role"].split(" ")[-1]


    graph, _ = pm4py.discover_dcr(new_log,post_process=["pending","roles"],resource_key="org:role",group_key="org:role")
    pm4py.view_dcr(graph)


if __name__ == "__main__":
    map = "mirage"

    #load_all_logs("xes-files/"+map)



    log = pm4py.read_xes("xes-files/"+map+"/collected.xes")
    #check_path_player(log)
    check_bombing_path(log)
    #check_molotov_response(log)
    #check_buying_amount(log,1000)
    #check_buying_team(log,"[T]")
    #check_killing_events(log, "weapon")

    