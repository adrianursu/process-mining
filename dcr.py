import pm4py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

if __name__ == "__main__":
    log = pm4py.read_xes('rounds_data.xes')
    graph, _ = pm4py.discover_dcr(log)
    pm4py.view_dcr(graph)