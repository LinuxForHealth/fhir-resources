import unittest
import os
import unittest
import json
from cdp_fhir_resource_mgmt.fhir import fhir_patient_batch_handler, fhir_utils,merge_resources
from deepdiff import DeepDiff

from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.encounter import Encounter


class TestFhirResourceManagement(unittest.TestCase):

    def test_get_new_bundle_entry(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close
        # entry = get_new_bundle_entry("PUT", "Patient/123", )
        patientResource = patbatch_entry["primaryPatientResourceEntry"]["resource"]
        result = fhir_utils.get_new_bundle_entry("PUT", "Patient/pat12345", Patient.parse_obj(patientResource),
                                                     "urn:id:pat12345")
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only_output_bundle_entry.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        BundleEntry.parse_obj(output)
        f.close
        self.assertEqual(DeepDiff(BundleEntry.parse_obj(output), result), {})

    def test_get_new_bundle_entry_put_dict_resource(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close

        result = fhir_utils.get_new_bundle_entry_put_dict_resource("PUT",
                                                                   patbatch_entry["primaryPatientResourceEntry"][
                                                                       "resource"])

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only_output_bundle_entry.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        BundleEntry.parse_obj(output)
        f.close
        self.assertEqual(DeepDiff(BundleEntry.parse_obj(output), result), {})

    def test_get_patient_reference(self):
        r = fhir_utils.get_patient_reference("ABC-123")
        self.assertEqual('{"reference": "Patient/ABC-123"}', r.json())

    def test_no_primary_resource_patient(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "no_primary_pat_resource.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close

        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "no_primary_pat_resource_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

    def test_patient_only_empty_batch(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close
        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only_bundle_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})


    def test_patient_only_nullbatch(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only.json")

        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close
        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"], patbatch_entry["patientBatch"])
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "patient_only_bundle_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

    def test_encounters_only(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounters_only.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close
        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounters_only_bundle_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

    def test_encounter_2_merge(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounter_list_2.json")
        f = open(resourcesFile)
        encounters = json.loads(f.read())
        f.close
        id_map = {}
        result = merge_resources.deduplicate_list(id_map, encounters, "Encounter")
        outputmap = {"Encounter/encounter2": "Encounter/encounter3", "Encounter/encounter3": "Encounter/encounter3"}
        self.assertEqual(DeepDiff(outputmap, id_map),  {})

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounter_2_deduplicate_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(output, result), {})


    def test_encounter_3_merge(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounter_list_3.json")
        f = open(resourcesFile)
        encounters = json.loads(f.read())
        f.close

        id_map = {"Encounter/encounterABC": "Encounter/encounterABC", "Encounter/encounterDEF": "Encounter/encounterDEF"}
        result = merge_resources.deduplicate_list(id_map, encounters, "Encounter")


        outputmap = {"Encounter/encounterABC": "Encounter/encounterABC", "Encounter/encounterDEF": "Encounter/encounterDEF", "Encounter/encounter2": "Encounter/encounter4",
         "Encounter/encounter3": "Encounter/encounter4", "Encounter/encounter4": "Encounter/encounter4"}
        self.assertEqual(DeepDiff(outputmap, id_map), {})

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounter_3_deduplicate_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(output, result), {})

    def test_encounter_id_null_values_merge(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounters_null_id.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close

        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "encounters_null_id_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

    def test_adt_A01(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "adtA01.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close
        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "adtA01_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

    def test_resource_mapping(self):
        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "resource_map_test_file.json")
        f = open(resourcesFile)
        patbatch_entry = json.loads(f.read())
        f.close

        result = fhir_patient_batch_handler.create_fhir_bundle(patbatch_entry["primaryPatientResourceId"],
                                             patbatch_entry["primaryPatientResourceEntry"],
                                             patbatch_entry["patientBatch"])

        resourcesFile = os.path.join(os.getcwd(), "tests/resources", "resource_map_test_file_output.json")
        f = open(resourcesFile)
        output = json.loads(f.read())
        f.close
        self.assertEqual(DeepDiff(Bundle.parse_obj(output), result), {})

if __name__ == "__main__":
    unittest.main()


