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
    CartKey=''
    Data=[]
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
                    self.Data=[]
                panels.append({
                    'title': 'Mouser Actions',
                    'icon': 'fa-user',
                    'content_template': 'supplier_panel/mouser.html',
                })
            if order.supplier.pk==self.DigikeyPK and HasPermission:
                if (order.pk != self.PurchaseOrderPK):
                    self.Data=[]
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

#------------------------------ SendRequest ------------------------------------
    def SendRequest(self, Cart, Path):

        proxy_con= os.getenv('PROXY_CON')
        proxy_url= os.getenv('PROXY_URL')
        if proxy_con and proxy_url:
            Proxies = {proxy_con : proxy_url}
        elif self.get_setting('PROXY_CON') != '' and self.get_setting('PROXY_URL') != '':
            Proxies = {self.get_setting('PROXY_CON') : self.get_setting('PROXY_URL')}
        else:
            Proxies = {}
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        try:
            Response=requests.post(Path+'?apiKey='+self.get_setting('MOUSERKEY')+'&countryCode=DE',
                    verify=False,
                    proxies=Proxies,
                    data=json.dumps(Cart),
                    timeout=5,
                    headers=headers)
            Response.error_type = "OK"
        except (requests.ConnectTimeout, requests.HTTPError, requests.ReadTimeout, requests.Timeout, requests.ConnectionError) as error:
            Response=requests.models.Response()
            Response.error_type = "Connection Error"
            Response.status_code = 500
        return(Response)

#------------------------- UpdateSupplierCart ----------------------------------
# Sends the PO data to the supplier and gets back the result.

    def UpdateSupplierCart(self, Data, CartKey):
        cart={
          "CartKey": CartKey,
          "CartItems": Data
        }
        Path= 'https://api.mouser.com/api/v001/cart'
        Response=self.SendRequest(cart,Path)
        return(Response)

#--------------------- create_cart ---------------------------------------
# This is just a wrapper that selects the proper creation function base
# on the supplier. 

    def create_cart(self, supplier_pk):
        if supplier_pk==self.MouserPK:
            response=self.create_mouser_cart()
        elif supplier_pk==self.DigikeyPK:
            response=self.create_digikey_cart()
        else:
            respone=None
        return(response)

# For Mouser we send an insert request with an empty CartKey string. Mouser 
# creates a Cartkey in that case and sends it back.
# Surprisingly the part doses not show up in the newly created cart.
# So there is no need to remove it.

    def create_mouser_cart(self):
        cart={
          "CartKey": '',
          "CartItems":[
             {
               "MouserPartNumber": '595-6PAIC3104IRHBRQ1',
               "Quantity": 1,
             }
          ]
        }
        Path='https://api.mouser.com/api/v001/cart/items/insert'
        Response=self.SendRequest(cart,Path)
        return(Response)

# Digikey does not have a cart API. So we create a list using the MyLists API
# the list can easily be converted to a shipping cart in the WEB UI of Digikey

    def create_digikey_cart(self):
        print('Digikeyllllllllllllllllll')
        return(None)

#---------------------------- TransferCart ---------------------------------------
# This is called when the button is pressed and does most of the work.

    def TransferCart(self,request,pk):
        self.PurchaseOrderPK=int(pk)
        Order=PurchaseOrder.objects.filter(id=pk).all()[0]
        Response=self.create_cart(Order.supplier.pk)
        if Response.status_code != 200:
            self.ErrorCode=str(Response.status_code)
            try:
                self.Message=Response.json()['Message']
            except:
                self.Message=Response.error_type
            return HttpResponse(f'Error')
        self.CartKey=Response.json()['CartKey']
        CartItems=[]
        self.Data=[]
        Total=0
        for item in Order.lines.all():
            CartItems.append({'MouserPartNumber':item.part.SKU,
                              'Quantity':int(item.quantity),
                              'CustomerPartNumber':item.part.part.IPN})
            if item.part.SKU =='N/A':
                self.ErrorCode=''
                self.Message='Part '+item.part.part.IPN+' is not available at Mouser. Please remove from PO'
                return HttpResponse(f'Error')
        Response=self.UpdateSupplierCart(CartItems, self.CartKey)
        CartData=Response.json()
        if Response.status_code != 200:
            self.ErrorCode=str(Response.status_code)
            self.Message=CartData=Response.json()['Message']
            return HttpResponse(f'Error')
        if CartData['Errors'] != []:
            self.ErrorCode=str(Response.status_code)
            self.Message='Cart Data Error'
            return HttpResponse(f'Error')
        Status={False:'Depleted',True:'OK'}
        for CartItem in CartData['CartItems']:
            self.Data.append({'PCS':CartItem['Quantity'],
                              'SKU':CartItem['MouserPartNumber'],
                              'IPN':CartItem['CartItemCustPartNumber'],
                              'status':Status[CartItem['Quantity'] <= CartItem['MouserATS']],
                              'price':CartItem['UnitPrice'],
                              'total':CartItem['ExtendedPrice'],
                              'available':CartItem['MouserATS'],
                              'currency':CartData['CurrencyCode'],
                              })
        self.Total=CartData['MerchandiseTotal']
        self.ErrorCode=str(Response.status_code)
        self.Message=Response.error_type

        # Now we transfer the actual prices back into the PO
        for POItem in Order.lines.all():
            for MouserItem in self.Data:
                if POItem.part.SKU==MouserItem['SKU']:
                    POItem.purchase_price=MouserItem['price']
                    POItem.save()
        return HttpResponse(f'OK')

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

