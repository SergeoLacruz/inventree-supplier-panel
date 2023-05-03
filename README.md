[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# The InvenTree-supplier-panel

This is a plugin for [InvenTree](https://inventree.org), which translates a purchase order
into a Mouser shopping cart. After using this plugin you can directly order the shopping
cart on the Mouser WEB page. You need to have a Mouser account and a Mouser API key. 
The shopping cart will be created in your Mouser account.

## Prerequisites

For this plugin to work you need to have Mouser as as supplier in your InvenTree data.
Suppliers parts must be added to all the parts that you like to buy at Mouser. All Mouser supplier
parts need to have the proper SKU. It needs to match the Mouser part number exactly.

For access to the Mouser API you need a Mouser account and a shopping cart API key. 
You can get this on the Mouser WEB page. Do not mess up with the Mouser search API
key. This is different. If the key is properly set up you can find it on the Mouser 
WEB page here:
![Mouser API](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/mouser_api.png)

## Installation

```
pip install git+https://github.com/SergeoLacruz/inventree-supplier-panel
```

## Configuration 
### Mouser Supplier ID
Place here the primary key of the supplier Mouser in your system. You can select from a list of
your suppliers.

### Supplier API key
Place here you Mouser key for manipulating shopping carts. 

### Supplier shopping cart key
Each shopping cart on the Mouser page has a designated key. You can have several shopping carts 
in our account. Each cart has a separate key. The plugin puts your PO into the cart with this key.
If you do not have a shopping cart key, leave the field empty. The plugin will create a cart
and save the key in the field. 

### Proxies
In case you need to authorise a proxy server between your InvenTree server and the internet
put the required setting here. The argument for the request is {'Proxy CON' : 'Proxy URL'} for
example: 

```
{ 'https' : 'https://user:password@ipaddress:port' }
```

If you do not need this just leave Proxy CON empty. 

## What it does

The plugin creates a new panel which is visible on the purchase order details view. 
This is called Mouser actions. On the panel there are three things: 

- a button that starts the transfer of your PO to Mouser
- a status bar that shows error messages
- a table that contains the created Mouser shopping cart. 

![Mouser Panel](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/mouser_panel.png)

The button initiates the transfer. It takes each element of your PO, takes the SKU of
the Mouser supplier part and adds it into your shopping cart. When finished it downloads
the shopping cart from the Mouser WEB page and puts the data into the table. Here you see
the actual stock at mouser and an OK bubble when the stock is large enough for you order. 
You also find the actual price as well as the total amount of your order. 

All items that have been in the cart before get deleted. The cart always contains only the parts
in your PO. 

The plugin also transfers your IPNs (internal part numbers). Mouser reserves a field 
for such numbers. They show up in your shopping cart as well as on the invoice and even
on the labels that they put onto the bags and reels. 

Finally the prices that come with the Mouser shopping cart will be copied back into your
InvenTree purchase order line items. So you can always see what you payed for the part when
you ordered it. This does not modify the price breaks of the supplier part. These are stored
with the supplier part. Here we just modify the purchase order. 

The panel is only displayed when the supplier of the current purchase order is Mouser.
In addition the current user must have change, add or delete access to purchase orders. 

## How it works

```
def get_custom_panels(self, view, request)
```

This defines the panel. The function must return a panels list. Here it return just one 
panel. The panel is returned under three conditions: The view must be PurchaseOrderDetail, 
the supplier must be Mouser and the user must have edit permissions to purchase orders. 
The content_template is an html file that defines how the panel content looks. 

```
def get_custom_panels(self, view, request)
```
Here we define the url that controls the panel. Let's look at the details here:

- ```name='transfer-cart'```: This is the name under which the url is called from the html file. We will
come to that later when we discuss the template. 

- ```self.TransferCart``` is the function that is called. It is defined later in this plugin

- ```transfercart/(?P<pk>\d+)/``` The string that looks a bit like white noise defines the url. transfercart
ist the url togehter with the slug. The ? is well known for parameters. In this case we get just one 
parameter, the orders primary key. \d+ is a regular expression that limits the parameters to a digital
number with n digits. 

## Issues
### Mouser messed up
It can happen that the Mouser shopping cart API gets messed up and no item are added into
your cart. Just delete the cart in that case and delete the key in the plugin setting.
A new key will be created and usually works.  

### API keys are global
The API keys and especially the proxy password are user specific and shall not be given to 
others. Up to now there are no user specific settings in InvenTree. So these keys are global
and visible to, at least every admin. All users who use the plugin will have the same
keys. We use a team key to solve this.

### Other suppliers
Actually this works only for Mouser. Other suppliers like Digikey, Farnell or Buerklin
might follow. 

