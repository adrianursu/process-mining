import pm4py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

if __name__ == "__main__":
    log = pm4py.read_xes('rounds_data.xes')
    print(log)
    graph, _ = pm4py.discover_dcr(log,post_process=["roles"],resource_key="org:role",group_key="org:role")
    pm4py.view_dcr(graph)