"""Basic unit tests for the plugin"""

from httmock import urlmatch, HTTMock, response
from django.test import TestCase

from plugin import InvenTreePlugin
from plugin.mixins import SettingsMixin

from .mouser import Mouser


class TestCartPlugin(TestCase, SettingsMixin, InvenTreePlugin):

    # -------------------------------------------------------------------------
    def test_reformat_mouser_price(self):

        self.assertEqual(Mouser.reformat_mouser_price(self, '1.456,34 €'), 1456.34)
        self.assertEqual(Mouser.reformat_mouser_price(self, '1,45645 €'), 1.45645)
        self.assertEqual(Mouser.reformat_mouser_price(self, '1,56 $'), 1.56)
        self.assertEqual(Mouser.reformat_mouser_price(self, ''), 0)
        self.assertEqual(Mouser.reformat_mouser_price(self, 'Mumpitz'), 0)

    # -------------------------------------------------------------------------
    def test_get_mouser_package(self):

        SettingsMixin.set_setting(self, key='MOUSERLANGUAGE', value='German')
        part_data = {'ProductAttributes': [
            {'AttributeName': 'Verpackung', 'AttributeValue': 'Reel'},
            {'AttributeName': 'Verpackung', 'AttributeValue': 'Cut Tape'},
            {'AttributeName': 'Verpackung', 'AttributeValue': 'MouseReel',
                'AttributeCost': 'Für die MouseReel™ wird Ihrem Warenkorb automatisch eine Gebühr...'},
            {'AttributeName': 'Standardpackungsmenge', 'AttributeValue': '3000'}]}

        self.assertEqual(Mouser.get_mouser_package(self, part_data), 'Reel, Cut Tape, MouseReel, ')

        SettingsMixin.set_setting(self, key='MOUSERLANGUAGE', value='English')
        self.assertEqual(Mouser.get_mouser_package(self, part_data), '')

        part_data = {}
        self.assertEqual(Mouser.get_mouser_package(self, part_data), None)

    # ----------------------------------------------------------------------------
    # Lets first test all error cases that can occur

    def test_get_mouser_partdata_errors(self):

        # No access key in settings. We test against the original Mouser API
        data = Mouser.get_mouser_partdata(self, 'namxxxe', 'none')
        self.assertEqual(data['error_status'], 'Required')

        # Wrong access key in settings. Create a key and test against Mouser API
        SettingsMixin.set_setting(self, key='MOUSERSEARCHKEY', value='blabla')
        data = Mouser.get_mouser_partdata(self, 'namxxxe', 'none')
        self.assertEqual(data['error_status'], 'InvalidAuthorization')

        # Too many request
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        content = {'Errors': [
            {'Id': 0,
             'Code': 'TooManyRequests',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
        ], 'SearchResults': None
        }

        @urlmatch(netloc=r'(.*\.)?api\.mouser\.com.*')
        def mouser_mock(url, request):
            return response(200, content, headers, None, 5, request)
        with HTTMock(mouser_mock):
            data = Mouser.get_mouser_partdata(self, 'LTC7806IUFDM#WPBF', 'none')
        self.assertEqual(data['error_status'], 'TooManyRequests', 'Too many requests per day')

        # Unknown error
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        content = {'Errors': [
            {'Id': 0,
             'Code': 'WhatEverCode',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
        ], 'SearchResults': None
        }

        @urlmatch(netloc=r'(.*\.)?api\.mouser\.com.*')
        def mouser_mock(url, request):
            return response(200, content, headers, None, 5, request)
        with HTTMock(mouser_mock):
            data = Mouser.get_mouser_partdata(self, 'LTC7806IUFDM#WPBF', 'none')
        self.assertEqual(data['error_status'], 'WhatEverCode', 'Some unknown error')

    # -------------------------------------------------------------------------
    # Test with corect data, one result returned. Because we do not want to
    # distribute a valid key and need a stable response, we mock the Mouser
    # URL using the HTTMock library. Some unused entries have been removed
    # from the content.

    def test_get_mouser_partdata(self):

        # Real search without results
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        content = {
            'Errors': [],
            'SearchResults': {
                'NumberOfResult': 0,
                'Parts': []
            }
        }

        @urlmatch(netloc=r'(.*\.)?api\.mouser\.com.*')
        def mouser_mock(url, request):
            return response(200, content, headers, None, 5, request)

        with HTTMock(mouser_mock):
            data = Mouser.get_mouser_partdata(self, 'blabla', 'none')
        self.assertEqual(data['error_status'], 'OK', 'Test one result')
        self.assertEqual(data['number_of_results'], 0)

        # Real search with one result
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        content = {
            'Errors': [],
            'SearchResults': {
                'NumberOfResult': 1,
                'Parts': [{
                    'Description': '40V, Low IQ, 3MHz, 2-Phase Synchronous Boost Controller',
                    'LeadTime': '0 Tage',
                    'LifecycleStatus': None,
                    'Manufacturer': 'Analog Devices',
                    'ManufacturerPartNumber': 'LTC7806IUFDM#WPBF',
                    'Min': '0',
                    'Mult': '0',
                    'MouserPartNumber': 'LTC7806IUFDM#WPBF',
                    'ProductAttributes': [],
                    'PriceBreaks': [],
                    'ProductDetailUrl': 'https://www.mouser.de/ProductDetail/Analog-Devices/LTC7806IUFDMWPBF',
                    'Reeling': False,
                    'ROHSStatus': '',
                    'SuggestedReplacement': '',
                    'AvailabilityInStock': None,
                    'AvailabilityOnOrder': [],
                    'InfoMessages': []}]}}

        @urlmatch(netloc=r'(.*\.)?api\.mouser\.com.*')
        def mouser_mock(url, request):
            return response(200, content, headers, None, 5, request)

        with HTTMock(mouser_mock):
            data = Mouser.get_mouser_partdata(self, 'LTC7806IUFDM#WPBF', 'none')
        self.assertEqual(data['error_status'], 'OK', 'Test one result')
        self.assertEqual(data['number_of_results'], 1)
        self.assertEqual(data['SKU'], 'LTC7806IUFDM#WPBF')
        self.assertEqual(data['MPN'], 'LTC7806IUFDM#WPBF')
        self.assertEqual(data['URL'], 'https://www.mouser.de/ProductDetail/Analog-Devices/LTC7806IUFDMWPBF')
        self.assertEqual(data['lifecycle_status'], None)
        self.assertEqual(data['pack_quantity'], '0')
        self.assertEqual(data['description'], '40V, Low IQ, 3MHz, 2-Phase Synchronous Boost Controller')
        self.assertEqual(data['package'], '')
        self.assertEqual(data['price_breaks'], [])
