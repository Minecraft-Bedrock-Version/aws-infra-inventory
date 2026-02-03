def compare_with_existing(service, identifier, existing_nodes):
    if not identifier:
        return None
        
    for node in existing_nodes:
        if node['service'] == service and node['identifier'] == identifier:
            return node
    return None