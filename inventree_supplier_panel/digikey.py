from common.models import InvenTreeSetting

from inventree_supplier_panel.request_wrappers import Wrappers
from inventree_supplier_panel.meta_access import MetaAccess
from urllib.parse import quote
import json


class Digikey():

    # --------------------------- get_digikey_partdata ----------------------------
    # This part is for the new digikey search V4. In case of problems, the V3
    # version is still available below. It can be selected by changing the
    # function selector in the main file.

    def get_digikey_partdata_v4(self, sku, options):
        part_data = {}
        token = Digikey.refresh_digikey_access_token(self)
        if token['status_code'] != 200:
            part_data['error_status'] = token['message']
            return part_data

        # replace invalid characters in the partnumber
        sku = quote(sku, safe='')
        url = f'https://api.digikey.com/products/v4/search/{sku}/productdetails'
        country_code = self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type': 'application/json',
            'X-DIGIKEY-Locale-Currency': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
            'X-DIGIKEY-Locale-Site': country_code,
            'X-DIGIKEY-Locale-Language': 'EN'
        }
        response = Wrappers.get_request(self, url, headers=header)
        try:
            response_json = response.json()
        except Exception:
            part_data['error_status'] = response
            return part_data
        # print(response_json)

        # If we are here, digikey responded. Lets look for errors.
        try:
            if response_json['status'] != 200:
                part_data['error_status'] = response_json['title'] + response_json['detail']
                return part_data
        except Exception:
            pass
        print('Remaining requests:', response.headers['X-RateLimit-Remaining'])

        # Select the right variation that fits the searched SKU
        for product in response_json['Product']['ProductVariations']:
            if product['DigiKeyProductNumber'] == sku:
                break
        part_data['SKU'] = product['DigiKeyProductNumber']
        part_data['MPN'] = response_json['Product']['ManufacturerProductNumber']
        part_data['URL'] = response_json['Product']['ProductUrl']
        part_data['lifecycle_status'] = response_json['Product']['ProductStatus']['Status']
        part_data['description'] = response_json['Product']['Description']['DetailedDescription']
        part_data['package'] = product['PackageType']['Name']
        part_data['price_breaks'] = []
        part_data['error_status'] = 'OK'
        part_data['number_of_results'] = 1

        # Digikey responds 0 for the pack quantity on obsolete parts. We change this because
        # Inventree does not support 0 here.
        if product['MinimumOrderQuantity'] == 0:
            part_data['pack_quantity'] = '1'
        else:
            part_data['pack_quantity'] = str(product['MinimumOrderQuantity'])
        for pb in product['StandardPricing']:
            part_data['price_breaks'].append({'Quantity': pb['BreakQuantity'],
                                              'Price': pb['UnitPrice'],
                                              'Currency': response_json['SearchLocaleUsed']['Currency']
                                              })
        return (part_data)

    # ------------------- create_digikey_cart
    # Digikey does not have a cart API. So we create a list using the MyLists API
    # The list can easily be converted to a shopping cart or a quote in the
    # WEB UI of Digikey. However the List API is not so simple to handle because
    # all the list names are stored and blocked for future use. Even deleted ones..

    def create_digikey_cart(self, order):
        cart_data = {}
        list_name = MetaAccess.get_value(self, order, 'DigiKeyListName')
        if list_name is None:
            list_name = order.reference + '-00'
        version = int(list_name[len(list_name) - 2:]) + 1
        token = Digikey.refresh_digikey_access_token(self)

        if token['status_code'] != 200:
            cart_data['error_status'] = token['message']
            return cart_data
        list_name = order.reference + '-' + str(version).zfill(2)
        i = version
        while not Digikey.check_valid_listname(self, list_name):
            i = i + 1
            list_name = order.reference + '-' + str(i).zfill(2)
            if i == version + 20:
                cart_data['ID'] = ''
                cart_data['error_status'] = 'No valid list name found within 20 attempts'
                return cart_data
        MetaAccess.set_value(self, order, 'DigiKeyListName', list_name)
        url = 'https://api.digikey.com/mylists/v1/lists'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type': 'application/json'
        }
        url_data = {
            'ListName': list_name,
            'accept': 'application/json'
        }
        response = Wrappers.post_request(self, json.dumps(url_data), url, headers=header)
#        self.status_code = response.status_code
        cart_data['ID'] = response.json()
        cart_data['error_status'] = 'OK'
        return (cart_data)

    # Error status not checked !!!
    def check_valid_listname(self, list_name):
        url = f'https://api.digikey.com/mylists/v1/lists/validate/{list_name}?createdBy=xxxx'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }
        response = Wrappers.get_request(self, url, headers=header)
        return (response.content == b'true')

    # ------------------------------------------------------------------
    # Digikey has no shopping cart API. So we create a list using the MyLists API.
    # The list can easily be transferred into an order in the web interface.

    def update_digikey_cart(self, order, list_id):

        pack_types = {'TR': 'full reel', 'DKR': 'DigiReel', 'CT': 'cut tape', 'BAG': 'bulk'}
        url = f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts'
        header = {'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
                  'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
                  'accept': 'application/json',
                  'Content-Type': 'application/json'
                  }
        cart_items = []
        for item in order.lines.all():
            cart_items.append({'RequestedPartNumber': item.part.SKU,
                               'Quantities': [{'Quantity': int(item.quantity) * int(item.part.pack_quantity)}],
                               'CustomerReference': item.part.part.IPN
                               })
        # The post equest just generates the list in the Digikey cloud
        Wrappers.post_request(self, json.dumps(cart_items), url, header)

        # Now we get the parts from the generated list
        parts_in_list = Digikey.get_parts_in_list(self, list_id)
        cart_items = []
        merchandise_total = 0
        for p in parts_in_list['PartsList']:
            if p['DigiKeyPartNumber'] != '':

                # For an obsolete part PackOptions is empty. We set a default for the rest
                # not to crash
                pack_option = {}
                pack_option['CalculatedUnitPrice'] = 0
                pack_option['ExtendedPrice'] = 0
                pack_option['MinimumOrderQuantity'] = 1
                pack_option['PackType'] = 'Obsolete'
                for pack_option in p['Quantities'][0]['PackOptions']:
                    if pack_option['DigiKeyPartNumber'] == p['DigiKeyPartNumber']:
                        break
                if pack_option['MinimumOrderQuantity'] > p['Quantities'][0]['QuantityRequested']:
                    cart_items.append({'SKU': p['DigiKeyPartNumber'],
                                       'IPN': p['CustomerReference'],
                                       'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                       'QuantityAvailable': p['QuantityAvailable'],
                                       'UnitPrice': 0,
                                       'ExtendedPrice': 0,
                                       'Error': 'Minimum order quantity not reached',
                                       })
                else:
                    try:
                        pack = pack_types[pack_option['PackType']]
                    except Exception:
                        pack = pack_option['PackType']
                    cart_items.append({'SKU': p['DigiKeyPartNumber'],
                                       'IPN': p['CustomerReference'],
                                       'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                       'QuantityAvailable': p['QuantityAvailable'],
                                       'UnitPrice': pack_option['CalculatedUnitPrice'],
                                       'ExtendedPrice': pack_option['ExtendedPrice'],
                                       'Error': pack,
                                       })
                    merchandise_total = merchandise_total + pack_option['ExtendedPrice']
            else:
                cart_items.append({'SKU': p['RequestedPartNumber'],
                                   'IPN': p['CustomerReference'],
                                   'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                   'QuantityAvailable': p['QuantityAvailable'],
                                   'UnitPrice': 0,
                                   'ExtendedPrice': 0,
                                   'Error': 'Partnumber not found at Digikey',
                                   })

        # Digikey does not return a currency code. So we take the one from the settings.
        shopping_cart = {'MerchandiseTotal': merchandise_total,
                         'CartItems': cart_items,
                         'cart_key': MetaAccess.get_value(self, order, 'DigiKeyListName'),
                         'currency_code': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
                         }
        shopping_cart['error_status'] = 'OK'
        return (shopping_cart)

    # ------------------------------- get_parts_in_list ----------------------
    def get_parts_in_list(self, list_id):
        currency_code = InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')
        country_code = self.COUNTRY_CODES[currency_code]
        url = f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts/?countryIso={country_code}&currencyIso={currency_code}&languageIso={country_code}&createdBy=xxxx&pricingCountryIso={country_code}'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }
        response = Wrappers.get_request(self, url, headers=header)
        if not response:
            return (None)
        return (response.json())

    # -------------------- Here starts the digikey token stuff --------------------
    def refresh_digikey_access_token(self):

        url = 'https://api.digikey.com/v1/oauth2/token'
        client_id = self.get_setting('DIGIKEY_CLIENT_ID')
        client_secret = self.get_setting('DIGIKEY_CLIENT_SECRET')
        refresh_token = self.get_setting('DIGIKEY_REFRESH_TOKEN')
        url_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        header = {}
        token = {}
        response = Wrappers.post_request(self, url_data, url, headers=header)
        response_json = response.json()

        # On success there is no StatusCode, just in error case
        try:
            token['status_code'] = response_json['StatusCode']
            token['message'] = response_json['ErrorDetails']
            return (token)
        except Exception:
            pass
        print('\033[32mToken refresh SUCCESS\033[0m')
        response_data = response.json()
        self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
        self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
        token['status_code'] = response.status_code
        token['message'] = 'success'
        token['acces_token'] = response_data['access_token']
        token['refresh_token'] = response_data['refresh_token']
        return (token)
