from typing import Optional, List, Dict
from pydantic import BaseModel

from fhir.resources.bundle import BundleEntry

""" Define the patient_bundle endpoint's input payload. See card 184 for details and update as needed. """

# Example of the data payload json structure defined by classes below:
#     [{"patbatch_storage_id":"poid-29",
#       "primaryPatientResourceId":"1234",
#       "primaryPatientResourceEntry":{"request":{"method":"PUT","url":"Patient/1234"} ,"resource":{"name":[{"family":"last","given":["first","middle"]}],"resourceType":"Patient"}},}
#    ]
# class Request(BaseModel):
#     method: Optional[str] = "POST or PUT"
#     url: Optional[str] = "Patient/patientId"


# class ResourceName(BaseModel):
#     family: str = "last"
#     given: List[str] = ["first", "middle"]


# class Resource(BaseModel):
#     name: List[ResourceName]
#     resource_type: Optional[str] = "Patient"


# class ResourceEntry(BaseModel):
#     request: Request
#     resource: Resource


class PatientBundlePayload(BaseModel):
    patbatch_storage_id: str
    primaryPatientResourceId: str
    primaryPatientResourceEntry: Optional[BundleEntry]
