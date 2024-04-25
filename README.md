[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# The InvenTree-supplier-panel

This is a plugin for [InvenTree](https://inventree.org), which uploads a purchase order
to a supplier WEB page. After using this plugin you can directly order the parts on
supplier WEB page. You need to have a supplier account and a different kinds of API keys
depending on the supplier.
The data will be created in your supplier account. Each time you transfer your PO
a new data set cart will be created. So make sure that you delete them from time to time in
the supplier WEB interface.
The plugin also helps to create supplierparts based on the supplier part number..
Actually the plugin supports two suppliers: Mouser and Digikey.

## Installation
The plugin is on pypi. You can install it by just calling:

```
pip install inventree-supplier-panel
```

## Configuration

### Mouser Supplier ID
Place here the primary key of the supplier Mouser in your system. You can select from a list of
your suppliers. If this is not set the panel will not be displayed and a error is raised.

### Digikey Supplier ID
Place here the primary key of the supplier Digikey in your system. You can select from a list of
your suppliers. If this is not set the panel will not be displayed and a error is raised.

### Mouser API key
Place here your Mouser key for manipulating shopping carts. You find it in your Mouser account.

### Digikey ID and Digikey Secret
This is the client ID and the client secret that has been generated in the Digkey API admin WEB portal.
Copy it from there to the InvenTree settings.

### Digikey token and Digikey refresh token
These fields are filled automatically. The Digikey API requires two tokens with different life times.
Please refer to the Digikey section for more information.

### Proxy CON
Protocol to proxy server e.g. https

### Proxy URL
In case you need to authorise a proxy server between your InvenTree server and the internet
put the required setting here. Example:

```
https://user:password@ipaddress:port
```

If you do not need this just leave the fields empty.
A proxy can also be set using the environment variables PROXY_CON and PROXY_URL. The
values in the environment variables overwrite InvenTree settings.

### Base URL
The base URL for server instance is in the Server Settings category of InvenTree. The plugin
uses this setting to build the OAuth callback for Digikey. Put the correct URL here.

## What the plugin does

The plugin creates a new panel which is visible on the purchase order details view.
This is called either Mouser actions or Digikey actions depending on the supplier of the
active PO. On the panel there are three things:

- a button that starts the transfer of your PO to the supplier
- a status bar that shows error messages
- a table that contains the created Mouser shopping cart.
- in case of Digikey a button that initiates the token generation.

![Mouser Panel](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/mouser_panel.png)

The button "Transfer PO" initiates the transfer. It takes each element of your PO using the SKU of
the supplier part and transfers it to the suppliers WEB shop. When finished it downloads
the data from the WEB page and puts the data into the table. Here you see
the actual stock at the supplier and an OK bubble when the stock is large enough for you order.
You also find the actual price as well as the total amount of your order. If the supplier
detects an error with the part it is displayed in the very right column.

The plugin also transfers your IPNs (internal part numbers). Most suppliers reserve a field
for such numbers. They show up in your shopping cart as well as on the invoice and even
on the labels that they put onto the bags and reels.

Finally the actual prices are copied back into your
InvenTree purchase order line items. So you can always see what you payed for the part when
you ordered it. This does not modify the price breaks of the supplier part. These are stored
with the supplier part. Here we just modify the purchase order.

## Working with Mouser

### Set up

For this plugin to work you need to have Mouser as a supplier in your InvenTree database.
Supplierparts must be added to all the parts that you like to buy at Mouser. All Mouser supplier
parts need to have the proper SKU. It needs to match the Mouser part number exactly.

For access to the Mouser API you need a Mouser account and a shopping cart API key.
You can get this in your Mouser WEB account. Do not mess up with the Mouser search API
key. This is a different one. If the key is properly set up you can find it on the Mouser
WEB page here:
![Mouser API](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/mouser_api.png)

### Usage
Using Mouser is easy. Only the Mouser shopping cart key is required for authentication. Its lifetime
is endless. Mouser has an API for the shopping cart. On pressing the button a shopping
cart is crated and all items are put into this shopping cart. When you login to the
Mouser WEB shop you can use this shopping cart for your order.

Please be aware that the plugin creates a new cart  with a new ID each time the button is pressed.
If you afterwards create a order in the WEB UI, be careful selecting the right one
and delete all unused carts.

#### Currency support
Mouser needs a country code for currency support. The plugin selects a proper country based on
the InvenTree currency setting and transfers this to Mouser. Mouser sends back the sopping cart
in the correct currency.  The currency name is shown in last line of the table.

## Working with Digikey

### Set up

You need a registration on the [Digikey API products WEB page](https://developer.digikey.com).
This is not your normal Digikey account for shopping. You have to apply separately. After
registration create an organisation and inside the organization a production app.
The most important thing to set is the OAuth Callback. This is an URL on your local server
that is called by Digikey for key generation. The plugin sets up an URL for this.
Just add your local IP. The entry should look somehow like:

```
https://192.168.1.40:8123/plugin/suppliercart/digikeytoken/
```

In this example 192.168.1.40:8123 is the local IP address and port where my
InvenTree development server runs. Place here the appropriate address.
In Production products section make sure that Product information and MyLists is activated.

In the View tab of your app you find the Client-ID and the Client-Secret. Place those in
the plugin settings.

Digikey Supplierparts have to by in your InvenTree Database as described already in
the Mouser section.

### Usage
Using Digikey is more complex. The authorisation system is token based and they do not
have a shopping cart API.

#### Authorization
The Digikey Client ID and the Client secret are the first things you need. With those
you call an API endpoint. You HAVE to go through an interactive browser window and
enter your credentials. Afterwards Digikey opens a callback URL on your local machine
and transfers a key. With this key the plugin calls another API endpoint to create
a token and a refresh token. The key gets bad after 60 seconds.

The token is used for each call to a Digikey API. It is good for 30 minutes. It has to
be refreshed using the refresh token. This one is valid for 90 days.

The plugin has a button in the panel that initiates the first step. It opens a browser
where you enter your credentials. When the OAuth callback is properly set the URL
...plugin/suppliercart/digikeytoken/ is called. This triggers a call to
https://api.digikey.com/v1/oauth2/token from where the plugin get the tokens. The tokens
are stored in the plugin setting area. Do not change them manually.

Each time you transfer a PO the refresh token is called independently from the
tokens live time. This also refreshes the refresh token. So you are save when
you use the plugin ate least once in 90 days. In case the token gets bad you need to
create a fresh set using the token button again.

If you are confused now read the documentation on the Digikey WEB page for more details.

#### MyLists
Digikey does not have such a simple shopping cart API. The plugin uses the MyLists API.
It creates a list on the WEB shop that can easily be transferred to a shopping
cart. When creating a list a list name has to be provided. The plugin creates a name
based on the PO name and adding a -xx that counts upwards each time you push the button.
The reason is that each name is allowed only once. Even when the list is deleted, the
name stays blocked forever. If you are done with your order delete the lists from your
Digikey WEB account.

#### Currency support
Digikey requires a country code and a currency code. The plugin  uses the same translation
as mentioned in the Mouser section and transfers both to Digikey. Digikey sends back the
list in the correct currency. Unfortunately the currency code is not sent back. The only
thing Digikey sends is a currency symbol but no info if $ is USD, AUD or whatever kind of Dollar.
The plugin shows the symbol in the table for control.

## Automatically add supplierparts
The plugin can add supplierparts based on the supplier part number. For users with
edit part permission a panel called "Automatic Supplier parts" is shown. Here
you can select the supplier and add the exact supplier part number. The plugin
will create a corresponding  supplierpart. I can fill the following part fields automatically:

- Supplier part number
- URL
- Package when available
- Lifecycle status
- Minimum order
- Description

If the supplier does not provide information for a field it it left empty.

## How it works

```
def get_custom_panels(self, view, request)
```

This defines the panel. The function must return a panels list. Here it returns just one
panel. The panel is returned under three conditions: The view must be PurchaseOrderDetail,
the supplier must be Mouser or Digikey and the user must have edit permissions to purchase orders.
The content_template is an html file that defines how the panel content looks.

```
re_path(r'transfercart/(?P<pk>\d+)/', self.TransferCart, name='transfer-cart'),
```
Here we define the url that controls the panel. Let's look at the details here:

- ```name='transfer-cart'```: This is the name under which the url is called from the html file. We will
come to that later when we discuss the template.

- ```self.TransferCart``` is the function that is called. It is defined later in this plugin

- ```transfercart/(?P<pk>\d+)/``` The string that looks a bit like white noise defines the url. transfercart
is the url which can be chosen freely. The ? is well known for parameters. In this case we get just one
parameter, the orders primary key. \d+ is a regular expression that limits the parameters to a digital
number with n digits.

May be it is worth to leave a few more words on this. We define the url of the plugin. This is called by the Javascript
function when we push the button. Let's have a look on the names and how they belong together:

![Dataflow](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/plugin_dataflow.svg)

In the picture you see the relevant lines in the python and java code. The names in the coloured boxes need to match.
In case something does not fit the panel will not render and you will get an error message.

## Issues

### API keys are global
The API keys and especially the proxy password are user specific and shall not be given to
others. Up to now there are no user specific settings in InvenTree. So these keys are global
and visible to, at least every admin. All users who use the plugin will have the same
keys. We use a team key to solve this.

### Missing DigiKey features
Digikey allows more features like customer ID and list owners. These are not implemented so far.
The plugin supports just a single Digikey organization and user. Some APIs require a createdBy
value to be set. xxxx works fine so far.

### https Callback
The OAuto callback setting in your Digikey WEB account allows only https. http is not allowed.
This is usually not a problem in production environments. However the development server
usually runs http. But InvenTree has the required stuff for https on board. I just changed
the runserver to runsslserver in tasks.py.

