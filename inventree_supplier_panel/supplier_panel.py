from django.http import HttpResponse
from django.urls import re_path

from order.views import PurchaseOrderDetail
from order.models import PurchaseOrder
from part.views import PartDetail
from part.models import Part
from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, SettingsMixin, UrlsMixin
from company.models import Company, ManufacturerPart, SupplierPart
from company.models import SupplierPriceBreak
from inventree_supplier_panel.version import PLUGIN_VERSION
from inventree_supplier_panel.mouser import Mouser
from inventree_supplier_panel.meta_access import MetaAccess
from inventree_supplier_panel.request_wrappers import Wrappers
from users.models import check_user_role
from common.models import InvenTreeSetting

from urllib.parse import quote
import json


class SupplierCartPanel(PanelMixin, SettingsMixin, InvenTreePlugin, UrlsMixin):

    PurchaseOrderPK = 0

    NAME = "SupplierCart"
    SLUG = "suppliercart"
    TITLE = "Create Shopping Cart"
    AUTHOR = "Michael"
    PUBLISH_DATE = "2024-02-03:00:00"
    DESCRIPTION = "This plugin allows to transfer a PO into a supplier shopping cart."
    VERSION = PLUGIN_VERSION
    COUNTRY_CODES = {'AUD': 'AU',
                     'CAD': 'CA',
                     'CNY': 'CN',
                     'GBP': 'GB',
                     'JPY': 'JP',
                     'NZD': 'NZ',
                     'USD': 'US',
                     'EUR': 'DE'
                     }

    SETTINGS = {
        'MOUSER_PK': {
            'name': 'Mouser Supplier ID',
            'description': 'Primary key of the Mouser supplier',
            'model': 'company.company',
        },
        'DIGIKEY_PK': {
            'name': 'Digikey Supplier ID',
            'description': 'Primary key of the Digikey supplier',
            'model': 'company.company',
        },
        'MOUSERKEY': {
            'name': 'Mouser API key',
            'description': 'Place here your key for the Mouser API',
        },
        'MOUSERSEARCHKEY': {
            'name': 'Mouser search API key',
            'description': 'Place here your key for the Mouser search API',
        },
        'DIGIKEY_CLIENT_ID': {
            'name': 'Digikey ID',
            'description': 'Client ID for Digikey',
        },
        'DIGIKEY_CLIENT_SECRET': {
            'name': 'Digikey Secret',
            'description': 'Client secret for Digikey',
        },
        'DIGIKEY_TOKEN': {
            'name': 'Digikey token',
            'description': 'Token for Digikey',
        },
        'DIGIKEY_REFRESH_TOKEN': {
            'name': 'Digikey refresh token',
            'description': 'Digikey Refresh token',
        },
        'PROXY_CON': {
            'name': 'Proxy CON',
            'description': 'Connection protocol to proxy server if needed e.g. https',
        },
        'PROXY_URL': {
            'name': 'Proxy URL',
            'description': 'URL to proxy server if needed e.g. http://user:password@ipaddress:port',
        },
    }

# ----------------------------------------------------------------------------
# Here we check the settings and show som status messages. We also construct
# the Digikey redirect_uri that needs to put into the Digikey web page.
# If the pk of the supplier is not set ein tne settings, the supplier is
# disabled. The button for Digikey token creation is also here.

    def get_settings_content(self, request):
        try:
            self.get_setting('DIGIKEY_PK')
            digikey_enabled = '<span class="badge badge-left rounded-pill bg-success">Enabled</span>'
        except Exception:
            digikey_enabled = '<span class="badge badge-left rounded-pill bg-danger">Disabled</span>'
        try:
            self.get_setting('MOUSER_PK')
            mouser_enabled = '<span class="badge badge-left rounded-pill bg-success">Enabled</span>'
        except Exception:
            mouser_enabled = '<span class="badge badge-left rounded-pill bg-danger">Disabled</span>'
        client_id = self.get_setting('DIGIKEY_CLIENT_ID')
        base_url = InvenTreeSetting.get_setting('INVENTREE_BASE_URL')
        if base_url == '':
            base_url_state = '<span class="badge badge-left rounded-pill bg-danger">Missing</span>'
        elif base_url[0:5] != 'https':
            base_url_state = '<span class="badge badge-left rounded-pill bg-danger">Server does not run https</span>'
        else:
            base_url_state = '<span class="badge badge-left rounded-pill bg-success">OK</span>'
        redirect_uri = f'{base_url}/{self.base_url}digikeytoken/'
        url = f'https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'
        return f"""
        <p>Setup:</p>
        <ol>
        <li>Read the <a href="https://github.com/SergeoLacruz/inventree-supplier-panel"> docu </a> on github</li>
        <li>Enable the plugin</li>
        <li>Put all required keys into settings</li>
        <li>Enjoy</li>
        <li>Remove the shopping carts and lists regularly from your accounts</li>
        </ol>
        <p>Status:</p>
        <table class='table table-condensed'>
           <tr>
           <td>Mouser</td><td>{mouser_enabled}</td>
           </tr>
           <tr>
           <td>Digikey</td><td>{digikey_enabled}</td>
           </tr>
           <tr>
           <td>Server Base URL</td><td>{base_url_state}</td>
           </tr>
           <tr>
           <td>Callback URL (Add this to your Digikey account)</td><td>{redirect_uri}</td>
           </tr>
        </table>
        <a class="btn btn-dark" onclick="window.open('{url}','name','width=1000px,height=800px')"">
         Create Digikey Token
        </a>
        """

# ----------------------------------------------------------------------------
# Create the panel that will display on the PurchaseOrder view.

    def get_custom_panels(self, view, request):
        panels = []
        try:
            self.registered_suppliers['Mouser']['pk'] = int(self.get_setting('MOUSER_PK'))
            self.registered_suppliers['Mouser']['is_registered'] = True
        except Exception:
            pass
        try:
            self.registered_suppliers['Digikey']['pk'] = int(self.get_setting('DIGIKEY_PK'))
            self.registered_suppliers['Digikey']['is_registered'] = True
        except Exception:
            pass

        # For purchase orders: PO transfer
        if isinstance(view, PurchaseOrderDetail):
            order = view.get_object()
            has_permission = (check_user_role(view.request.user, 'purchase_order', 'change')
                              or check_user_role(view.request.user, 'purchase_order', 'delete')
                              or check_user_role(view.request.user, 'purchase_order', 'add'))

            for s in self.registered_suppliers:
                if order.supplier.pk == self.registered_suppliers[s]['pk'] and has_permission:
                    if (order.pk != self.PurchaseOrderPK):
                        self.cart_content = []
                    panels.append({
                        'title': self.registered_suppliers[s]['name'] + ' Actions',
                        'icon': 'fa-user',
                        'content_template': self.registered_suppliers[s]['po_template'],
                    })

        # For parts: Supplier part creation
        if isinstance(view, PartDetail):
            has_permission = (check_user_role(view.request.user, 'part', 'change')
                              or check_user_role(view.request.user, 'part', 'delete')
                              or check_user_role(view.request.user, 'part', 'add'))
            show_panel = False
            for s in self.registered_suppliers:
                show_panel = show_panel or self.registered_suppliers[s]['is_registered']
            part = view.get_object()
            if has_permission and show_panel and part.purchaseable:
                panels.append({
                    'title': 'Automatic Supplier parts',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/add_supplierpart.html',
                })
        return panels

    def setup_urls(self):
        return [
            # This one is for the Digikey OAuth callback
            re_path(r'^digikeytoken/', self.receive_authcode, name='digikeytoken'),

            # Now for the plugin
            re_path(r'transfercart/(?P<pk>\d+)/', self.transfer_cart, name='transfer-cart'),
            re_path(r'addsupplierpart(?:\.(?P<format>json))?$', self.add_supplierpart, name='add-supplierpart'),
        ]

# --------------------------- get_partdata ------------------------------------
# This is just the wrapper that selects the proper supplier dependant function
    def get_partdata(self, supplier, sku):

        for s in self.registered_suppliers:
            if supplier == self.registered_suppliers[s]['pk']:
                part_data = self.registered_suppliers[s]['get_partdata'](self, sku)
        return (part_data)

# ------------------------------------------------------------------
# The Digikey part
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
        parts_in_list = self.get_parts_in_list(list_id)
        cart_items = []
        merchandise_total = 0
        for p in parts_in_list['PartsList']:
            if p['DigiKeyPartNumber'] != '':
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
                         'cart_key': MetaAccess.get_value(self, order, self.NAME, 'DigiKeyListName'),
                         'currency_code': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
                         }
        self.status_code = 200
        self.message = 'OK'
        return (shopping_cart)

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

# --------------------------- get_digikey_partdata ----------------------------
    def get_digikey_partdata(self, sku):
        part_data = {}
        token = self.refresh_digikey_access_token()
        if not token:
            return (None)

        # replace invalid characters in the partnumber
        sku = quote(sku)
        url = f'https://api.digikey.com/Search/v3/Products/{sku}'
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
        if not response:
            return (None)
        print('Remaining requests:', response.headers['X-RateLimit-Remaining'])
        response = response.json()
        part_data['SKU'] = response['DigiKeyPartNumber']
        part_data['MPN'] = response['ManufacturerPartNumber']
        part_data['URL'] = response['ProductUrl']
        part_data['lifecycle_status'] = response['ProductStatus']
        part_data['pack_quantity'] = str(response['MinimumOrderQuantity'])
        part_data['description'] = response['DetailedDescription']
        part_data['package'] = ''
        part_data['price_breaks'] = []
        for pb in response['StandardPricing']:
            part_data['price_breaks'].append({'Quantity': pb['BreakQuantity'], 'Price': pb['UnitPrice'], 'Currency': response['SearchLocaleUsed']['Currency']})
        for p in response['Parameters']:
            if p['ParameterId'] == 7:
                part_data['package'] = p['Value']
        self.status_code = 200
        self.message = 'OK'
        return (part_data)

# ------------------------ create_cart -------------------------------------------
# For Mouser this is just a dummy. We do not create a cart ID so far. It is
# automatically created by Mouser during item insertion. The return values are
# only for error handling.

    def create_mouser_cart(self, order):
        cart_data = {}
        self.status_code = 200
        cart_data['ID'] = ''
        self.message = 'Success'
        return (cart_data)

# Digikey does not have a cart API. So we create a list using the MyLists API
# The list can easily be converted to a shopping cart or a quote in the
# WEB UI of Digikey. However the List API is not so simple to handle because
# all the list names are stored and blocked for future use. Even deleted ones..

    def create_digikey_cart(self, order):
        cart_data = {}
        list_name = MetaAccess.get_value(self, order, self.NAME, 'DigiKeyListName')
        if list_name is None:
            list_name = order.reference + '-00'
        version = int(list_name[len(list_name) - 2:]) + 1
        token = self.refresh_digikey_access_token()
        if not token:
            return (None)
        list_name = order.reference + '-' + str(version).zfill(2)
        i = version
        while not self.check_valid_listname(list_name):
            i = i + 1
            list_name = order.reference + '-' + str(i).zfill(2)
            if i == version + 20:
                self.status_code = 0
                cart_data['ID'] = ''
                self.message = 'No valid list name found within 20 attempts'
                return cart_data
        MetaAccess.set_value(self, order, self.NAME, 'DigiKeyListName', list_name)
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
        self.status_code = response.status_code
        cart_data['ID'] = response.json()
        self.message = 'success'
        return (cart_data)

    def check_valid_listname(self, list_name):
        url = f'https://api.digikey.com/mylists/v1/lists/validate/{list_name}?createdBy=xxxx'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }
        response = Wrappers.get_request(self, url, headers=header)
        return (response.content == b'true')

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
        if not response:
            return (None)
        print('\033[32mToken refresh SUCCESS\033[0m')
        response_data = response.json()
        self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
        self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
        token['status_code'] = response.status_code
        token['message'] = 'success'
        token['acces_token'] = response_data['access_token']
        token['refresh_token'] = response_data['refresh_token']
        return (token)

# --------------------------- receive_authcode --------------------------------

    def receive_authcode(self, request):
        auth_code = request.GET.get('code')
        url = 'https://api.digikey.com/v1/oauth2/token'
        redirect_uri = InvenTreeSetting.get_setting('INVENTREE_BASE_URL') + '/' + self.base_url + 'digikeytoken/'
        url_data = {
            'code': auth_code,
            'client_id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'client_secret': self.get_setting('DIGIKEY_CLIENT_SECRET'),
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        header = {}
        response = Wrappers.post_request(self, url_data, url, headers=header)
        if response.status_code == 200:
            print('\033[32mAccess Token get SUCCESS\033[0m')
            response_data = response.json()
            self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
            self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
            return HttpResponse('New Digikey token successfully received')
        else:
            print('\033[31m\033[1mReceive access token FAILED\033[0m')
            return HttpResponse(response.content)

# --------------------------- transfer_cart ------------------------------------
# This is called when the button is pressed and does most of the work.

    def transfer_cart(self, request, pk):

        self.PurchaseOrderPK = int(pk)
        order = PurchaseOrder.objects.filter(id=pk).all()[0]
        for s in self.registered_suppliers:
            if order.supplier.pk == self.registered_suppliers[s]['pk']:
                supplier = s
        cart_data = self.registered_suppliers[supplier]['create_cart'](self, order)
        if self.status_code != 200:
            self.cart_content = {}
            return HttpResponse('Error')
        self.cart_content = self.registered_suppliers[supplier]['update_cart'](self, order, cart_data['ID'])
        if self.status_code != 200:
            return HttpResponse('Error')

        # Now we transfer the actual prices back into the PO
        for po_item in order.lines.all():
            for item in self.cart_content['CartItems']:
                if po_item.part.SKU == item['SKU']:
                    po_item.purchase_price = item['UnitPrice']
                    po_item.save()
        return HttpResponse('OK')

# ---------------------------- add_supplierpart -------------------------------
    def add_supplierpart(self, request):
        data = json.loads(request.body)
        part = Part.objects.filter(id=data['pk'])[0]
        supplier = Company.objects.filter(id=data['supplier'])[0]
        if (data['sku'] == ''):
            self.status_code = 'Please provide part number'
            return HttpResponse('OK')

        manufacturer_part = ManufacturerPart.objects.filter(part=data['pk'])
        if len(manufacturer_part) == 0:
            self.status_code = 'Part has no manufacturer part'
            return HttpResponse('OK')

        supplier_parts = SupplierPart.objects.filter(part=data['pk'])
        for sp in supplier_parts:
            if sp.SKU == data['sku']:
                self.status_code = 'Supplierpart with this SKU already exists'
                return HttpResponse('OK')

        part_data = self.get_partdata(data['supplier'], data['sku'])
        if (self.status_code != 200):
            return HttpResponse('OK')
        if self.debug:
            print(part_data['price_breaks'])
        sp = SupplierPart.objects.create(part=part,
                                         supplier=supplier,
                                         manufacturer_part=manufacturer_part[0],
                                         SKU=part_data['SKU'],
                                         link=part_data['URL'],
                                         note=part_data['lifecycle_status'],
                                         packaging=part_data['package'],
                                         pack_quantity=part_data['pack_quantity'],
                                         description=part_data['description'],
                                         )
        for pb in part_data['price_breaks']:
            SupplierPriceBreak.objects.create(part=sp, quantity=pb['Quantity'], price=pb['Price'], price_currency=pb['Currency'])
        return HttpResponse('OK')

# ---------------------------- Define the suppliers ----------------------------
    debug = False
    registered_suppliers = {'Mouser': {'pk': 0,
                                       'name': 'Mouser',
                                       'po_template': 'supplier_panel/mouser.html',
                                       'is_registered': False,
                                       'get_partdata': Mouser.get_mouser_partdata,
                                       'update_cart': Mouser.update_mouser_cart,
                                       'create_cart': Mouser.create_mouser_cart,
                                       },
                            'Digikey': {'pk': 0,
                                        'name': 'Digikey',
                                        'po_template': 'supplier_panel/digikey.html',
                                        'is_registered': False,
                                        'get_partdata': get_digikey_partdata,
                                        'update_cart': update_digikey_cart,
                                        'create_cart': create_digikey_cart,
                                        }
                            }
