import copy

from std_hub.dnd.utils import get_function_metadata, list_to_edge_list
from typing import List, Union

class Dnd:
    def __init__(self,method_list:List[callable]=None,connections:Union[list,bool]=True):
        self.method_list:List[callable]  =method_list  
        self.connections:Union[list,bool]=connections
    def get_flow_schema(self,method_list:List[callable]=None,connections:Union[list,bool]=None):
        func_list = []
        func_names=[]
        final={}
        func_dict={}
        
        
        method_list = method_list or self.method_list
        connections = connections or self.connections
        
        for func in method_list:
            func_data = get_function_metadata(func=func)
            func_list.append(func_data)
            func_names.append(func_data["name"])
            func_dict[func_data["name"]]=func
        
        

                
        final["nodes"] = func_list
        final["funcs"] = func_dict
        final["connections"]=[]
        
        if isinstance(connections,bool):
            if connections:
                connections = list_to_edge_list(nodes=func_names)
            
        if connections:
            for gnode in connections:
                final["connections"].append({
                    "from":gnode[0],
                    "to":gnode[1],
                })
                
        return final

    def flow_graph_kickoff(self,flow_graph:dict,state:dict,default_flow_graph:dict={}):

        connections = copy.deepcopy(flow_graph["connections"])
        start_con = connections.pop(0)
        
    
        while start_con:
            ncon= next_con(start_con=start_con,connections=connections,flow_graph=flow_graph,state=state,default_flow_graph=default_flow_graph)
            if ncon:
            
                start_con,connections=ncon
            else : break

        return state
            
            



def next_con(start_con:dict=None,connections:list=None,flow_graph:dict=None,state:dict=None,default_flow_graph:dict={}):
    start_name:str=None,
    if start_con:
        start_name=start_con["from"]
        
    if start_name=="eof":
        
        return  None
    current_func = flow_graph["funcs"].get(start_name,None) or default_flow_graph.get("funcs",{}).get(start_name,None)
    if not current_func:
        raise Exception(f"no function : {start_name} avilable")
    func_data = get_function_metadata(func=current_func)
    input_list = list(func_data["inputs"].keys())
    kwargs = {}
    for node in flow_graph["nodes"]:
        if node["name"] == func_data["name"]:
            edited_func_data = node
    for inps in input_list:
        func_in = edited_func_data["inputs"].get(inps,None)
        state_in = state.get(inps,None)
        if state_in :
            kwargs[inps]=state_in
        if isinstance(func_in,str) :
            if func_in!="<class 'str'>":
                kwargs[inps]=func_in

        
    res = current_func(**kwargs)
    state[start_name+"_ouput"]=res
    next_func= None
    if isinstance(res,dict):
        next_func = res.get("next_function",None)
    if not next_func:
        next_func =start_con["to"]
        
    res_cons = None
    for con in connections:
        if con["from"] == next_func:
            connections.remove(con)
            res_cons =  con,connections
    if not res_cons :
        if start_con["to"]== next_func:
            res_cons =  {"from":next_func,"to":"eof"},connections
            state["eof"+"_ouput"]=res
            

    return res_cons