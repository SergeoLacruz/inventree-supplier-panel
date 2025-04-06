"""
Unfortunately Mouser does not list possible error codes. Here are some examples:

If the access key is wrong:
{'Errors': [
            {'Id': 0,
             'Code': 'Invalid',
             'Message': 'Invalid unique identifier.',
             'ResourceKey': 'InvalidIdentifier',
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': 'API Key'}
           ], 'SearchResults': None}

If the access key is empty:
{'Errors': [
            {'Id': 0,
             'Code': 'Required',
             'Message': 'Required',
             'ResourceKey': 'Required',
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': 'API Key'}
           ], 'SearchResults': None}

If there are invalid characters in the search string like non ACSII:
{'Errors': [
            {'Id': 0,
             'Code': 'InvalidCharacters',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
           ], 'SearchResults': None}

If you created more than 1000 requests within 24 hours:
{'Errors': [
            {'Id': 0,
             'Code': 'TooManyRequests',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
           ], 'SearchResults': None}

"""
from common.models import InvenTreeSetting

from inventree_supplier_panel.request_wrappers import Wrappers
from inventree_supplier_panel.meta_access import MetaAccess
import re
import json


class Mouser():
    # --------------------------- get_mouser_partdata -----------------------------
    def get_mouser_partdata(self, sku, options):

        part_data = {}
        part = {"SearchByPartRequest": {"mouserPartNumber": sku,
                                        "partSearchOptions": options,
                                        }
                }
        url = 'https://api.mouser.com/api/v1.0/search/partnumber?apiKey=' + self.get_setting('MOUSERSEARCHKEY')
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = Wrappers.post_request(self, json.dumps(part), url, header)
        try:
            response = response.json()
        except Exception:
            part_data['error_status'] = response
            return part_data

#        print(response)
        # If we are here, Mouser responded. Lets look for errors. Some
        # errors do not come in the Errors array, but in a Message.
        # Lets check those first
        try:
            part_data['error_status'] = response['Message']
            return part_data
        except Exception:
            pass

        # Then we evaluate the Errors array. there are some known errors
        # and the rest.
        if response['Errors'] != []:
            if response['Errors'][0]['Code'] == 'InvalidCharacters':
                part_data['error_status'] = 'InvalidCharacters'
            elif response['Errors'][0]['Code'] == 'Invalid':
                part_data['error_status'] = 'InvalidAuthorization'
            elif response['Errors'][0]['Code'] == 'TooManyRequests':
                part_data['error_status'] = 'TooManyRequests'
            else:
                part_data['error_status'] = response['Errors'][0]['Code']
            return part_data

        # If we came here, no errors have been reported and there sould be results.
        number_of_results = int(response['SearchResults']['NumberOfResult'])
        if number_of_results == 0:
            part_data['error_status'] = 'OK'
            part_data['number_of_results'] = number_of_results
            return part_data

        # Here least one result has been reported
        part_data['error_status'] = 'OK'
        number_of_results = 0

        # Sometimes Mouser reports parts with different SKU even when exace is set
        # Lest filter those
        for pd in response['SearchResults']['Parts']:
            if pd['MouserPartNumber'] == sku:
                part_data['price_breaks'] = []
                part_data['SKU'] = pd['MouserPartNumber']
                part_data['MPN'] = pd['ManufacturerPartNumber']
                part_data['URL'] = pd['ProductDetailUrl']
                part_data['lifecycle_status'] = pd['LifecycleStatus']
                part_data['pack_quantity'] = pd['Mult']
                part_data['description'] = pd['Description']
                part_data['package'] = Mouser.get_mouser_package(self, pd)
                for pb in pd['PriceBreaks']:
                    new_price = Mouser.reformat_mouser_price(self, pb['Price'])
                    part_data['price_breaks'].append({'Quantity': pb['Quantity'], 'Price': new_price, 'Currency': pb['Currency']})
                number_of_results = number_of_results + 1
            else:
                print('SKU does not match')
        part_data['number_of_results'] = number_of_results
        return part_data

    # ------------------------------- get_mouser_package --------------------------
    # Extracts the available packages from the Mouser part data json. The language
    # the Mouser uses for the anwser cannot be set. It seems to be fixed toe the region
    # where the request comes from. There is a setting for this with two values so far.
    def get_mouser_package(self, part_data):

        att_names = {'packaging': {'German': 'Verpackung', 'English': 'Packaging'}}
        package = ''
        try:
            attributes = part_data['ProductAttributes']
        except Exception:
            return None
        for att in attributes:
            if att['AttributeName'] == att_names['packaging'][self.get_setting('MOUSERLANGUAGE')]:
                package = package + att['AttributeValue'] + ', '
        return (package)

    # --------------------------- reformat_mouser_price --------------------------
    # We need a Mouser specific modification to the price answer because they put
    # funny things inside like an EURO sign and they use , instead of .

    def reformat_mouser_price(self, price):
        price = price.replace('.', '')
        price = price.replace(',', '.')
        non_decimal = re.compile(r'[^\d.]+')
        price = non_decimal.sub('', price)
        if price == '':
            price = 0
        else:
            price = float(price)
        return price

    # ------------------------ create_cart -------------------------------------------
    # For Mouser this is just a dummy. We do not create a cart ID so far. It is
    # automatically created by Mouser during item insertion. The return values are
    # only for error handling.

    def create_mouser_cart(self, order):
        cart_data = {}
        cart_data['ID'] = ''
        cart_data['error_status'] = 'OK'
        return (cart_data)

    # ------------------------ update_cart ----------------------------------
    # Actually we send an empty CartKey. So Mouser creates a new key each time
    # the button is pressed. This should be improved in future. It is mandatory
    # to send a county code. The code is dreived from the Inventree currency setting.
    # This might not always fit.

    def update_mouser_cart(self, order, cart_key):
        country_code = self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        cart_items = []
        shopping_cart = {}

        for item in order.lines.all():
            cart_items.append({'MouserPartNumber': item.part.SKU,
                               'Quantity': int(item.quantity),
                               'CustomerPartNumber': item.part.part.IPN
                               })
        cart = {
            "CartKey": cart_key,
            "CartItems": cart_items
        }
        url = 'https://api.mouser.com/api/v001/cart/items/insert?apiKey=' + self.get_setting('MOUSERCARTKEY') + '&countryCode=' + country_code
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = Wrappers.post_request(self, json.dumps(cart), url, header)

        # Return with error if response was not OK
        if response.status_code != 200:
            shopping_cart['error_status'] = str(response.content)
            return (shopping_cart)
        response = response.json()
        if response['Errors'] != []:
            shopping_cart['error_status'] = response['Errors'][0]['Message']
            return (shopping_cart)
        cart_items = []
        for p in response['CartItems']:
            if p['Errors'] == []:
                cart_items.append({'SKU': p['MouserPartNumber'],
                                   'IPN': p['CartItemCustPartNumber'],
                                   'QuantityRequested': p['Quantity'],
                                   'QuantityAvailable': p['MouserATS'],
                                   'UnitPrice': p['UnitPrice'],
                                   'ExtendedPrice': p['ExtendedPrice'],
                                   'Error': ''
                                   })
            else:
                cart_items.append({'SKU': p['MouserPartNumber'],
                                   'IPN': p['CartItemCustPartNumber'],
                                   'QuantityRequested': p['Quantity'],
                                   'QuantityAvailable': p['MouserATS'],
                                   'UnitPrice': p['UnitPrice'],
                                   'ExtendedPrice': p['ExtendedPrice'],
                                   'Error': p['Errors'][0]['Message']
                                   })

        # Here we get the currency_code from the Mouser response
        shopping_cart = {'MerchandiseTotal': response['MerchandiseTotal'],
                         'CartItems': cart_items,
                         'cart_key': response['CartKey'],
                         'currency_code': response['CurrencyCode'],
                         'error_status': 'OK',
                         }
        MetaAccess.set_value(self, order, 'MouserCartKey', response['CartKey'])
        return (shopping_cart)
