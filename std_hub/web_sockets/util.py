




def websocket_client_switch(client_id):
    _id,client = client_id.split("__")

    if client=="agent":
        return _id+"__client"
    elif client=="client":
        return _id+"__agent"
