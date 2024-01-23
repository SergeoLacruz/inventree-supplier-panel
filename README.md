[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# The InvenTree-supplier-panel

This is a plugin for [InvenTree](https://inventree.org), which translates a purchase order
into a Mouser shopping cart. After using this plugin you can directly order the shopping
cart on the Mouser WEB page. You need to have a Mouser account and a Mouser API key.
The shopping cart will be created in your Mouser account. Each time you transfer your PO
a new shopping cart will be created. So make sure that you delete them from time to time in
the mouser WEB interface.

## Prerequisites

For this plugin to work you need to have Mouser as a supplier in your InvenTree database.
Supplierparts must be added to all the parts that you like to buy at Mouser. All Mouser supplier
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
your suppliers. If this is not set the panel will not be displayed and a error is raised.

### Supplier API key
Place here your Mouser key for manipulating shopping carts.

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
values in the environment variables overwrite Inventree settings.

## What it does

The plugin creates a new panel which is visible on the purchase order details view.
This is called Mouser actions. On the panel there are three things:

- a button that starts the transfer of your PO to Mouser
- a status bar that shows error messages
- a table that contains the created Mouser shopping cart.

![Mouser Panel](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/mouser_panel.png)

The button initiates the transfer. It creates a Mouser shopping cart and takes each element of your PO using the SKU of
the Mouser supplier part and adds it into your shopping cart. When finished it downloads
the shopping cart from the Mouser WEB page and puts the data into the table. Here you see
the actual stock at Mouser and an OK bubble when the stock is large enough for you order.
You also find the actual price as well as the total amount of your order. If Mouser
detects an error with the part it is displayed in the very right column.

The plugin also transfers your IPNs (internal part numbers). Mouser reserves a field
for such numbers. They show up in your shopping cart as well as on the invoice and even
on the labels that they put onto the bags and reels.

Finally the prices that come with the Mouser shopping cart will be copied back into your
InvenTree purchase order line items. So you can always see what you payed for the part when
you ordered it. This does not modify the price breaks of the supplier part. These are stored
with the supplier part. Here we just modify the purchase order.

The plugin creates a new chopping cart with a new ID each time the button is pressed. 
If you afterwards create a real order in the WEB UI, be careful selecting the right one
and delete all unused carts.

The panel is only displayed when the supplier of the current purchase order is Mouser.
In addition the current user must have change, add or delete access to purchase orders.

## Digikey support
The support of the supplier Digikey is still experimental. There are still some problems
with proper handling of their MyLists API.

## How it works

```
def get_custom_panels(self, view, request)
```

This defines the panel. The function must return a panels list. Here it returns just one
panel. The panel is returned under three conditions: The view must be PurchaseOrderDetail,
the supplier must be Mouser and the user must have edit permissions to purchase orders.
The content_template is an html file that defines how the panel content looks.

```
url(r'transfercart/(?P<pk>\d+)/', self.TransferCart, name='transfer-cart'),
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

![Dataflow](https://github.com/SergeoLacruz/inventree-supplier-panel/blob/master/pictures/plugin_dataflow.png)

In the picture you see the relevant lines in the python and java code. The names in the coloured boxes need to match.
In case something does not fit the panel will not render and you will get an error message.

## Issues

### API keys are global
The API keys and especially the proxy password are user specific and shall not be given to
others. Up to now there are no user specific settings in InvenTree. So these keys are global
and visible to, at least every admin. All users who use the plugin will have the same
keys. We use a team key to solve this.
