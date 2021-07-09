import os
from typing import Dict
import pytest
from cdp_fhir_resource_mgmt.rest import endpoints_module
from fastapi import HTTPException
from cdp_fhir_resource_mgmt.rest.patient_bundle_input_model import PatientBundlePayload
from cdp_minio.wrapper import MinioClientApi


def set_minio_mock_data_return_patient(mocker, zip_path: str) -> dict:
    """ 
    Utility to set the mock minio data and return the first patient entry
    within the input file.
    """
    with open(zip_path, "rb") as file:
        zip_bytes: bytes = file.read()
    mocker.patch.object(MinioClientApi, "get_object", return_value=zip_bytes)

    # Get the first patient resource in the data, if one exists.
    unzipped_array = endpoints_module.get_bundle_array(zip_bytes)
    patient_entry = None
    for entry in unzipped_array[0]["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            patient_entry = entry
            break
    return patient_entry


def test_ping_endpoint():
    print("Test ping...")
    response = endpoints_module.ping()


def test_get_bundle_array():
    with open(
        "./tests/resources/for_endpoints_module/fhirBundlePatientMrnPID1234_2Files.zip",
        "rb",
    ) as file:
        zip_bytes: bytes = file.read()
    unzipped_array = endpoints_module.get_bundle_array(zip_bytes)
    assert len(unzipped_array) == 2
    assert isinstance(unzipped_array[0], Dict)


def test_get_minio_client():
    assert endpoints_module.get_minio_client()


def test_verify_tenant_id():
    endpoints_module.verify_tenant_id("some-tenant-id")  # Expect no Exception.

    with pytest.raises(HTTPException):
        endpoints_module.verify_tenant_id(None)  # Expect Exception.

    with pytest.raises(HTTPException):
        endpoints_module.verify_tenant_id("  ")  # Expect Exception.


@pytest.mark.asyncio
async def test_patient_bundle(mocker):
    test_storage_id = "dummy_sid"
    test_patient_mrn = "PATID1234"  # Must match the Fhir bundle zip file used below.

    patient_entry = set_minio_mock_data_return_patient(
        mocker,
        "./tests/resources/for_endpoints_module/fromAndy-contains1FhirBundle.zip",
    )
    assert patient_entry  # Ensure an entry was found.

    # Define input payload for patient_bundle endpoint and test it
    payload = PatientBundlePayload(
        patbatch_storage_id=test_storage_id,
        primaryPatientResourceId=test_patient_mrn,
        primaryPatientResourceEntry=patient_entry,
    )
    response = await endpoints_module.patient_bundle(payload, "dummy_tenant")
    assert response != None
    assert isinstance(response, Dict)


@pytest.mark.asyncio
async def test_patient_bundle_with_400error(mocker):
    test_storage_id = "dummy_sid"
    test_patient_mrn = "PATID5421"  # Must match the Fhir bundle zip file used below.

    patient_entry = set_minio_mock_data_return_patient(
        mocker,
        "./tests/resources/for_endpoints_module/PATID5421-2021-06-24T19.54.31.832316255Z-NoStatusInDiagReport-fhir.json.zip",
    )
    assert patient_entry  # Ensure an entry was found.

    # Define input payload for patient_bundle endpoint and test it
    payload = PatientBundlePayload(
        patbatch_storage_id=test_storage_id,
        primaryPatientResourceId=test_patient_mrn,
        primaryPatientResourceEntry=patient_entry,
    )

    # Note, http_exp is an ExceptionInfo instance, which is a wrapper around the actual exception raised.
    with pytest.raises(HTTPException) as http_exp_info:
        response = await endpoints_module.patient_bundle(payload, "dummy_tenant")
    assert http_exp_info.value.status_code == 400
    assert "DiagnosticReport" in http_exp_info.value.detail
