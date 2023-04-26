[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# The inventree-supplier-panel

This is a plugin for [InvenTree](https://inventree.org), which translates a purchase order
into a Mouser shopping cart. After using this plugin you can directly order the shopping
cart on the Mouser WEB page. J You need to have a Mouser account  and a Mouser API key. 
The shopping cart will be created in your Mouser account.

## Prerequisites

For this plugin to work you need to have Mouser as as supplier in your InvenTree data.
The supplier name needs to be Mouser, not Mouser inc. or something like that. Suppliers
parts must be added to all the parts that you like to buy at Mouser. All Mouser supplier
parts need to have the proper SKU. 

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
### Supplier API key
Place here you Mouser shopping cart key. 

### Supplier shopping cart key
Each shopping cart on the Mouser page has a designated key. You can have several shopping carts 
in our account. Each cart has a separate key. The plugin puts your PO into the cart with this key.
If you do not have a shopping cart key, leave the field empty. the plugin will create a cart
and save the key in the field. 

### Proxies
In case you need to authorise a proxy server between your InvenTree server and the internet
put the required setting here. The argument for the request is {'Proxy CON' : 'Proxy URL'} for
example: ```{ 'https' : 'https://user:password@ipaddress:port' }.```
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

All items that have been in the cart before get deleted. Tha cart always contains only the parts
in your PO. 

The plugin also transfers your IPNs (internal part numbers). Mouser reserves a field 
for such numbers. They show up in your shopping cart as well as on the invoice and even
on the labels that they put onto the bags and reels. 

## How it works
Work to do :-)


## Issues
### Mouser messed up
It can happen that the Mouser shopping cart API gets messed up and no item are added into
your cart. Just delete the cart in that case and delete the key in the plugin setting.
A new key will be created an usually works. 

### API keys are global
The API keys and especially the proxy password are user specific and shall not be given to 
others. up to now there are no user specific settings in InvenTree. So these keys are global
and visible to, at least every admin. All users who use the plugin will have the same
keys. We use a team key to solve this.

### Other suppliers
Actually this works only for Mouser. Other suppliers like Digikey, Farnell or Buerklin
might follow. 

