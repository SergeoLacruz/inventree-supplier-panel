# Class to access the meta data field in InvenTree. The wrappers build
# a dict with plugin name so that the data from different plugins does
# not overlap

class MetaAccess():

    def get_value(self, inventree_object, key):
        try:
            value = inventree_object.metadata[self.NAME][key]
        except Exception:
            value = None
        return (value)

    def set_value(self, inventree_object, key, value):
        data = inventree_object.metadata
        if data is None:
            data = {}
        if self.NAME in data:
            app_data = data[self.NAME]
            app_data.update({key: value})
            data.update({self.NAME: app_data})
        else:
            data.update({self.NAME: {key: value}})
        inventree_object.metadata = data
        inventree_object.save()
