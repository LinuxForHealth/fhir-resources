from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.bundle import BundleEntryRequest
from fhir.resources.encounter import Encounter
from fhir.resources.resource import Resource
from fhir.resources.reference import Reference

import fhir


def get_new_bundle() -> Bundle:
    b = Bundle.construct()
    #TODO: determine if Bundle Type should be configurable
    b.type = "transaction"
    b.entry= []
    return b

def get_new_bundle_entry(request_method_code, request_url, fhir_resource, full_url) -> BundleEntry:
    entry = BundleEntry.construct()
    entry.resource = fhir_resource
    entry.fullUrl = full_url
    #note there is a bug in fhir.resources the validation
    #both fields are required fields, when setting one field the second field is not set and throws validation error
    #as a work around BundleEntryRequest has to be created as json object first
    request_json = {
        "method": request_method_code,
        "url": request_url
    }
    entry.request = BundleEntryRequest.parse_obj(request_json)

    return entry

def get_new_bundle_entry_put_resource(fhir_resource : Resource) -> BundleEntry:
    return get_new_bundle_entry("PUT", fhir_resource.resource_type + "/" + fhir_resource.id,fhir_resource, "urn:id:" + fhir_resource.id)



def get_new_bundle_entry_put_dict_resource(request_method_code,dict_resource : dict) -> BundleEntry:
    bundle_entry_json ={
    "fullUrl" : "urn:id:" + dict_resource["id"],
    "request": { "method":request_method_code, "url":dict_resource["resourceType"] +"/" +dict_resource["id"] },
    "resource": dict_resource
    }
    return BundleEntry.parse_obj(bundle_entry_json)


def get_patient_reference(patient_resource_id) -> Reference:
    patRef : Reference
    patRef =Reference.construct()
    patRef.reference="Patient/" + patient_resource_id
    return patRef

def get_resource_reference(rsc) -> Reference:
    rref : Reference
    rref =Reference.construct()
    rref.reference=rsc["resourceType"] + "/"+ rsc["id"]
    return rref


# resource_map sample {"Encounter/123":"Encounter/123", "Encounter/ABC" : "Encounter/123, "Observation/1" : "Observation/2"}
# The resource map keeps track of the changes to resource.id that occurred through processing
# Applying resource map to FHIR object includes recursively examine each field in the object looking for references
# if reference exists as key in resource_map, that reference is replaced with the value associated with that key in the resource_map
def apply_resource_map_to_references(rsrc, resource_map) :
    #recursive function - end - found fhir.resource.reference.Reference object
    #apply resource map and return
    if (type(rsrc) == fhir.resources.reference.Reference):
        if rsrc.reference in resource_map:
            replaceValue = resource_map[rsrc.reference]
            if replaceValue is not None:
                rsrc.reference = replaceValue
        return
    # recursive function - end - primitive attribute
    if not hasattr(rsrc, "__dict__"):
        return

    for k, v in vars(rsrc).items():
        #lists and dictionaries will call this function again on its content
        if (type(v) == list):
            for item in v:
                apply_resource_map_to_references(item, resource_map)
        if (type(v) == dict):
            for item in v:
                apply_resource_map_to_references(item, resource_map)

        #Reference object - apply map
        if (type(v) == fhir.resources.reference.Reference) :
           if v.reference in resource_map:
                replaceValue = resource_map[v.reference]
                if replaceValue is not None:
                    v.reference=replaceValue

    return

# Method to traverse thru each BundleEntry in the bundle
# Calls apply_resource_map_to_references to apply resource map
def apply_reference_map_to_bundle(patbundle, resource_map):
    for item in patbundle.entry:
        apply_resource_map_to_references(item.resource, resource_map)
    return
