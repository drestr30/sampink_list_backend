from pydantic import BaseModel, Field
from typing import Optional

# Data Models
class JobRequest(BaseModel):
    typedoc: str = Field(..., description="Document type, must be one of CC, CE, INT, NIT, PP, PPT, NOMBRE")
    doc: str = Field(..., description="Document number or name if typedoc is 'NOMBRE'")
    fechaE: Optional[str] = Field(None, description="Issue date in format dd/mm/yyyy, required for CE")
    name: Optional[str] = Field(None, description="Name of person, required for INT and PP")
    force: Optional[bool] = Field(None, description="Force consultation")
    resolve_name: Optional[bool] = Field(None, description="Resolve name ambiguity")

class JobResponse(BaseModel):
    jobid: str = Field(..., description="Unique job ID assigned to the request")
    # status: str = Field(..., description="Status of the request (e.g., 'pending', 'completed')")
    data: Optional[dict] = Field(None, description="Additional response message")

# class JobRequest(BaseModel):
#     job_id: str = Field(..., description="Unique job ID assigned to the request")

class JobStatusResponse(BaseModel):
    cedula: int = Field(..., description="Document number")
    error: bool = Field(..., description="Indicates if there was an error")
    errores: list = Field(..., description="List of errors, if any")
    estado: str = Field(..., description="Current status of the job (e.g., 'finalizado')")
    hallazgo: bool = Field(..., description="Indicates if a finding was made")
    hallazgos: str = Field(..., description="Severity of findings (e.g., 'Alto')")
    id: str = Field(..., description="Unique job ID")
    nombre: str = Field(..., description="Name of the person associated with the document")
    results: dict = Field(..., description="Detailed results of the analysis")
    time: float = Field(..., description="Time taken to process the request")
    typedoc: str = Field(..., description="Type of document (e.g., 'CC')")
    validado: bool = Field(..., description="Indicates if the document was validated")

class JobResultsResponse(BaseModel):
    job_id: str = Field(..., description="Job ID of the request")
    data: dict = Field(..., description="Full response data from tusdatos API")

class ErrorResponse(BaseModel):
    detail: dict = Field(..., description="Details of the error, including the status and message")