from apps.common.domain.exceptions import DomainError


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


class VehicleNotFound(DomainError):
    status_code = 404
    title = "Vehicle Not Found"
    default_detail = "No vehicle found with id={vehicle_id}."
    code = "vehicle_not_found"


class VehiclePatentAlreadyExists(DomainError):
    status_code = 409
    title = "Patent Already Exists"
    default_detail = "A vehicle with patent '{patent}' already exists."
    code = "vehicle_patent_already_exists"


class VehiclePatentNotFound(DomainError):
    status_code = 404
    title = "Patent not found"
    default_detail = "No vehicle found with patent: {patent}"
    code = "vehicle_patent_not_found"


# ---------------------------------------------------------------------------
# VehicleLog
# ---------------------------------------------------------------------------


class VehicleLogNotFound(DomainError):
    status_code = 404
    title = "Vehicle Log Not Found"
    default_detail = "No log found with id={log_id} for vehicle id={vehicle_id}."
    code = "vehicle_log_not_found"


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------


class MediaNotFound(DomainError):
    status_code = 404
    title = "Media Not Found"
    default_detail = "No media file found with id={media_id}."
    code = "media_not_found"


class InvalidMediaType(DomainError):
    status_code = 422
    title = "Invalid Media Type"
    default_detail = (
        "'{media_type}' is not a valid media type. Accepted values: photo, video."
    )
    code = "invalid_media_type"


class MediaUploadFailed(DomainError):
    status_code = 500
    title = "Media Upload Failed"
    default_detail = "The file could not be stored. Please try again."
    code = "media_upload_failed"
