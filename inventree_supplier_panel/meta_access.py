class MetaAccess():

    def get_value(self, inventree_object, app, key):
        try:
            value = inventree_object.metadata[app][key]
        except Exception:
            value = None
        print('<----', app, key, value)
        return (value)

    def set_value(self, inventree_object, app, key, value):
        print('---->', app, key, value)
        data = inventree_object.metadata
        if data is None:
            data = {}
        print('out    ', data)
        if app in data:
            app_data = data[app]
            app_data.update({key: value})
            data.update({app: app_data})
        else:
            data.update({app: {key: value}})
        print('changed', data)
        inventree_object.metadata = data
        inventree_object.save()
