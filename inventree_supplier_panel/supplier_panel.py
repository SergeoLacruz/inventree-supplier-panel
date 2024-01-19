from django.conf.urls import url
from django.http import HttpResponse
from django.urls import re_path

from order.views import PurchaseOrderDetail
from order.models import PurchaseOrder
from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, SettingsMixin, UrlsMixin
from company.models import Company
from inventree_supplier_panel.version import PLUGIN_VERSION
from users.models import check_user_role
import requests
import json
import os

class SupplierCartPanel(PanelMixin, SettingsMixin, InvenTreePlugin, UrlsMixin):

    # Define data that is displayed on the panel
    Message=''
    ErrorCode=''
    Total=0
    PurchaseOrderPK=0

    NAME = "SupplierCart"
    SLUG = "suppliercart"
    TITLE = "Create Mouser Cart"
    AUTHOR = "Michael"
    PUBLISH_DATE = "2023-11-15T20:00:00"
    DESCRIPTION = "This plugin allows to transfer a PO into a mouser shopping cart."
    VERSION = PLUGIN_VERSION

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
            'description': 'Refresh token Digikey',
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
        <li>Create a key for the Mouser API</li>
        <li>RTFM</li>
        <li>Enable the plugin</li>
        <li>Put keys into settings</li>
        <li>Enjoy</li>
        <li>Remove the shopping carts regularly from your Mouser account</li>
        """

# Create the panel that will display on the PurchaseOrder view,
    def get_custom_panels(self, view, request):
        panels = []

        if isinstance(view, PurchaseOrderDetail):
            self.digikey_client_id=self.get_setting('DIGIKEY_CLIENT_ID')
            try:
                self.MouserPK=int(self.get_setting('MOUSER_PK'))
            except:
                return panels
            try:
                self.DigikeyPK=int(self.get_setting('DIGIKEY_PK'))
            except:
                return panels
            order=view.get_object()
            HasPermission=(check_user_role(view.request.user, 'purchase_order','change') or
                           check_user_role(view.request.user, 'purchase_order','delete') or
                           check_user_role(view.request.user, 'purchase_order','add'))
            if order.supplier.pk==self.MouserPK and HasPermission:
                if (order.pk != self.PurchaseOrderPK):
                    #self.Data=[]
                    pass
                panels.append({
                    'title': 'Mouser Actions',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/mouser.html',
                })
            if order.supplier.pk==self.DigikeyPK and HasPermission:
                if (order.pk != self.PurchaseOrderPK):
                    #self.Data=[]
                    pass
                panels.append({
                    'title': 'Digikey Actions',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/digikey.html',
                })
        return panels

    def setup_urls(self):
        return [
            re_path(r'^digikeytoken/', self.receive_authcode, name='digikeytoken'),
            url(r'transfercart/(?P<pk>\d+)/', self.TransferCart, name='transfer-cart'),
        ]

#------------------------------ post_request ------------------------------------
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
            Response=requests.post(path,
                    verify=False,
                    proxies=Proxies,
                    json=post_data,
                    timeout=5,
                    headers=headers)
            Response.error_type = "OK"
        except (requests.ConnectTimeout, requests.HTTPError, requests.ReadTimeout, requests.Timeout, requests.ConnectionError) as error:
            Response=requests.models.Response()
            Response.error_type = "Connection Error"
            Response.status_code = 500
        return(Response)

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
            Response=requests.get(path,
                    verify=False,
                    proxies=Proxies,
                    timeout=5,
                    headers=headers)
            Response.error_type = "OK"
        except (requests.ConnectTimeout, requests.HTTPError, requests.ReadTimeout, requests.Timeout, requests.ConnectionError) as error:
            Response=requests.models.Response()
            Response.error_type = "Connection Error"
            Response.status_code = 500
        return(Response)
#------------------------- update_cart ----------------------------------
# Sends the PO data to the supplier and gets back the result.

    def update_cart(self, supplier_pk, cart_items, cart_key):
        if supplier_pk==self.MouserPK:
            cart_data=self.update_mouser_cart(cart_items, cart_key)
        elif supplier_pk==self.DigikeyPK:
            cart_data=self.update_digikey_cart(cart_items, cart_key)
        else:
            cart_data=None
        return(cart_data)


    def update_mouser_cart(self, Data, CartKey):
        cart={
          "CartKey": CartKey,
          "CartItems": Data
        }
        Path= 'https://api.mouser.com/api/v001/cart?apiKey='+self.get_setting('MOUSERKEY')+'&countryCode=DE'
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response=self.post_request(cart,Path,headers)
        response=response.json()
        cart_items=[]
        for p in response['CartItems']:
            cart_items.append({
                              'SKU':p['MouserPartNumber'],
                              'IPN':p['CartItemCustPartNumber'],
                              'QuantityRequested':p['Quantity'],
                              'QuantityAvailable':p['MouserATS'],
                              'UnitPrice':p['UnitPrice'],
                              'ExtendedPrice':p['ExtendedPrice'],
                              'CurrencyCode':response['CurrencyCode'],
                              })
        total_price=response['MerchandiseTotal']
        shopping_cart={'MerchandiseTotal':total_price,'CartItems':cart_items,'StatusCode':200,'Message':'Success'}
        return(shopping_cart)


    def update_digikey_cart(self, cart_items, list_id):
        print('Update Digikey Cart')
        url=f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json'
        }
        url_data=[]
        for p in cart_items:
            url_data.append({'RequestedPartNumber': p['MouserPartNumber'], 
                              'CustomerReference':p['CustomerPartNumber'],
                              'Quantities': [{'Quantity': p['Quantity']}]})
        response = requests.post(url,  headers=header, json=url_data)
        part_ids=response.json()
        cart_items=[]
        merchandise_total=0
        for p in part_ids:
            response=self.get_part_info(list_id, p)
            cart_items.append({
                               'SKU':response['DigiKeyPartNumber'],
                               'IPN':response['CustomerReference'],
                               'QuantityRequested':response['Quantities'][0]['QuantityRequested'],
                               'QuantityAvailable':response['QuantityAvailable'],
                               'UnitPrice':response['Quantities'][0]['PackOptions'][0]['CalculatedUnitPrice'],
                               'ExtendedPrice':response['Quantities'][0]['PackOptions'][0]['ExtendedPrice'],
                               'CurrencyCode':'EUR'
                               })
            merchandise_total=merchandise_total+response['Quantities'][0]['PackOptions'][0]['ExtendedPrice']
        shopping_cart={'MerchandiseTotal':merchandise_total,'CartItems':cart_items,'StatusCode':200,'Message':'Success'}
        return(shopping_cart)


    def get_part_info(self, list_id, part_id):
        url=f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts/{part_id}?countryIso=DE&currencyIso=EUR&languageIso=DE&createdBy=Michael&pricingCountryIso=DE'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json'
        }
        response = self.get_request(url,  headers=header)
        return(response.json())

#--------------------- create_cart ---------------------------------------
# This is just a wrapper that selects the proper creation function base
# on the supplier. 

    def create_cart(self, supplier_pk, reference):
        if supplier_pk==self.MouserPK:
            cart_data=self.create_mouser_cart()
        elif supplier_pk==self.DigikeyPK:
            cart_data=self.create_digikey_cart(reference)
        else:
            cart_data=None
        return(cart_data)

# For Mouser we send an insert request with an empty CartKey string. Mouser 
# creates a Cartkey in that case and sends it back.
# Surprisingly the part doses not show up in the newly created cart.
# So there is no need to remove it.

    def create_mouser_cart(self):
        cart_data={}
        cart={
          "CartKey": '',
          "CartItems":[
             {
               "MouserPartNumber": '595-6PAIC3104IRHBRQ1',
               "Quantity": 3000,
             }
          ]
        }
        url='https://api.mouser.com/api/v001/cart/items/insert?apiKey='+self.get_setting('MOUSERKEY')+'&countryCode=DE'
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response=self.post_request(cart,url,headers)
        print('create Response;',response)
        if response.status_code == 200:
            cart_data['status_code']=response.status_code
            cart_data['ID']=response.json()['CartKey']
            cart_data['message']='success'
        else:
            cart_data['status_code']=response.status_code
            cart_data['message']=response.json()['Message']
        print('Shopping cart Data:',cart_data)
        return(cart_data)

# Digikey does not have a cart API. So we create a list using the MyLists API
# the list can easily be converted to a shopping cart  or a quote in the
# WEB UI of Digikey

    def create_digikey_cart(self, reference):
        cart_data={}
        token=self.refresh_digikey_access_token()
        existing_lists=self.get_lists()
        for l in existing_lists:
            print('List:',l['ListName'],l['Id'],l['CreatedBy'],l['CompanyName'])
            if l['ListName']==reference+'_5':
                cart_data['status_code']=200
                cart_data['ID']=l['Id']
                cart_data['message']='success'
                print('List already exists',cart_data)
                return(cart_data)

        url = f'https://api.digikey.com/mylists/v1/lists'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID')
        }
        url_data = {
            'ListName': reference+'_5',
            'CreatedBy': 'Michael',
            'accept':'application/json'
        }

        response = self.post_request(url_data, url,  headers=header)
        print('Raw Response:',response.content)
        if response.status_code == 200:
            cart_data['status_code']=response.status_code
            cart_data['ID']=response.json()
            cart_data['message']='success'
        else:
            cart_data['status_code']=response.status_code
            cart_data['message']=response.json()['detail']
        print('Shopping cart Data:',cart_data)
        return(cart_data)

    def get_lists(self):
        url = f'https://api.digikey.com/mylists/v1/lists?createdBy=Michael'
        header = {
            'X-DIGIKEY-Locale-Site': 'DE',
            'X-DIGIKEY-Locale-Currency': 'EUR',
            'X-DIGIKEY-Customer-Id': '15353569',
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept':'application/json'
        }
        response = self.get_request(url,  headers=header)
        return(response.json())

#-------------------------- Here starts the digikey token stuff -----------------------------
    def refresh_digikey_access_token(self):
        url = 'https://api.digikey.com/v1/oauth2/token'
        token={}
        client_id=self.get_setting('DIGIKEY_CLIENT_ID')
        client_secret=self.get_setting('DIGIKEY_CLIENT_SECRET')
        refresh_token=self.get_setting('DIGIKEY_REFRESH_TOKEN')

        url_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        response = requests.post(url, data=url_data)

        if response.status_code == 200:
            print('\033[32mToken refresh SUCCESS\033[0m')
            response_data = response.json()

            token['access_token'] = response_data['access_token']
            token['refresh_token'] = response_data['refresh_token']
            token['expires_in'] = response_data['expires_in']
            token['refresh_token_expires_in'] = response_data['refresh_token_expires_in']
            token['token_type'] = response_data['token_type']
            self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
            self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])

            with open('bla_token.json', "w") as arquivo:
                json.dump(token, arquivo)
                arquivo.close()
            return(token)
        else:
            print('\033[31m\033[1mToken refreshed FAILED\033[0m')
            print(response.status_code)
            print(response.reason)
            return(None)

#---------------------------- receive_authcode ---------------------------------------
    def receive_authcode(self, request):
        auth_code = request.GET.get('code')
        print("Received auth code", auth_code)

        url = 'https://api.digikey.com/v1/oauth2/token'
        url_data = {
            'code': auth_code,
            'client_id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'client_secret': self.get_setting('DIGIKEY_CLIENT_SECRET'),
            'redirect_uri': 'https://192.168.1.40:8123/plugin/suppliercart/digikeytoken/',
            'grant_type': 'authorization_code'
        }
        response = requests.post(url, data=url_data)
        if response.status_code == 200:
            print('\033[32mAccess Token get SUCCESS\033[0m')
            token={}
            response_data = response.json()
            token['access_token'] = response_data['access_token']
            token['refresh_token'] = response_data['refresh_token']
            token['expires_in'] = response_data['expires_in']
            token['token_type'] = response_data['token_type']
            self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
            self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
        else:
            print('Access Token failed')
            print(response.status_code)
            print(response.content)
        return HttpResponse(f'OK')

#---------------------------- TransferCart ---------------------------------------
# This is called when the button is pressed and does most of the work.

    def TransferCart(self,request,pk):
        self.PurchaseOrderPK=int(pk)
        Order=PurchaseOrder.objects.filter(id=pk).all()[0]
        cart_data=self.create_cart(Order.supplier.pk,Order.reference)
        if cart_data['status_code'] != 200:
            self.ErrorCode=str(cart_data['status_code'])
            self.Message=cart_data['message']
            return HttpResponse(f'Error')
        CartItems=[]
        Total=0
        for item in Order.lines.all():
            CartItems.append({'MouserPartNumber':item.part.SKU,
                              'Quantity':int(item.quantity),
                              'CustomerPartNumber':item.part.part.IPN})
            if item.part.SKU =='N/A':
                self.ErrorCode=''
                self.Message='Part '+item.part.part.IPN+' is not available at Mouser. Please remove from PO'
                return HttpResponse(f'Error')
        self.cart_content=self.update_cart(Order.supplier.pk, CartItems, cart_data['ID'])
#        CartData=Response.json()
#        if Response.status_code != 200:
#            self.ErrorCode=str(Response.status_code)
#            self.Message=CartData=Response.json()['Message']
#            return HttpResponse(f'Error')
#        if CartData['Errors'] != []:
#            self.ErrorCode=str(Response.status_code)
#            self.Message='Cart Data Error'
#            return HttpResponse(f'Error')

        # Now we transfer the actual prices back into the PO
        for POItem in Order.lines.all():
            for Item in self.cart_content['CartItems']:
                if POItem.part.SKU==Item['SKU']:
                    POItem.purchase_price=Item['UnitPrice']
                    POItem.save()
        return HttpResponse(f'OK')

