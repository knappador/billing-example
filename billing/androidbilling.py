from kivy.app import App
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.properties import DictProperty, BooleanProperty, ListProperty
from kivy.logger import Logger

from jnius import autoclass, PythonJavaClass, java_method, cast
from android import activity
from android.runnable import run_on_ui_thread

context = autoclass('org.renpy.android.PythonActivity').mActivity
IabHelper = autoclass('org.kivy.billing.IabHelper')
IabResults = autoclass('org.kivy.billing.IabResult')
Inventory = autoclass('org.kivy.billing.Inventory')
Purchase = autoclass('org.kivy.billing.Purchase')

DEBUG=True

#callbacks
class _OnIabSetupFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$OnIabSetupFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_OnIabSetupFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/IabResult;)V')
    def onIabSetupFinished(self, result):
        self.callback(result)


class _QueryInventoryFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$QueryInventoryFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_QueryInventoryFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/IabResult;Lorg/kivy/billing/Inventory;)V')
    def onQueryInventoryFinished(self, result, inventory):
        self.callback(result, inventory)


class _OnPurchaseFinishedListener(PythonJavaClass):
    ''' This one seems to blow up inside the IabHelper OnActivityResult'''
    __javainterfaces__ = ['org.kivy.billing.IabHelper$OnIabPurchaseFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_OnPurchaseFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/IabResult;Lorg/kivy/billing/Purchase;)V')
    def onIabPurchaseFinished(self, result, purchase):
        self.callback(result, purchase)

class _OnConsumeFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$OnConsumeFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_OnConsumeFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/Purchase;Lorg/kivy/billing/IabResult;)V')
    def onConsumeFinished(self, purchase, result):
        self.callback(purchase, result)


class AndroidBilling(EventDispatcher):
    products = ListProperty()
    consumed = DictProperty()
    _inventory_checked = BooleanProperty(False)

    def __init__(self, app_public_key, skus, r_code = 666777):
        if DEBUG:
            skus = ['android.test.purchased']
        self.r_code = r_code
        self.skus = skus
        k = app_public_key
        c = cast('android.app.Activity', context)
        self._buy_waiting = []
        self.helper = helper = IabHelper(c, k)
        # prints a lot of useful messages that might
        # not make it back to python space
        helper.enableDebugLogging(True)
        self._setup()

    # Bound in _setup_callback to activity.on_activity_result
    def _on_activity_result(self, requestCode, responseCode, Intent):
        Logger.info('Request Code: ' + str(requestCode))
        Logger.info('Expected Code: ' + str(self.r_code))
        Logger.info('Response Code: ' + str(type(Intent)))
        if requestCode == self.r_code:
            Logger.info('Passing result to helper')
            if self.helper.handleActivityResult(requestCode, responseCode, Intent):
                Logger.info('Helper completed the request.')
                # here we go the long way around and get the inventory
                # this is a workaround due to _purchase_finished failing at the 
                # point of invocation inside IabHelper.java around line 425
                self._get_inventory(None)
                return True
            else:
                Logger.info('Letting the result/event propogate')
    
    def _setup(self, *args):
        Logger.info('Attempting to start the helper')
        s = _OnIabSetupFinishedListener(self._setup_callback)
        self.helper.startSetup(s)
        Logger.info('Startup process underway')
        
        # ugly way of detecting crashes in the helper that don't call back
        def try_again(*args):
            if not self._inventory_checked:
                Logger.info('Inventory wasn\'t checked after 5 second.  Starting over')
                self._dispose()
                Clock.schedule_once(self._setup)
        Clock.schedule_once(try_again, 5.0)

    @run_on_ui_thread
    def _setup_callback(self, result):
        # setup frequently fails with a jnius error.
        # I/python  (15570):  Exception AttributeError: "'ObservableReferenceList' object has no attribute 'invoke'" in 'jnius.jnius.invoke0' ignored
        # so let's have a buy_waiting list to determine if we need to buy things
        # after setup.  Perform the actual buy after the inventory check has completed
        # and consumed all products inside _consume_finished
        Logger.info('Setup complete. Scheduling inventory check')
        if result.isSuccess():
            a = App.get_running_app()
            a.bind(on_stop=self._dispose)
            activity.bind(on_activity_result=self._on_activity_result)
            # can we also do this with properties?
            Clock.schedule_once(self._get_inventory, 0)
        else:
            self._dispose()
            self._setup()
            
    @run_on_ui_thread
    def _get_inventory(self, *args):
        Logger.info('Getting Inventory')
        q = _QueryInventoryFinishedListener(self._got_inventory_callback)
        self.helper.queryInventoryAsync(q)

    @run_on_ui_thread
    def _got_inventory_callback(self, result, inventory):
        Logger.info('Got Inventory')
        # at this point, it seems like things will be working, so allow buy
        self._inventory_checked = True
        if result.isSuccess():
            if len(self._buy_waiting):
                self.buy(self._buy_waiting.pop())
            # can we also do this with property listening?
            # self.new_inventory = True
            else:
                self.inventory = inventory
                for s in self.skus:
                    Logger.info('Checking for ' + s + ' in the inventory')
                    purchases = list()
                    if inventory.hasPurchase(s):
                        purchases.append(inventory.getPurchase(s))
                        Logger.info(s + ' is ready for consumption')
                    if len(purchases):
                        Clock.schedule_once(self._new_inventory, 0)
                        self.purchases = purchases
            if DEBUG:
                # refresh products list
                # until the inventory is used to build the list
                # a known list of product skus must be used
                self.products = self.skus

    def _new_inventory(self, *args):
        if len(self.purchases):
            Logger.info('We have the products in the warehouse. Let\' consume one!')
            p = self.purchases[0]
            self._consume(p)

    def buy(self, sku):
        if sku not in self.products:
            raise AttributeError('The product is not in the available products List')
        if not self._inventory_checked:
            Logger.info('Couldn\'t check inventory...  Re-doing.  Buy later after inventory workflow')
            self._dispose()
            self._buy_waiting.append(sku)
            self._setup()
        else:
            Logger.info('Starting purchase workflow for ' + sku)
            c = cast('android.app.Activity', context)
            # arbitrary request code for this purchase flow
            # IabHelper compares activity result codes with 
            # an internal result code variable to somewhat verify
            # that the acitivity result is intended for it
            r = self.r_code
            # note, onPurchaseFinishedListener is never called due to
            # workaround.  See IabHelper.java commented lines in handleActivityResult
            p = _OnPurchaseFinishedListener(self._purchase_finished)
            self.helper.launchPurchaseFlow(c, sku, r, p)

    @run_on_ui_thread
    def _purchase_finished(self, result, purchase):
        Logger.info('Result was ' + str(result.isSuccess()) + ' for ' + purchase.getSku())
        if result.isSuccess():
            self._consume(purchase)

    @run_on_ui_thread
    def _consume(self, purchase):
        Logger.info('Consuming ' + purchase.getSku())
        c = _OnConsumeFinishedListener(self._consume_finished)
        self.helper.consumeAsync(purchase, c)

    @run_on_ui_thread
    def _consume_finished(self, purchase, result):
        if result.isSuccess():
            s = purchase.getSku()
            if self.consumed.has_key(s):
                self.consumed[s] += 1
            else:
                self.consumed[s] = 1
            Logger.info(s + ' was successfully purchased.  Time to get rich!')
            self.purchases.remove(self.purchases[0])
            self._new_inventory()
                    
    def _dispose(self, *args):
        self.helper.dispose()
