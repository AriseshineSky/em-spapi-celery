from dropshipping import logger
from dropshipping.utils.utils import request


def create_dog_asin(asin, country, errors='', ignore_exc=True):
    country = country.upper()

    # url = "http://35.239.179.130/api/blacklist/dog/create/{}/{}".format(asin, country)
    # data = {'errors': errors}
    # try:
    #     response = request('POST', url=url, data=data)
    #     return response.json()
    # except Exception as e:
    #     logger.exception(e)
    #     if not ignore_exc:
    #         raise


if __name__ == '__main__':
    create_dog_asin('007364343X', 'US', errors='invalid asins', ignore_exc=True)
