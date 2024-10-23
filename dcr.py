import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes('rounds_data.xes')
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(log)
    pm4py.view_petri_net(net, initial_marking, final_marking, format="svg")