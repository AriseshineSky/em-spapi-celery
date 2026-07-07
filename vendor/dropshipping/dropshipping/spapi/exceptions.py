from sp_api.base.exceptions import (
    SellingApiException,
    SellingApiBadRequestException,
    SellingApiForbiddenException,
    SellingApiNotFoundException,
    SellingApiRequestThrottledException,
    SellingApiServerException,
    SellingApiTemporarilyUnavailableException,
    SellingApiGatewayTimeoutException,
    MissingScopeException,
)


class SellingApiInvalidAsinException(SellingApiBadRequestException):
    pass