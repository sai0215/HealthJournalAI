import inspect

def get_function_metadata(func):
    # Get the function's name
    function_name = func.__name__
    
    # Get the module where the function is defined
    module_path = func.__module__
    
    # Get the function's docstring (description)
    docstring = inspect.getdoc(func)
    
    # Get the function's signature and parameters with type hints
    signature = inspect.signature(func)
    inputs = {}
    for param in signature.parameters.values():
        inputs[param.name] = str(param.annotation) if param.annotation != inspect.Parameter.empty else 'No type hint'
    
    # Try to get the output (return type) using type hint
    output = str(signature.return_annotation) if signature.return_annotation != inspect.Signature.empty else 'No return type hint'
    
    # Construct the resulting dictionary
    function_metadata = {
        "name": function_name,
        "module_path": module_path,
        "description": docstring,
        "inputs": inputs,
        "output": output
    }
    
    return function_metadata

def list_to_edge_list(nodes):
    """
    Converts a list of nodes into an edge list representation of a graph.
    
    Parameters:
    nodes (list): A list of nodes (e.g., ['a', 'b', 'c', 'd']).

    Returns:
    list: A list of edges, where each edge is a pair of consecutive nodes (e.g., [['a', 'b'], ['b', 'c'], ['c', 'd']]).
    """
    # Initialize an empty list to store the edges
    edges = []
    
    # Iterate through the list of nodes up to the second-to-last element
    for i in range(len(nodes) - 1):
        # Create an edge between consecutive nodes
        edge = [nodes[i], nodes[i + 1]]
        edges.append(edge)
    
    return edges