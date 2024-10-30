import pm4py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

log = pm4py.read_xes('../rounds_data.xes')
print(log)
graph, _ = pm4py.discover_dcr(log, post_process=["roles", "pending"], resource_key="org:role",group_key="org:role")
print("Found graph")
pm4py.view_dcr(graph)