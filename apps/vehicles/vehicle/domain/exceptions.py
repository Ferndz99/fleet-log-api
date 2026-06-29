from django.utils.translation import gettext_lazy as _

from apps.common.domain.exceptions import DomainError


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


class VehicleNotFound(DomainError):
    """Exception raised when a requested vehicle cannot be found by its ID.

    Attributes:
        status_code (int): HTTP 404 Not Found.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring 'vehicle_id' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 404
    title = _("Vehicle Not Found")
    default_detail = _("No vehicle found with id={vehicle_id}.")
    code = "vehicle_not_found"


class VehiclePatentAlreadyExists(DomainError):
    """Exception raised when attempting to register a patent that is already in use.

    Attributes:
        status_code (int): HTTP 409 Conflict.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring 'patent' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 409
    title = _("Patent Already Exists")
    default_detail = _("A vehicle with patent '{patent}' already exists.")
    code = "vehicle_patent_already_exists"


class VehiclePatentNotFound(DomainError):
    """Exception raised when a lookup by license plate (patent) returns no results.

    Attributes:
        status_code (int): HTTP 404 Not Found.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring 'patent' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 404
    title = _("Patent not found")
    default_detail = _("No vehicle found with patent: {patent}")
    code = "vehicle_patent_not_found"


class VehiclePatentQueryParamRequired(DomainError):
    """Exception raised when the 'patent' query parameter is missing or empty.

    Attributes:
        status_code (int): HTTP 400 Bad Request.
        title (str): Title description for the error response.
        default_detail (str): Detail message shown to the client.
        code (str): Machine-readable string code identifier.
    """

    status_code = 400
    title = _("Missing query parameter")
    default_detail = _("The 'patent' query parameter is required.")
    code = "vehicle_patent_query_param_required"


# ---------------------------------------------------------------------------
# VehicleLog
# ---------------------------------------------------------------------------


class VehicleLogNotFound(DomainError):
    """Exception raised when a specific log entry cannot be found for a given vehicle.

    This error occurs when the log ID does not exist or when it exists but
    is not associated with the specified vehicle ID, ensuring relational integrity.

    Attributes:
        status_code (int): HTTP 404 Not Found.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring both 'log_id' and 'vehicle_id' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 404
    title = _("Vehicle Log Not Found")
    default_detail = _("No log found with id={log_id} for vehicle id={vehicle_id}.")
    code = "vehicle_log_not_found"


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------


class MediaNotFound(DomainError):
    """Exception raised when a requested media file cannot be found in the database.

    Attributes:
        status_code (int): HTTP 404 Not Found.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring 'media_id' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 404
    title = _("Media Not Found")
    default_detail = _("No media file found with id={media_id}.")
    code = "media_not_found"


class InvalidMediaType(DomainError):
    """Exception raised when an uploaded file extension does not match supported formats.

    Attributes:
        status_code (int): HTTP 422 Unprocessable Entity.
        title (str): Title description for the error response.
        default_detail (str): Template string requiring 'media_type' context.
        code (str): Machine-readable string code identifier.
    """

    status_code = 422
    title = _("Invalid Media Type")
    default_detail = _(
        "'{media_type}' is not a valid media type. Accepted values: photo, video."
    )
    code = "invalid_media_type"


class MediaUploadFailed(DomainError):
    """Exception raised when an internal server error prevents storing the physical file.

    This acts as a safe wrapper for low-level filesystem or cloud storage (S3) errors,
    preventing technical stack traces from leaking to the final client.

    Attributes:
        status_code (int): HTTP 500 Internal Server Error.
        title (str): Title description for the error response.
        default_detail (str): Generic message instructing the user to retry.
        code (str): Machine-readable string code identifier.
    """

    status_code = 500
    title = _("Media Upload Failed")
    default_detail = _("The file could not be stored. Please try again.")
    code = "media_upload_failed"
