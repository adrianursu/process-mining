import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes('rounds_data.xes')
    dcr, initial_marking = pm4py.discover_dcr(log)
    pm4py.view_dcr(dcr)