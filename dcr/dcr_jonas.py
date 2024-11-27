import pm4py
import warnings
import os
import pandas as pd
from copy import deepcopy
from pm4py.objects.dcr.exporter import exporter as dcr_exporter

warnings.filterwarnings("ignore", category=DeprecationWarning)
pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.width', None)  # Prevent line wrapping
pd.set_option('display.max_colwidth', None)  # Show full column content (if


def load_all_logs(path):
    log = pd.DataFrame([])
    case_id = 0
    current_case_id = case_id
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        temp_log = pm4py.read_xes(file_path)
        case_id += 1
        for i, row in temp_log.iterrows():
            if row["case:concept:name"] != current_case_id:
                current_case_id = row["case:concept:name"]
                case_id += 1

            temp_log.loc[i, "case:concept:name"] = case_id
        log = pd.concat([log, temp_log], ignore_index=True)

    log.reset_index()

    file_path = path + "/collected.xes"
    pm4py.write_xes(log, file_path)


def check_path_player_transform(log, site, specific_player, ct_win):
    new_log = deepcopy(log)
    new_log.drop(new_log.index, inplace=True)
    traceId = 1
    new_log = pd.DataFrame([])

    rounds = log["case:concept:name"].unique()
    for round in rounds:
        temp = log[log["case:concept:name"] == round]
        bomb_plant = pd.DataFrame(
            log[(log["concept:name"] == "Bomb-plant") & (log["bomb_place"] == "Bombsite" + site)].head(1).reset_index(
                drop=True))
        if not bomb_plant.empty:
            time = bomb_plant["time:timestamp"].iloc[0]
            players = temp["org:role"].unique()
            for player in players:
                if "ZywOo [CT]" in player and specific_player and ct_win:
                    move = temp[(temp["org:role"] == player)
                                & (temp["case:winner"] == "CT")
                                & (temp["time:timestamp"] >= time)
                                & (temp["concept:name"].str.contains("Move to")
                                   | (temp["concept:name"] == "Bomb-defuse"))]
                    move["case:concept:name"] = str(traceId)
                    bomb_plant["case:concept:name"] = str(traceId)
                    new_log = pd.concat([new_log, bomb_plant, move], ignore_index=True)
                    traceId += 1
                elif player.endswith("[CT]") and specific_player == False and ct_win == False:
                    move = temp[(temp["org:role"] == player)
                                & (temp["time:timestamp"] >= time)
                                & (temp["concept:name"].str.contains("Move to")
                                   | (temp["concept:name"].str.contains("Move to"))
                                   | (temp["concept:name"] == "Bomb-defuse"))]
                    move["case:concept:name"] = str(traceId)
                    bomb_plant["case:concept:name"] = str(traceId)
                    new_log = pd.concat([new_log, bomb_plant, move], ignore_index=True)
                    traceId += 1

    new_log = new_log.reset_index()

    if not os.path.exists("vitality.xes"):
        pm4py.write_xes(new_log, "vitality.xes")
    elif not os.path.exists("mirage.xes"):
        pm4py.write_xes(new_log, "mirage.xes")
    elif not os.path.exists("conformance.xes"):
        pm4py.write_xes(new_log, "conformance.xes")
    return new_log


def check_path_player(log, site, start, success):
    new_log = check_path_player_transform(log, site, start, success)
    post_process = []
    # post_process = ["roles",pending]
    graph, _ = pm4py.discover_dcr(new_log, post_process=post_process, resource_key="org:role", group_key="org:role")
    graph.marking.pending.add("Bomb-plant")
    pm4py.view_dcr(graph)
    return graph


def check_bombing_path(log):
    log = log[(log["concept:name"] != "Inventory Check")
              & (~log["concept:name"].str.contains("Throw"))
              & (log["concept:name"] != "Kill [CT]")]

    killer_place = log[(log["concept:name"] == "Kill  [T]") & (log["killer_place"] == "BombsiteA")]

    log = log[log["org:role"].str.contains("[T]")]
    players = log[(log["org:role"].str.endswith("[T]")) & (log["concept:name"] == "Bomb-plant")]["org:role"].unique()
    case_id = 0

    new_log = pd.DataFrame([])
    for index, row in killer_place.iterrows():
        temp_row = log[
            (log["concept:name"] == row["concept:name"]) & (log["case:concept:name"] == row["case:concept:name"])]

        for player in players:
            temp = log[(log["time:timestamp"] > row["time:timestamp"])
                       & (log["case:concept:name"] == row["case:concept:name"])
                       & (log["org:role"] == player)]
            if (temp == "Bomb-plant").any().any():
                new_log = pd.concat([new_log, temp_row, temp], ignore_index=True)
                case_id += 1

    log = new_log

    bomb_plant = log[(log["concept:name"] == "Bomb-plant")]

    new_log = pd.DataFrame([])
    for index, row in bomb_plant.iterrows():
        temp = log[(log["time:timestamp"] <= row["time:timestamp"])
                   & (log["case:concept:name"] == row["case:concept:name"])]
        new_log = pd.concat([new_log, temp], ignore_index=True)

    for index, row in new_log.iterrows():
        new_log.loc[index, "org:role"] = row["org:role"].split(" ")[-1]
        new_log = new_log.reset_index()
    graph, _ = pm4py.discover_dcr(new_log, post_process=["pending", "roles"], resource_key="org:role",
                                  group_key="org:role")
    pm4py.view_dcr(graph)


def check_T_movement(log, site):
    rounds = log["case:concept:name"].unique()
    temp_log = log.copy()
    temp_log.drop(temp_log.index, inplace=True)
    for round in rounds:
        round_trace: pd.DataFrame = log[
            (log["case:concept:name"] == round) & (log["concept:name"] != "Inventory Check")]
        players = round_trace[round_trace["org:role"].str.endswith("[T]")]["org:role"].unique()

        # if ZyWoo is in the players as terrorist skip
        if "ZywOo [T]" in players:
            continue
        CT_player = round_trace[round_trace["org:role"].str.endswith("[CT]")]["org:role"].unique()
        moves = ["Move to CTSpawn", "Move to Shop", "Move to BombsiteB", "Throw-Molotov"]
        time = None
        allow_reaction = False
        for player in CT_player:
            correct_player_path_found = False
            move = 0
            actions = round_trace[round_trace["org:role"] == player]
            for index, row in actions.iterrows():
                if move == len(moves):
                    correct_player_path_found = True
                    allow_reaction = True
                    break
                if row["concept:name"] == moves[move]:
                    time = row["time:timestamp"]
                else:
                    break
                move += 1
            if correct_player_path_found:
                player_actions = round_trace[(round_trace["org:role"] == player)
                                             & (round_trace["time:timestamp"] <= time)]

                temp_log = pd.concat([temp_log, player_actions])

                if allow_reaction:
                    T_player = round_trace[(round_trace["org:role"].str.endswith("[T]"))
                                           & (round_trace["player_place"].isin(site))
                                           & (round_trace["concept:name"].str.contains("Move to"))
                                           & (round_trace["time:timestamp"] > time)
                                           & (round_trace["time:timestamp"] <= (time + pd.Timedelta(seconds=2)))
                                           & (round_trace["concept:name"] != "Move to PalaceAlley")]
                    temp_log = pd.concat([temp_log, T_player])

    for index, row in temp_log.iterrows():
        temp_log.loc[index, "org:role"] = temp_log.loc[index, "org:role"].split(" ")[-1]

    return temp_log.reset_index()


def check_grenade(log, site, winner):
    rounds = log["case:concept:name"].unique()
    actions = deepcopy(log)
    actions.drop(actions.index, inplace=True)
    for round in rounds:
        temp = log[log["case:concept:name"] == round]
        players = temp[temp["org:role"].str.endswith("[T]")]["org:role"].unique()

        # if ZyWoo is in the players as terrorist skip
        if "ZywOo [T]" in players:
            continue
        TgrenadeTime = temp[(temp["player_place"].isin(site))
                            & (temp["concept:name"].str.contains("Throw-"))
                            & (temp["org:role"].str.endswith("[T]"))].reset_index()

        round_actions = deepcopy(log)
        round_actions.drop(round_actions.index, inplace=True)
        if not TgrenadeTime.empty:
            time = TgrenadeTime.head(1).iloc[0]["time:timestamp"]
            if winner:
                move = temp[(temp["player_place"].isin(site))
                            & (temp["concept:name"].str.contains("Move to"))
                            & (temp["time:timestamp"] > time)
                            & (temp["case:winner"] == "CT")].reset_index()
            else:
                move = temp[(temp["player_place"].isin(site))
                            & (temp["concept:name"].str.contains("Move to"))
                            & (temp["time:timestamp"] > time)].reset_index()

            index_to_drop = []
            for index, row in move.iterrows():
                if move.loc[index, "org:role"].split(" ")[-1] != "[CT]":
                    move.loc[index, "concept:name"] = "[" + move.loc[index, "org:role"].split("[")[-1] + " " + move.loc[
                        index, "concept:name"]
                else:
                    index_to_drop.append(index)

            for index in index_to_drop:
                move = move.drop(index=index)

            move.reset_index()
            CTgrenadeTime = temp[(temp["player_place"].isin(site))
                                 & (temp["concept:name"].str.contains("Throw-"))
                                 & (temp["org:role"].str.endswith("[CT]"))].reset_index()

            round_actions = pd.concat([round_actions, CTgrenadeTime, move], ignore_index=True).sort_values(
                by='time:timestamp')
            actions = pd.concat([actions, round_actions], ignore_index=True)

    for index, row in actions.iterrows():
        actions.loc[index, "org:role"] = actions.loc[index, "org:role"].split(" ")[-1]

    actions.reset_index()
    return actions

if __name__ == "__main__":
    # note for this, we looked at Vitality,
    # so the code will work on other logs,
    # but it will not provide the consistency of a given teams grenade reaction for given teams
    map = "mirage"
    outputPath = 'dcr.png'
    option = 2
    if option == 0:
        load_all_logs("xes-files/" + map + "Team/xes")

    elif option == 1:
        B = {"BackAlley", "Apartments", "SideAlley", "Middle", "stairs", "House", "TopofMid", "TSpawn"}
        log = pm4py.read_xes("xes-files/" + map + "Team/xes/game1.xes")
        log["time:timestamp"] = pd.to_datetime(log["time:timestamp"])
        log = check_T_movement(log, B)
        graph, _ = pm4py.discover_dcr(log, post_process=["pending", "roles"], resource_key="org:role",
                                      group_key="org:role")
        pm4py.save_vis_dcr(graph, outputPath)

    elif option == 2:
        B = {"BackAlley", "Apartments", "BombsiteB", "Shop", "Truck", "Catwalk"}
        log = pm4py.read_xes("xes-files/" + map + "Team/xes/collected.xes")
        log["time:timestamp"] = pd.to_datetime(log["time:timestamp"])
        log = check_grenade(log, B, True)
        graph, _ = pm4py.discover_dcr(log, post_process=["roles", "pending"], resource_key="org:role",
                                      group_key="org:role")
        pm4py.save_vis_dcr(graph, outputPath)