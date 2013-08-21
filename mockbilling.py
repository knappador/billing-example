from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.properties import DictProperty, ListProperty, BooleanProperty
from kivy.logger import Logger

class MockBilling(EventDispatcher):
    #_setup_complete = BooleanProperty()
    consumed = DictProperty()
    products = ListProperty()

    def __init__(self, key, skus, *args, **kwargs):
        super(MockBilling, self).__init__(*args, **kwargs)
        #self._setup_complete = True
        Clock.schedule_once(self.add_products, 1)

    def add_products(self, *args):
        self.products.extend(['org.fake.product1',
                              'org.fake.product2',
                              'org.fake.product3'])

    def buy(self, sku):
        Logger.info('Ha ha faking purchase of ' + sku)
        c = self.consumed
        if c.has_key(sku):
            self.consumed[sku] += 1
        else:
            self.consumed[sku] = 1 

