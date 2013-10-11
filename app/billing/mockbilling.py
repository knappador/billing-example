from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.properties import DictProperty, ListProperty
from kivy.logger import Logger

import netcheck

PURCHASE_STARTED=True
PURCHASE_SUCCESS=False
PURCHASE_RETRY_SUCCESS=True

class MockBilling(EventDispatcher):
    consumed = DictProperty()

    def __init__(self, key, skus, *args, **kwargs):
        super(MockBilling, self).__init__(*args, **kwargs)
        self.error_msg = 'debugging'
        self.skus = skus

    def purchase(self, sku, callback=None):
        callback = callback if callback else lambda *args, **kwargs: None
        if PURCHASE_STARTED:
            Logger.info('Ha ha faking purchase of ' + sku)
            self.purchase_callback = callback
            self.purchasing = sku
            self._process_purchase()
        return PURCHASE_STARTED

    def retry_prompt(self, callback):
        ''' monkey patch here to implement a real prompt'''
        callback(False)

    def set_retry_prompt(self, fn):
        self.retry_prompt = fn

    def _process_purchase(self):
        sku = self.purchasing
        if not netcheck.connection_available():
            netcheck.ask_connect(self._connection_callback)
        else:
            def purchase_response(dt):
                if PURCHASE_SUCCESS:
                    c = self.consumed
                    if c.has_key(sku):
                        self.consumed[sku] += 1
                    else:
                        self.consumed[sku] = 1 
                    self.purchase_callback(True, '')
                else:
                    self._fail()
            Clock.schedule_once(purchase_response, 0.5)

    def _connection_callback(self, connected):
        Logger.info('in billing connection callback: ' + str(connected))
        if connected:
            self._process_purchase()
        else:
            self._fail()

    def _fail(self):
        self._ask_retry()

    def _ask_retry(self):
        self.retry_prompt(self._retry_callback)

    def _retry_callback(self, retry):
        if retry:
            global PURCHASE_SUCCESS
            PURCHASE_SUCCESS = PURCHASE_RETRY_SUCCESS
            self._process_purchase()
        else:
            self.purchase_callback(False, self.error_msg)
            self.purchasing = self.purchase_callback = None
