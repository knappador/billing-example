from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty, AliasProperty, BooleanProperty, StringProperty, DictProperty
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.graphics import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.logger import Logger

from billing import Billing

# let's do this at some point instead?
#class ServiceController(EventDispatcher):
#    billing=ObjectProperty()
    
# anything here is initialized before it's used.
# do not break this contract!
global app
global billing


class Product(Button):
    ''' Press to buy '''
    def __init__(self, product_key, **kwargs):
        self.product_key = product_key
        self.text = 'Buy ' + product_key
        super(Button, self).__init__(**kwargs)

    def on_press(self):
        billing.buy(self.product_key)


class Consumed(Button):
    ''' Press to "use" a product.
        Consumption was completed by billing '''
    def __init__(self, product_key, **kwargs):
        self.product_key = product_key
        self.text = 'Use ' + product_key
        super(Button, self).__init__(**kwargs)
    
    def on_press(self):
        count = billing.consumed[self.product_key] - 1
        billing.consumed[self.product_key] = count
        Logger.debug(self.product_key + ' consumed ' + str(count) + ' remainging')

class BuyStuff(BoxLayout):
    def __init__(self, **kwargs):
        app.bind(billing=self.bind_billing)
        self.products = dict()
        super(BuyStuff, self).__init__(**kwargs)
    
    def update_products(self, instance, value):
        ''' Re-generate the product list with the inventory'''
        pl = self.product_list
        pl.clear_widgets()
        ps = self.products
        for k in value:
            if not ps.has_key(k):
                ps[k] = Product(k)
        for p in ps:
            pl.add_widget(ps[p])

    def bind_billing(self, instance, value):
        value.bind(products=self.update_products)

class AfterConsumption(BoxLayout):
    def __init__(self, **kwargs):
        app.bind(billing=self.bind_billing)
        super(AfterConsumption, self).__init__(**kwargs)

    def update_consumed(self, instance, value):
        ''' Re-generate the consumed list'''
        cl = self.consumed_list
        cl.clear_widgets()
        for k in value:
            for i in range(value[k]):
                cl.add_widget(Consumed(k))
    
    def bind_billing(self, instance, value):
        value.bind(consumed=self.update_consumed)
        

class BillingUI(FloatLayout):
    pass


class BillingApp(App):
    billing = ObjectProperty()
    def __init__(self, *args, **kwargs):
        global app
        app = self
        super(BillingApp, self).__init__(*args, **kwargs)

    def build(self):
        return BillingUI()

    def on_start(self):
        b_key = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArYf73V3aCHtA1C7Kg3FO/ofDujXJj34YVlYMSvvQ2voKV6oKGXHKb+7F9MuYTbEIm1RK9q1K3qW7hXTZMZtE6BYpM6xpDejj7sd09LkFSsOI8DKls/xfwXSElZn7AgA0eI3dI73tqVfE8hXfXWhcHISeY41/XJcSJA74Vz9SdjDg6dedTYsMHfHBgsAxW3PkdOZBUTyYcTGrjb57GqUvtGE+ollJoaHB4Bg8VCyjA5n03qGAYXc/rdBPaMaLlIdrmmx95pa2PzSaHlZ5UHziHsd58RVf4hFKmxDN0KyAYXsceDPnRTy8d0jAIjLhhsAw0sEj7giM31ES0nbZHIsRCwIDAQAB'
        # used to initialize product list?  for now, yes
        # it's possible to get this back from the inventory list instead
        # but the Inventory class will need some JNIus work =)
        skus = dict()
        global billing
        self.billing = billing = Billing(b_key, skus)

    def on_pause(self):
        return True
        
    def on_resume(self):
        pass


if __name__ == "__main__":
    BillingApp().run()
