from pydantic import BaseModel, Field
from typing import Optional, Union, List
from uuid import UUID

# Data Models
class BackgroundCheckRequest(BaseModel):
    typedoc: str = Field(..., description="Document type, must be one of CC, CE, INT, NIT, PP, PPT, NOMBRE")
    doc: Union[int, str] = Field(..., description="Document number, required unless typedoc is 'NOMBRE'")
    fechaE: Optional[str] = Field(None, description="Issue date in format dd/mm/yyyy, required for CE")
    name: Optional[str] = Field(None, description="Name of person, required for INT and PP")
    force: Optional[bool] = Field(None, description="Force consultation")
    resolve_name: Optional[bool] = Field(False, description="Resolve name ambiguity")

class BackgroundCheckResponse(BaseModel):
    email: str = Field(..., description="Email de la cuenta con la que se ejecuta la consulta")
    doc: int = Field(..., description="Documento consultado")
    jobid: UUID = Field(..., description="Identificador de la consulta en proceso, con vigencia de 2 horas")
    nombre: Optional[str] = Field(None, description="Nombre de la persona consultada")
    typedoc: str = Field(..., description="Tipo de documento consultado")
    validado: Optional[bool] = Field(None, description="Retorna verdadero si el documento consultado pudo ser validado. No se retorna este valor si la consulta es de pasaporte o nombre")

class CheckStatusResponse(BaseModel):
    cedula: int = Field(..., description="Documento consultado")
    error: bool = Field(..., description="Retorna verdadero si alguna fuente presentó un error")
    estado: str = Field(..., description="Estado de la consulta. Retorna procesando, finalizado o error")
    hallazgo: bool = Field(..., description="Retorna verdadero si la persona consultada presenta un hallazgo")
    errores: Optional[List[str]] = Field(None, description="Nombres de las fuentes que presentaron un error al realizar la consulta")
    hallazgos: Optional[str] = Field(None, description="Retorna el hallazgo de mayor categoría encontrado en la consulta, sea alto, medio, bajo, info o vacio")
    id: Optional[str] = Field(None, description="Identificador de la consulta almacenada en la base de datos")
    nombre: Optional[str] = Field(None, description="Nombre de la persona consultada.")
    results: Optional[dict] = Field(None, description="Diccionario con el resultado de la consulta, expresado de forma 'NombreFuente': 'Resultado'. Resultado retorna en verdadero cuando hay un hallazgo sobre la fuente, falso cuando no lo hay o Error cuando no se pudo consultar la fuente.")
    time: Optional[float] = Field(None, description="Tiempo de duración de la consulta en segundos")
    typedoc: Optional[str] = Field(None, description="Tipo de documento consultado")
    validado: Optional[bool] = Field(None, description="Retorna verdadero si el documento consultado pudo ser validado, no se retorna este valor si la consulta es de pasaporte o nombre")
    # data: Optional[dict] = Field(None, description="Diccionario con el resultado final de la consulta cuando el estado es finalizado")

class CheckResultsResponse(BaseModel):
    data: Optional[dict] = Field(None, description="Diccionario con el resultado final de la consulta cuando el estado es finalizado")

class BatchCheckRequest(BaseModel):
    country: str = Field(..., description="Country code: CO or EC")
    checks: List[BackgroundCheckRequest] = Field(..., max_items=2000, description="List of individual background checks")
    legal_representative: Optional[List[str]] = Field(default=[], description="List of legal representatives")

class BatchCheckResponse(BaseModel):
    batch_id: str = Field(..., description="Unique identifier for the batch request")
    status: str = Field(..., description="Batch processing status")

# class JobStatusResponse(BaseModel):
#     estado: Optional[str] = Field(None, description="Processing status: 'procesando', 'finalizado'")
#     error: Optional[str] = Field(None, description="Error message if processing failed")


# class JobRequest(BaseModel):
#     job_id: str = Field(..., description="Unique job ID assigned to the request")

# class JobStatusResponse(BaseModel):
#     cedula: int = Field(..., description="Document number")
#     error: bool = Field(..., description="Indicates if there was an error")
#     errores: list = Field(..., description="List of errors, if any")
#     estado: str = Field(..., description="Current status of the job (e.g., 'finalizado')")
#     hallazgo: bool = Field(..., description="Indicates if a finding was made")
#     hallazgos: str = Field(..., description="Severity of findings (e.g., 'Alto')")
#     id: str = Field(..., description="Unique job ID")
#     nombre: str = Field(..., description="Name of the person associated with the document")
#     results: dict = Field(..., description="Detailed results of the analysis")
#     time: float = Field(..., description="Time taken to process the request")
#     typedoc: str = Field(..., description="Type of document (e.g., 'CC')")
#     validado: bool = Field(..., description="Indicates if the document was validated")

# class JobResultsResponse(BaseModel):
#     job_id: str = Field(..., description="Job ID of the request")
#     data: dict = Field(..., description="Full response data from tusdatos API")

# class ErrorResponse(BaseModel):
#     detail: dict = Field(..., description="Details of the error, including the status and message")