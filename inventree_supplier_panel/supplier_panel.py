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
from inventree_supplier_panel.digikey import Digikey
from inventree_supplier_panel.request_wrappers import Wrappers
from users.models import check_user_role
from common.models import InvenTreeSetting

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
        'MOUSERCARTKEY': {
            'name': 'Mouser cart API key',
            'description': 'Place here your key for the Mouser shopping cart API',
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

# --------------------------- receive_authcode --------------------------------
# This creates the Digikey token from the authcode

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
            if sp.SKU.strip() == data['sku'].strip():
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
                                        'get_partdata': Digikey.get_digikey_partdata_v4,
                                        'update_cart': Digikey.update_digikey_cart,
                                        'create_cart': Digikey.create_digikey_cart,
                                        }
                            }
