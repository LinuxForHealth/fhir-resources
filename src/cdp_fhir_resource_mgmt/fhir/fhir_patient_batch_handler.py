from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.encounter import Encounter

from . import merge_resources
from . import fhir_utils


# DataContract with the service indicates that a complete bundle entry containing resource will be sent
# This methond simply transfers patient bundle entry into current bundle
def bundle_add_patient_entry(patbundle, patient_resource) :
    #missing patient resource entry is valid, and simply indicates that patient resource should not be updated
    if patient_resource is None :
        return
    entry = BundleEntry.parse_obj(patient_resource)
    patbundle.entry.append(entry)
    return

def get_location_id_for_encounter(enc_dict) :
    #encounter.location is not a mandatory field
    if not "location" in enc_dict:
        return None
    if len(enc_dict["location"]) <= 0:
        return None

    value: str
    #this logic is going to try and look through location array
    # preferrably we should find "active" location
    # otherwise, if status is not provided, the location is assigned "at random"
    # in this case the last location entry is used
    for loc_entry in enc_dict ["location"]:
        if "status" in loc_entry:
            if loc_entry["status"] == "active":
                value = loc_entry["location"]["reference"]
                break
        else:
            value = loc_entry["location"]["reference"]
    return value

def get_visit_id_for_encounter(enc_dict) :
    #identifier is also optional field
    if not "identifier" in enc_dict:
        return None
    if len(enc_dict["identifier"]) <= 0:
        return None

    value: str
    #see README for complexity of the Encounter.identifier
    #at this time there is no way to go through array of identifiers and extract visit number
    #this code assumes no other identifiers are present besides visit_number
    #if "type/system" is introduced for visit. it should be updated here to retrieve the id with more precision
    for visitid in enc_dict ["identifier"]:
        if "value" in visitid:
            value = visitid["value"]
            break

    return value

def get_start_date_for_encounter(enc_dict) :
    #visit date is also used as encounter unique identifier
    #visit date is optional. If present we will only take "start" date
    if not "period" in enc_dict:
        return None
    if not "start" in enc_dict["period"]:
        return None
    return enc_dict["period"]["start"]

# This function goes through each encounter found in the array of bundles
# The encounters are grouped by the unique logical ids (see README)
# The encounters that considered to be duplicates are merged
# For all merged encounters resource_map will keep track of "old":"new" encounter resource.id
# Map can be applied to all resource that reference encounter
def bundle_add_encounter_entries(patbundle, patient_array_of_bundles, patient_resource_id, resource_map) -> dict:
    encounters = dict()

    for b in patient_array_of_bundles:
        for entry in b["entry"]:
            if entry["resource"].get("resourceType") == "Encounter" :
                enc_dict= entry["resource"]

                visit_number_id = get_visit_id_for_encounter(enc_dict)
                # missing visit number = set visit number to current encounter id to mark it as unique
                # without visit we will be using resource.id
                # if no encounter have visit numbers they all will be considred unique
                if visit_number_id is None:
                    visit_number_id = enc_dict["id"]

                start_date =   get_start_date_for_encounter(enc_dict)
                visit_number_id = visit_number_id + "^"
                if not start_date is None:
                    visit_number_id = visit_number_id + start_date

                location = get_location_id_for_encounter(enc_dict)
                visit_number_id = visit_number_id + "^"
                if not location is None:
                    visit_number_id = visit_number_id + "^" + location

                if visit_number_id not in encounters:
                    encounters[visit_number_id] = []
                encounters[visit_number_id].append (entry["resource"])

    for singleEncounter in encounters.values():
        if len(singleEncounter) > 1 : #duplicates
            enc = merge_resources.deduplicate_list(resource_map, singleEncounter, "Encounter")
        else : #no duplicate encounters
            enc = singleEncounter[0]
            resource_map["Encounter/" + enc["id"]] = "Encounter/" + enc["id"]
        fhir_encounter = Encounter.parse_obj(enc)
        fhir_encounter.subject =  fhir_utils.get_patient_reference(patient_resource_id)
        patbundle.entry.append(fhir_utils.get_new_bundle_entry_put_resource(fhir_encounter))

    return resource_map

# This function simply moves resources out of bundle array into a target patient bundle (patbundle)
# Patient ids are being rehashed as resources are moved
# Exclusion list is used to specify resources that should be ignored
# Currently resource map is mapping resource.id to its own resource.id
# However, if in the future resource ids will be changing, the map will help to keep changes recorded
def move_resources_to_bundle(patbundle, patient_array_of_bundles,
                             patient_resource_id, resource_map, resource_exclusion_list) -> dict:
    patient_reference=fhir_utils.get_patient_reference(patient_resource_id)
    for pb in patient_array_of_bundles:
        for entry in pb["entry"]:
            entry_resource=entry["resource"]
            if entry_resource.get("resourceType") in resource_exclusion_list:
                #This entry is excluded from being added to the patient bundle
                continue


            #is_patient_resource=False
            if "patient" in entry_resource and "reference" in entry_resource["patient"]:
                entry["resource"]["patient"] = patient_reference
               # is_patient_resource=True
            if "subject" in entry_resource and "reference" in entry_resource["subject"]:
                if entry_resource["subject"]["reference"].startswith("Patient"):
                    entry_resource["subject"] = patient_reference
                 #   is_patient_resource=True

           # if is_patient_resource :
            resource_ref =fhir_utils.get_resource_reference(entry_resource)
            resource_map[resource_ref.reference] = resource_ref.reference

            patbundle.entry.append(fhir_utils.get_new_bundle_entry_put_dict_resource("PUT", entry_resource))
    return resource_map


def create_fhir_bundle (patient_resource_id, primary_patient_resource_entry, patient_array_of_bundles) -> Bundle :
    patbundle = fhir_utils.get_new_bundle()
    #add patient to a bundle if present
    bundle_add_patient_entry(patbundle, primary_patient_resource_entry)

    #make sure we have resources
    if patient_array_of_bundles is None:
        return patbundle
    if len(patient_array_of_bundles) == 0:
        return patbundle

    #resource map will be accumulating changes in references
    #as a last step the bundle is traversed to re-id all of the resources
    resource_map ={}
    bundle_add_encounter_entries(patbundle, patient_array_of_bundles, patient_resource_id,resource_map)

    #this is the list of resources that we don't want to include in our bundle
    #Patient - already included as a master patient and should not be pulled from bundles
    #Encounter - already pulled and deduplicated
    #MessageHeader - information about the bundle conversion will not be persisted
    #TODO: is it worth to have it in configurations where list of exclusions/inclusions can be adjusted
    resource_exclusion_list = ["Patient", "Encounter", "MessageHeader", "Organization"]
    resource_map = move_resources_to_bundle\
        (patbundle, patient_array_of_bundles, patient_resource_id, resource_map, resource_exclusion_list)

    # the ids of the objects might have changed, their mapping has been accumulated in resource_map
    # next we need to go through entire bundle and apply the changes
    fhir_utils.apply_reference_map_to_bundle(patbundle, resource_map)
    return patbundle
