from deepmerge import Merger

# Assumes that list is sorted
def deduplicate_list(id_merge_map, resource_list, resource_type_name):
    if len(resource_list) <= 1:
        id_merge_map[resource_type_name + "/" + resource_list[0]["id"]]\
            = resource_type_name + "/" + resource_list[0]["id"]
        return resource_list[0]
    rsrc = resource_list[0]

    mm = Merger(
            [(dict,["merge"])], ["override"], ["override"])

    id_list=[resource_type_name + "/"+ rsrc["id"]]
    for i in range(len(resource_list) - 1):
        id_list.append(resource_type_name + "/" + resource_list[i + 1]["id"])
        rsrc = mm.merge(rsrc, resource_list[i + 1] )

    id_merge_map.update(id_merge_map.fromkeys(id_list, resource_type_name + "/" + rsrc["id"]))
    return rsrc
