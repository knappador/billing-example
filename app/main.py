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
import netcheck


class ModalCtl:
    ''' just a container for keeping track of modals and implementing
    user prompts.'''
    def ask_connect(self, tried_connect_callback):
        Logger.info('Opening net connect prompt')
        text = ('You need internet access to do that.  Do you '
                'want to go to settings to try connecting?')
        content = AskUser(text=text,
                          action_name='Settings',
                          callback=tried_connect_callback,
                          auto_dismiss=False)
        p = Popup(title = 'Network Unavailable',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        p.open()

    def ask_retry_purchase(self, retry_purchase_callback):
        Logger.info('Purchase Failed')
        text = ('There was a problem purchasing the item.  Would'
                ' you like to retry?')
        content = AskUser(text=text,
                          action_name='Retry',
                          callback=retry_purchase_callback,
                          auto_dismiss=False)
        p = Popup(title = 'Purchase Failed',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        p.open() 


class AskUser(RelativeLayout):
    ''' Callback(bool) if user wants to do something'''
    action_name = StringProperty()
    cancel_name = StringProperty()
    text = StringProperty()
    
    def __init__(self, 
                 action_name='Okay', 
                 cancel_name='Cancel', 
                 text='Are you Sure?',
                 callback=None, # Why would you do this?
                 *args, **kwargs):
        self.action_name = action_name
        self.cancel_name = cancel_name
        self._callback = callback
        self.text = text
        modal_ctl.modal = self
        super(AskUser, self).__init__(*args, **kwargs)

    def answer(self, yesno):
        ''' Callbacks in prompts that open prompts lead to errant clicks'''
        modal_ctl.modal.dismiss()
        if self._callback:
            def delay_me(*args):
                self._callback(yesno)
            Clock.schedule_once(delay_me, 0.1)


class Product(Button):
    ''' Press to purchase'''
    def __init__(self, product_key, **kwargs):
        self.product_key = product_key
        self.text = 'Purchase ' + product_key
        super(Button, self).__init__(**kwargs)

    def on_press(self):
        billing.purchase(self.product_key)


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
    
    def update_products(self, skus):
        ''' create product list from the billing object.
        since the sku's are passed into billing, this could be done
        from a constant list instead of waiting on billint.'''
        pl = self.product_list
        pl.clear_widgets()
        ps = self.products
        for k in skus:
            if not ps.has_key(k):
                ps[k] = Product(k)
        for p in ps:
            pl.add_widget(ps[p])

    def bind_billing(self, instance, billing):
        self.update_products(billing.skus)

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
        self.update_consumed(value, value.consumed)        

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
        global modal_ctl 
        modal_ctl = ModalCtl()
        netcheck.set_prompt(modal_ctl.ask_connect)
        b_key = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArYf73V3aCHtA1C7Kg3FO/ofDujXJj34YVlYMSvvQ2voKV6oKGXHKb+7F9MuYTbEIm1RK9q1K3qW7hXTZMZtE6BYpM6xpDejj7sd09LkFSsOI8DKls/xfwXSElZn7AgA0eI3dI73tqVfE8hXfXWhcHISeY41/XJcSJA74Vz9SdjDg6dedTYsMHfHBgsAxW3PkdOZBUTyYcTGrjb57GqUvtGE+ollJoaHB4Bg8VCyjA5n03qGAYXc/rdBPaMaLlIdrmmx95pa2PzSaHlZ5UHziHsd58RVf4hFKmxDN0KyAYXsceDPnRTy8d0jAIjLhhsAw0sEj7giM31ES0nbZHIsRCwIDAQAB'
        # these have to be provided ahead of time
        skus = ['test.mock.bs1',
                'test.mock.bs2',
                'test.mock.bs3',
                'android.test.purchased',]
        global billing
        self.billing = billing = Billing(b_key, skus)
        billing.set_retry_prompt(modal_ctl.ask_retry_purchase)

    def on_pause(self):
        return True
        
    def on_resume(self):
        pass


if __name__ == "__main__":
    BillingApp().run()
