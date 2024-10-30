import pm4py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

log = ["ct_elim.xes", "t_elim.xes", "def.xes", "expl.xes", "time_out.xes"]

for l in log:
    pm = pm4py.read_xes(l)
    graph, _ = pm4py.discover_dcr(pm, post_process=["roles", "pending"], resource_key="org:role",group_key="org:role")
    pm4py.view_dcr(graph)