from django.http import HttpResponse
from django.urls import re_path

from order.views import PurchaseOrderDetail
from part.views import PartDetail
from part.models import Part
from order.models import PurchaseOrder
from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, SettingsMixin, UrlsMixin
from company.models import Company
from company.models import ManufacturerPart, SupplierPart
from inventree_supplier_panel.version import PLUGIN_VERSION
from inventree_supplier_panel.meta_access import MetaAccess
from users.models import check_user_role
from common.models import InvenTreeSetting

from requests.exceptions import ConnectionError
from urllib.parse import quote
import requests
import json
import os

class SupplierCartPanel(PanelMixin, SettingsMixin, InvenTreePlugin, UrlsMixin):

    # Define data that is displayed on the panel
    PurchaseOrderPK=0

    NAME = "SupplierCart"
    SLUG = "suppliercart"
    TITLE = "Create Shopping Cart"
    AUTHOR = "Michael"
    PUBLISH_DATE = "2024-02-03:00:00"
    DESCRIPTION = "This plugin allows to transfer a PO into a supplier shopping cart."
    VERSION = PLUGIN_VERSION
    COUNTRY_CODES={'AUD':'AU','CAD':'CA','CNY':'CN','GBP':'GB','JPY':'JP','NZD':'NZ','USD':'US','EUR':'DE'}

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

# Create some help
    def get_settings_content(self, request):
        return """
        <p>Setup:</p>
        <ol>
        <li>Read the <a href="https://github.com/SergeoLacruz/inventree-supplier-panel"> docu </a> on github</li>
        <li>Enable the plugin</li>
        <li>Put all required keys into settings</li>
        <li>Enjoy</li>
        <li>Remove the shopping carts regularly from your Mouser account</li>
        """

# Create the panel that will display on the PurchaseOrder view,
    def get_custom_panels(self, view, request):
        panels = []

        self.digikey_client_id=self.get_setting('DIGIKEY_CLIENT_ID')
        self.callback_url=InvenTreeSetting.get_setting('INVENTREE_BASE_URL')+'/'+self.base_url
        try:
            self.MouserPK=int(self.get_setting('MOUSER_PK'))
        except:
            self.MouserPK=None
        try:
            self.DigikeyPK=int(self.get_setting('DIGIKEY_PK'))
        except:
            self.DigikeyPK=None
        if isinstance(view, PurchaseOrderDetail):
            order=view.get_object()
            HasPermission=(check_user_role(view.request.user, 'purchase_order','change') or
                           check_user_role(view.request.user, 'purchase_order','delete') or
                           check_user_role(view.request.user, 'purchase_order','add'))
            if order.supplier.pk==self.MouserPK and HasPermission:
                if (order.pk != self.PurchaseOrderPK):
                    self.cart_content=[]
                panels.append({
                    'title': 'Mouser Actions',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/supplier.html',
                })
            if order.supplier.pk==self.DigikeyPK and HasPermission:
                if (order.pk != self.PurchaseOrderPK):
                    self.cart_content=[]
                panels.append({
                    'title': 'Digikey Actions',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/supplier.html',
                })
        if isinstance(view, PartDetail):
            HasPermission=(check_user_role(view.request.user, 'part','change') or
                           check_user_role(view.request.user, 'part','delete') or
                           check_user_role(view.request.user, 'part','add'))
            if HasPermission:
                panels.append({
                    'title': 'Supplier parts',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/add_supplierpart.html',
                })

        return panels

    def setup_urls(self):
        return [
            # This one is for the Digikey OAuth callback
            re_path(r'^digikeytoken/', self.receive_authcode, name='digikeytoken'),
            re_path(r'transfercart/(?P<pk>\d+)/', self.TransferCart, name='transfer-cart'),
            re_path(r'addsupplierpart(?:\.(?P<format>json))?$', self.add_supplierpart, name='add-supplierpart'),
        ]

#---------------------- post_request and get_request wrappers ---------------------------
    def post_request(self, post_data, path, headers):
        proxy_con= os.getenv('PROXY_CON')
        proxy_url= os.getenv('PROXY_URL')
        if proxy_con and proxy_url:
            Proxies = {proxy_con : proxy_url}
        elif self.get_setting('PROXY_CON') != '' and self.get_setting('PROXY_URL') != '':
            Proxies = {self.get_setting('PROXY_CON') : self.get_setting('PROXY_URL')}
        else:
            Proxies = {}
        try:
            response=requests.post(path,
                    verify=False,
                    proxies=Proxies,
                    data=post_data,
                    timeout=5,
                    headers=headers)
            response.error_type = "OK"
        except Exception as e:
            self.cart_content={'status_code': e.args,
                              }
            raise ConnectionError
        if response.status_code != 200:
            self.cart_content={'status_code': response.status_code,
                               'message' : response.content
                              }
            raise ConnectionError
        return(response)

    def get_request(self, path, headers):
        proxy_con= os.getenv('PROXY_CON')
        proxy_url= os.getenv('PROXY_URL')
        if proxy_con and proxy_url:
            Proxies = {proxy_con : proxy_url}
        elif self.get_setting('PROXY_CON') != '' and self.get_setting('PROXY_URL') != '':
            Proxies = {self.get_setting('PROXY_CON') : self.get_setting('PROXY_URL')}
        else:
            Proxies = {}
        try:
            response=requests.get(path,
                    verify=False,
                    proxies=Proxies,
                    timeout=5,
                    headers=headers)
        except Exception as e:
            self.cart_content={'status_code': e.args,
                              }
            raise ConnectionError
        if response.status_code != 200:
            self.cart_content={'status_code': response.status_code,
                               'message' : response.content
                              }
            raise ConnectionError
        response.error_type = "OK"
        return(response)
#------------------------- update_cart ----------------------------------
# Sends the PO data to the supplier and get back the result. We use a simple
# wrapper that calls a dedicated sunction for each supplier.

    def update_cart(self, order, cart_key):
        if order.supplier.pk==self.MouserPK:
            cart_data=self.update_mouser_cart(order, cart_key)
        elif order.supplier.pk==self.DigikeyPK:
            cart_data=self.update_digikey_cart(order, cart_key)
        else:
            cart_data=None
        return(cart_data)

# The Mouser part
# Actually we do not send an empty CartKey. So Mouser creates a new key each time
# the button is pressed. This should be improved in future.

    def update_mouser_cart(self, order, cart_key):
        country_code=self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        cart_items=[]
        for item in order.lines.all():
            cart_items.append({'MouserPartNumber':item.part.SKU,
                              'Quantity':int(item.quantity),
                              'CustomerPartNumber':item.part.part.IPN})
        cart={
          "CartKey": cart_key,
          "CartItems": cart_items
        }
#        url= 'https://api.mouser.com/api/v001/cart?apiKey='+self.get_setting('MOUSERKEY')+'&countryCode=DE'
        url='https://api.mouser.com/api/v001/cart/items/insert?apiKey='+self.get_setting('MOUSERKEY')+'&countryCode='+country_code
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response=self.post_request(json.dumps(cart), url, header)
        response=response.json()
        if response['Errors']!=[]:
            shopping_cart={'status_code':'Mouser answered: ', 'message':response['Errors'][0]['Message']}
            return(shopping_cart)
        cart_items=[]
        for p in response['CartItems']:
            if p['Errors'] == []:
                cart_items.append({
                                  'SKU':p['MouserPartNumber'],
                                  'IPN':p['CartItemCustPartNumber'],
                                  'QuantityRequested':p['Quantity'],
                                  'QuantityAvailable':p['MouserATS'],
                                  'UnitPrice':p['UnitPrice'],
                                  'ExtendedPrice':p['ExtendedPrice'],
                                  'CurrencyCode':response['CurrencyCode'],
                                  'Error':''
                                  })
            else:
                cart_items.append({
                                  'SKU':p['MouserPartNumber'],
                                  'IPN':p['CartItemCustPartNumber'],
                                  'QuantityRequested':p['Quantity'],
                                  'QuantityAvailable':p['MouserATS'],
                                  'UnitPrice':p['UnitPrice'],
                                  'ExtendedPrice':p['ExtendedPrice'],
                                  'Error':p['Errors'][0]['Message']
                                  })
        shopping_cart={'MerchandiseTotal':response['MerchandiseTotal'],
                       'CartItems':cart_items,
                       'status_code':200,
                       'cart_key':response['CartKey'],
                       'currency_code':response['CurrencyCode'],
                       'message':'Success'
                      }

        MetaAccess.set_value(order, self.NAME, 'MouserCartKey', response['CartKey'])
        return(shopping_cart)

#---------------------------- get_partdata -------------------------------------------
    def get_partdata(self, supplier, sku):

        # This will crash if the suppliers are not confugured. 
        if supplier == self.MouserPK:
            part_data = self.get_mouser_partdata(sku)
        elif supplier == self.DigikeyPK:
            part_data = self.get_digikey_partdata(sku)
        return(part_data)
#---------------------------- get_mouser_partdata ------------------------------------
    def get_mouser_partdata(self, sku):
        part_data={}

        part={
          "SearchByPartRequest": {
          "mouserPartNumber": sku,
          "partSearchOptions": "exact"
          }
        }
        country_code=self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        url='https://api.mouser.com/api/v1.0/search/partnumber?apiKey='+self.get_setting('MOUSERSEARCHKEY')
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response=self.post_request(json.dumps(part), url, header)
        response=response.json()
        if response['Errors']!=[]:
            part_data['status_code'] = response['Errors']
            return(part_data)
        NumberOfResults=int(response['SearchResults']['NumberOfResult'])
        if NumberOfResults == 0:
            part_data['status_code'] = 'Part not found: ' + sku
            return(part_data)
        for i in range(0, NumberOfResults):
            part_data['status_code'] =  200
            part_data['message'] =  'OK'
            part_data['SKU'] = response['SearchResults']['Parts'][i]['MouserPartNumber']
            part_data['MPN'] = response['SearchResults']['Parts'][i]['ManufacturerPartNumber']
            part_data['URL'] = response['SearchResults']['Parts'][i]['ProductDetailUrl']
            part_data['lifecycle_status'] = response['SearchResults']['Parts'][i]['LifecycleStatus']
            part_data['pack_quantity'] = response['SearchResults']['Parts'][i]['Mult']
            part_data['description'] = response['SearchResults']['Parts'][i]['Description']
            part_data['package'] = self.get_mouser_package(response['SearchResults']['Parts'][i])
            part_data['price_breaks'] = response['SearchResults']['Parts'][i]['PriceBreaks']
        return(part_data)

#-------------------------------- get_mouser_package --------------------------------
    # Extracts the available packages from the Mouser part data json
    def get_mouser_package(self, PartData):
        Package=''
        try:
            Attributes=PartData['ProductAttributes']
        except:
            return None
        for Att in Attributes:
            if Att['AttributeName']=='Verpackung':
                Package=Package+Att['AttributeValue']+', '
        return(Package)


# The Digikey part
# digikey has no shopping cart API. So we create a list using the MyLists API.
# The list can easily be transfered into an order in the web interface.
#-------------------------- update_digikey_cart ---------------------------------------
    def update_digikey_cart(self, order, list_id):
        url=f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json',
            'Content-Type':'application/json'
        }
        cart_items=[]
        for item in order.lines.all():
            cart_items.append({'RequestedPartNumber':item.part.SKU,
                               'Quantities': [{'Quantity': int(item.quantity)}],
                               'CustomerReference':item.part.part.IPN
                             })
        response=self.post_request(json.dumps(cart_items),url,header)
        parts_in_list=self.get_parts_in_list(list_id)
        cart_items=[]
        merchandise_total=0
        for p in parts_in_list['PartsList']:
            if p['DigiKeyPartNumber'] !='':
                cart_items.append({
                                   'SKU':p['DigiKeyPartNumber'],
                                   'IPN':p['CustomerReference'],
                                   'QuantityRequested':p['Quantities'][0]['QuantityRequested'],
                                   'QuantityAvailable':p['QuantityAvailable'],
                                   'UnitPrice':p['Quantities'][0]['PackOptions'][0]['CalculatedUnitPrice'],
                                   'ExtendedPrice':p['Quantities'][0]['PackOptions'][0]['ExtendedPrice'],
                                   'Error':p['Quantities'][0]['PackOptions'][0]['FormattedExtendedPrice'][0],
                                   })
                merchandise_total=merchandise_total+p['Quantities'][0]['PackOptions'][0]['ExtendedPrice']
            else:
                cart_items.append({
                                   'SKU':p['RequestedPartNumber'],
                                   'IPN':p['CustomerReference'],
                                   'QuantityRequested':p['Quantities'][0]['QuantityRequested'],
                                   'QuantityAvailable':p['QuantityAvailable'],
                                   'UnitPrice':0,
                                   'ExtendedPrice':0,
                                   'Error':'Partnumber not found at Digikey',
                                   })
        shopping_cart={'MerchandiseTotal':merchandise_total,
                       'CartItems':cart_items,
                       'status_code':200,
                       'cart_key':MetaAccess.get_value(order, self.NAME , 'DigiKeyListName'),
                       'currency_code':InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
                       'message':'Success',
                      }
        return(shopping_cart)

    def get_parts_in_list(self, list_id):
        currency_code = InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')
        country_code = self.COUNTRY_CODES[currency_code]
        url=f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts/?countryIso={country_code}&currencyIso={currency_code}&languageIso={country_code}&createdBy=xxxx&pricingCountryIso={country_code}'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json'
        }
        response = self.get_request(url,  headers=header)
        return(response.json())

#---------------------------- get_digikey_partdata ------------------------------------
    def get_digikey_partdata(self, sku):
        part_data={}
        token=self.refresh_digikey_access_token()

        # replace invalid characters in the partnumber
        sku = quote(sku) #it replaces invalid characters in the partnumber
        url = f'https://api.digikey.com/Search/v3/Products/{sku}'
        header = {
            'X-DIGIKEY-Locale-Site': 'DE',
            'X-DIGIKEY-Locale-Currency': 'EUR',
            'X-DIGIKEY-Locale-Language': 'de',
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type':'application/json'
        }
        response = self.get_request(url,  headers=header)
        print('Remaining requests:',response.headers['X-RateLimit-Remaining'])
        response=response.json()
        print(response)

        part_data['status_code'] =  200
        part_data['message'] =  'OK'
        part_data['SKU'] = response['DigiKeyPartNumber']
        part_data['MPN'] = response['ManufacturerPartNumber']
        part_data['URL'] = response['ProductUrl']
        part_data['lifecycle_status'] = response['ProductStatus']
        part_data['pack_quantity'] = str(response['MinimumOrderQuantity'])
        part_data['description'] =  response['DetailedDescription']
        for p in response['Parameters']:
            if p['ParameterId'] == 7:
                part_data['package'] =  p['Value']

        return(part_data)

#--------------------- create_cart ---------------------------------------
# This is a wrapper that selects the proper creation function base
# on the supplier.

    def create_cart(self, order):
        if order.supplier.pk==self.MouserPK:
            cart_data=self.create_mouser_cart(order)
        elif order.supplier.pk==self.DigikeyPK:
            cart_data=self.create_digikey_cart(order)
        else:
            cart_data=None
        return(cart_data)

# This is just a dummy. We do not create a cart ID so far. It is automatically
# created by Mouser during item insertion. The return values are only for error
# handling.

    def create_mouser_cart(self, order):
        cart_data={}
        cart_data['status_code']=200
        cart_data['ID']=''
        cart_data['message']='cc success'
        return(cart_data)

# Digikey does not have a cart API. So we create a list using the MyLists API
# the list can easily be converted to a shopping cart  or a quote in the
# WEB UI of Digikey. However the List API is not so simple the handle becase
# all the list names are stored.

    def create_digikey_cart(self, order):
        cart_data={}
        list_name = MetaAccess.get_value(order, self.NAME , 'DigiKeyListName')
        if list_name == None:
            list_name = order.reference + '-00'
        version=int(list_name[len(list_name)-2:])+1
        token=self.refresh_digikey_access_token()
        list_name=order.reference + '-' + str(version).zfill(2)
        i=version
        while not self.check_valid_listname(list_name):
            i=i+1
            list_name=order.reference + '-' + str(i).zfill(2)
            if i==version + 20:
                cart_data['status_code']=0
                cart_data['ID']=''
                cart_data['message']='No valid list name found within 20 attempts'
                return cart_data
        MetaAccess.set_value(order, self.NAME , 'DigiKeyListName', list_name)
        url = f'https://api.digikey.com/mylists/v1/lists'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type':'application/json'
        }
        url_data = {
            'ListName': list_name,
            'accept':'application/json'
        }
        response = self.post_request(json.dumps(url_data), url,  headers=header)
        cart_data['status_code']=response.status_code
        cart_data['ID']=response.json()
        cart_data['message']='success'
        return(cart_data)

    def check_valid_listname(self, list_name):
        url=f'https://api.digikey.com/mylists/v1/lists/validate/{list_name}?createdBy=xxxx'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json'
        }
        response = self.get_request(url,  headers=header)
        return(response.content==b'true')

#-------------------------- Here starts the digikey token stuff -----------------------------
    def refresh_digikey_access_token(self):

        url = 'https://api.digikey.com/v1/oauth2/token'
        client_id=self.get_setting('DIGIKEY_CLIENT_ID')
        client_secret=self.get_setting('DIGIKEY_CLIENT_SECRET')
        refresh_token=self.get_setting('DIGIKEY_REFRESH_TOKEN')
        url_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        header={}
        token={}
        response = self.post_request(url_data, url,  headers=header)
        print('\033[32mToken refresh SUCCESS\033[0m')
        response_data = response.json()
        self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
        self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
        token['status_code']=response.status_code
        token['message']='success'
        token['acces_token']=response_data['access_token']
        token['refresh_token']=response_data['refresh_token']
        return(token)

#---------------------------- receive_authcode ---------------------------------------
    def receive_authcode(self, request):
        auth_code = request.GET.get('code')
        url = 'https://api.digikey.com/v1/oauth2/token'
        url_data = {
            'code': auth_code,
            'client_id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'client_secret': self.get_setting('DIGIKEY_CLIENT_SECRET'),
            'redirect_uri': 'https://192.168.1.40:8123/plugin/suppliercart/digikeytoken/',
            'grant_type': 'authorization_code'
        }
        header={}
        response = self.post_request(url_data, url,  headers=header)
        if response.status_code == 200:
            print('\033[32mAccess Token get SUCCESS\033[0m')
            response_data = response.json()
            self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
            self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
            return HttpResponse(f'OK')
        else:
            print('\033[31m\033[1mReceive access token FAILED\033[0m')
            return HttpResponse(response.content)

#---------------------------- TransferCart ---------------------------------------
# This is called when the button is pressed and does most of the work.

    def TransferCart(self,request,pk):
        self.PurchaseOrderPK=int(pk)
        Order=PurchaseOrder.objects.filter(id=pk).all()[0]
        cart_data=self.create_cart(Order)
        if cart_data['status_code'] != 200:
            self.cart_content={}
            self.cart_content['status_code']=str(cart_data['status_code'])
            self.cart_content['message']=cart_data['message']
            return HttpResponse(f'Error')
        self.cart_content=self.update_cart(Order, cart_data['ID'])
        if self.cart_content['status_code'] != 200:
            return HttpResponse(f'Error')
        # Now we transfer the actual prices back into the PO
        for POItem in Order.lines.all():
            for Item in self.cart_content['CartItems']:
                if POItem.part.SKU==Item['SKU']:
                    POItem.purchase_price=Item['UnitPrice']
                    POItem.save()
        return HttpResponse('OK')

    def add_supplierpart(self,request):
        data=json.loads(request.body)
        print(data)
        self.part_data=self.get_partdata(data['supplier'], data['sku'])
        print(self.part_data)
        if (data['sku'] == ''):
            self.part_data['status_code'] = 'Please provide part number'
            return HttpResponse('OK')
        if (self.part_data['status_code'] != 200):
            return HttpResponse('OK')
        part = Part.objects.filter(id=data['pk']).all()[0]
        supplier = Company.objects.filter(id=data['supplier']).all()[0]
        manufacturer_part = ManufacturerPart.objects.filter(part=data['pk'])
        if len(manufacturer_part) == 0:
            self.part_data['status_code'] = 'Part has no manufacturer part'
            return HttpResponse('OK')
        sp=SupplierPart.objects.create(part=part, 
                                       supplier = supplier, 
                                       manufacturer_part = manufacturer_part[0],
                                       SKU = self.part_data['SKU'],
                                       link = self.part_data['URL'],
                                       note = self.part_data['lifecycle_status'],
                                       packaging = self.part_data['package'],
                                       pack_quantity = self.part_data['pack_quantity'],
                                       description = self.part_data['description'],
                                       )
        return HttpResponse('OK')

