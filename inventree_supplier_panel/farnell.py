from inventree_supplier_panel.request_wrappers import Wrappers


class Farnell():
    # --------------------------- get_farnell_partdata -----------------------------
    def get_farnell_partdata(self, sku, options):

        store = 'de.farnell.com'
        currency = 'EUR'

        part_data = {}
        access_key = self.get_setting('FARNELLSEARCHKEY')
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        path = 'https://api.element14.com/catalog/products?'
        path_string = path + 'term=id:' + sku + '&storeInfo.id=' + store + '&resultsSettings.responseGroup=large&callInfo.responseDataFormat=json&callinfo.apiKey=' + access_key
        response = Wrappers.get_request(self, path_string, header)
        try:
            response = response.json()
        except Exception:
            part_data['error_status'] = str(response.content)
            return part_data
        try:
            part_data['error_status'] = str(response['error'])
            return part_data
        except Exception:
            pass
        response = response['premierFarnellPartNumberReturn']
        # print(response)
        part_data['error_status'] = 'OK'
        part_data['number_of_results'] = response['numberOfResults']
        part_data['price_breaks'] = []
        part_data['SKU'] = response['products'][0]['sku']
        part_data['MPN'] = response['products'][0]['translatedManufacturerPartNumber']
        part_data['URL'] = 'https://www.element14.com/community/view-product.jspa?fsku=' + sku
        part_data['lifecycle_status'] = response['products'][0]['productStatus']
        part_data['pack_quantity'] = str(response['products'][0]['translatedMinimumOrderQuality'])
        part_data['description'] = response['products'][0]['displayName']
        part_data['package'] = response['products'][0]['unitOfMeasure']
        for pb in response['products'][0]['prices']:
            new_price = pb['cost']
            part_data['price_breaks'].append({'Quantity': pb['from'], 'Price': new_price, 'Currency': currency})
        return part_data
