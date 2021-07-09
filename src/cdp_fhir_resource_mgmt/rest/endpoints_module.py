"""
Purpose: FHIR Resources Service rest API endpoints associated with the project.yaml file.
"""

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from typing import Optional
from fastapi import HTTPException, Header, File, UploadFile
from ..util import service_logger, config
from ..fhir import fhir_patient_batch_handler
import json
import os
import uuid
import pathlib

from .patient_bundle_input_model import PatientBundlePayload
from cdp_minio.wrapper import MinioClientApi
from zipfile import ZipFile
from io import BytesIO

logger = service_logger.get_logger(__name__)
cfg = config.get_config()


def verify_tenant_id(tenant_id: str):
    """ Utility to verify tenant id provide and throw exception if not. """
    if tenant_id == None or tenant_id.strip() == "":
        logger.error("'tenant-id' header not provided.")
        raise HTTPException(
            status_code=412, detail="The 'tenant-id' request header is required."
        )


def get_minio_client() -> MinioClientApi:
    mio_ep: str = cfg["minio"]["MINIO_ENDPOINT"]
    mio_key: str = cfg["minio"]["MINIO_ROOT_USER"]
    mio_pw: str = cfg["minio"]["MINIO_ROOT_PASSWORD"]
    if not mio_ep or not mio_key or not mio_pw:
        logger.error("MinIO environment not configured: mio_ep = " + mio_ep)
        raise HTTPException(
            status_code=500, detail="MinIO storage not propertly configured."
        )
    return MinioClientApi(mio_ep, mio_key, mio_pw)


def get_bundle_array(zipped_bundles: bytes) -> list:
    """ Return the list of string patient bundles from the input zipped data. """
    logger.info("Extracting the patient's bundles from the zip object...")
    zf_object = ZipFile(BytesIO(zipped_bundles))
    # Extract the bundles from the zip object and decode the bytes to string.
    json_bundles = list()
    for item in zf_object.filelist:
        try:
            bundle_bytes = zf_object.read(item)
            bundle = json.loads(bundle_bytes.decode("utf-8"))
        except:
            logger.exception(
                "Failed to retrieve zip compressed item: {0}.".format(str(item))
            )
            continue
        json_bundles.append(bundle)
    return json_bundles


# Simple API to verify the service is running.
def ping():
    return {"Pong - the FHIR resources service is running."}


# Note: FastAPI will convert the dashes/hyphens to underscore since a dash is not in
# python variable names, thus, use "tenant_id" for the header "tenant-id"
async def patient_bundle(data: PatientBundlePayload, tenant_id: str):
    """
    Based on the input payload patient information and referenced patient bundle, this endpoint
    creates and returns a FHIR bundle that can be sent directly to a FHIR server.
    """
    verify_tenant_id(tenant_id)

    try:
        logger.info("Process patient_bundle request.")

        patbatch_storage_id = data.patbatch_storage_id

        # Get the patient's FHIR bundle or bundles that need modification.
        minio_client = get_minio_client()
        pat_zipped_bundles = await minio_client.get_object(
            tenant_id, patbatch_storage_id
        )
        logger.info(
            "got pat_zipped_bundles from storage id " + str(patbatch_storage_id)
        )
        pat_bundles = get_bundle_array(pat_zipped_bundles)
        logger.info("got pat_bundles")
        ##############################
        # FHIR Resource Management logic
        fhir_bundle = fhir_patient_batch_handler.create_fhir_bundle(
            data.primaryPatientResourceId,
            data.primaryPatientResourceEntry,
            pat_bundles,
        )
        #
    except ValidationError as e:
        # If it exists, get the first wrapped ValidationError. It will contain more specific
        # FHIR Bundle error information (e.g., FHIR bundle specific resource name).
        childModelErrorText: str = None
        if e.raw_errors != None and len(e.raw_errors) > 0:
            childValidationError: ValidationError = e.raw_errors[0].exc
            if isinstance(childValidationError, ValidationError):
                childModelErrorText = str(childValidationError.model)

        errorText = "Bundle validation error: '" + str(e) + "'."
        if childModelErrorText:
            errorText = (
                errorText
                + " Additional validation error details: '"
                + childModelErrorText
                + "'."
            )
        logger.error(errorText, exc_info=True)
        raise HTTPException(status_code=400, detail=errorText)
    except Exception as e:
        logger.error("Unexcepted error", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error. " + str(e))

    # Note: FASTAPI maps Python objects to json, thus json.dumps() is not needed.
    return fhir_bundle.dict()


if __name__ == "__main__":
    pass
