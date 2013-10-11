from kivy.app import App
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.properties import DictProperty
from kivy.logger import Logger

import netcheck
import toast

from jnius import autoclass, PythonJavaClass, java_method, cast
from android import activity

from functools import partial

context = autoclass('org.renpy.android.PythonActivity').mActivity
IabHelper = autoclass('org.kivy.billing.IabHelper')
IabResults = autoclass('org.kivy.billing.IabResult')
Inventory = autoclass('org.kivy.billing.Inventory')
Purchase = autoclass('org.kivy.billing.Purchase')

''' There is a big difference between the twitter module.  All twitter
callbacks return through one listener that implements an interface.  There 
are many fewer places where an object can call back from Java to an object that
was already CG'd in Python.  Either sync the Python GC and Java GC or be sure 
to follow the Twitter4J style all-in-one listener architecture when implementing 
Java objects.  This is my advice for writing PyJNIus integrations for now.

Since every callback is it's own object here and there is no error callback, 
every callback has to be stored in _refs to keep it alive when it goes out of 
the scope where it was created '''

# constants
TIMEOUT = 120.0 # seconds to either succeed or fail
#implement save if you purchase (and consume) things without
#using them.  Alternatively implement the inventory without
#consuming items until the user uses them.
#SAVE_PATH = './billing.json'
DEBUG=True
# since our callbacks from Java don't keep their Python
# from getting GC'd, we have to keep refs
_refs = []

# we remove refs when they are called to allow gc
def _allow_gc(fn):
    def checked(self, *args, **kwargs):
            fn(self, *args, **kwargs)
            _refs.remove(self)
    return checked

def _protect_callback(new_callback):
    '''increment counter and attach to new callback object'''
    _refs.append(new_callback)


# Java callbacks that call back into the provided Python callbacks
class _OnIabSetupFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$OnIabSetupFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_OnIabSetupFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/IabResult;)V')
    @_allow_gc
    def onIabSetupFinished(self, result):
        self.callback(result)


class _QueryInventoryFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$QueryInventoryFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_QueryInventoryFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/IabResult;Lorg/kivy/billing/Inventory;)V')
    @_allow_gc
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
    @_allow_gc
    def onIabPurchaseFinished(self, result, purchase):
        self.callback(result, purchase)

class _OnConsumeFinishedListener(PythonJavaClass):
    __javainterfaces__ = ['org.kivy.billing.IabHelper$OnConsumeFinishedListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_OnConsumeFinishedListener, self).__init__()

    @java_method('(Lorg/kivy/billing/Purchase;Lorg/kivy/billing/IabResult;)V')
    @_allow_gc
    def onConsumeFinished(self, purchase, result):
        self.callback(purchase, result)


class AndroidBilling(EventDispatcher):
    consumed = DictProperty()

    def __init__(self, 
                 app_public_key, 
                 skus, 
                 auto_check_inventory=10,
                 toasty=True,
                 **kwargs):
        self.app_public_key = app_public_key        
        self.skus = skus
        self.toasty = toasty
        # This shouldn't collide, but I will pay you $2 if it does 
        # for the first occurrence ever.  After that, you should fix
        # the code to something more unique =)
        self.r_code = abs(hash('org.kivy.billing'))
        
        # interal state initialize
        self.purchase_requested = None
        self.syncing = False
        self.setup_complete = False
        self.error_msg = 'there was an error'
        
        if auto_check_inventory >= 0:
            Clock.schedule_once(self._setup, auto_check_inventory)

    def purchase(self, sku):
        # Really need to move these debug settings to a global 
        # settings file. Oh and they say that global settings files are bad.
        # Let's get to the bottom of it.
        if DEBUG:
            self.debug_sku = sku
            sku = 'android.test.purchased'
            if sku not in self.skus:
                self.skus.append(sku)
            Logger.warning('IAB is running in DEBUG mode and won\'t buy anything!')
        if self.purchase_requested is not None:
            self._toast('purchase already in progress')
            return False
        elif self.syncing:
            self.purchase_requested = sku
            Clock.schedule_once(self._fail, TIMEOUT)
            self._toast('will start purchase shortly')
            return True
        else:
            Logger.info('Purchasing ' + sku)
            if not self.setup_complete:
                self._toast('will start purchase shortly')
            else:
                self._toast('purchase started')
            self.purchase_requested = sku
            Clock.schedule_once(self._fail, TIMEOUT)
            self._process_purchase()
            return True
            
    def retry_prompt(self, callback):
        ''' Monkey patch here to implement a real prompt'''
        callback(False)

    def set_retry_prompt(self, fn):
        ''' Or use this handy public setter if you really like Java.'''
        self.retry_prompt = fn

    #################
    # Private Methods
    #################

    # Bound in _setup_callback to activity.on_activity_result
    def _on_activity_result(self, requestCode, responseCode, Intent):
        if DEBUG:
            Logger.info('Request Code: ' + str(requestCode))
            Logger.info('Expected Code: ' + str(self.r_code))
        if requestCode == self.r_code:
            Logger.info('Passing result to IAB helper')
            if self.helper.handleActivityResult(requestCode, responseCode, Intent):
                Logger.info('Helper completed the request.')
                self._get_inventory()
            return True
    
    def _setup(self, *args):
        Clock.unschedule(self._setup)
        if not self.syncing and not \
           (hasattr(self, 'helper') and self.helper.mSetupDone) and \
           netcheck.connection_available():
            self.syncing = True
            Logger.info('Attempting startup')
            k = self.app_public_key
            c = cast('android.app.Activity', context)
            self.helper = helper = IabHelper(c, k)
            # prints a lot of useful messages that might
            # not make it back to python space
            helper.enableDebugLogging(DEBUG)
            s = _OnIabSetupFinishedListener(self._setup_callback)
            _protect_callback(s)
            self.helper.startSetup(s)

    def _setup_callback(self, result):
        if result.isSuccess() and self.helper.mSetupDone:
            Logger.info('Setup complete. Scheduling inventory check')
            self.setup_complete = True
            a = App.get_running_app()
            a.bind(on_stop=self._dispose)
            activity.bind(on_activity_result=self._on_activity_result)
            self._get_inventory()
        else:
            Logger.info('There was a problem with setup')
            self.error_msg = 'could not connect to play store'
            self._fail()
            
    def _get_inventory(self, *args):
        Logger.info('Getting Inventory')
        q = _QueryInventoryFinishedListener(self._got_inventory_callback)
        _protect_callback(q)
        self.helper.queryInventoryAsync(q)

    def _got_inventory_callback(self, result, inventory):
        if result.isSuccess():
            Logger.info('Got Inventory')
            self.inventory = inventory
            # Inventory has some map methods that might be slightly more 
            # straightforward but this is fast already
            purchases = list()
            for s in self.skus:
                Logger.info('Checking for ' + s + ' in the inventory')
                if inventory.hasPurchase(s):
                    purchases.append(inventory.getPurchase(s))
                    Logger.info(s + ' is ready for consumption')
            self.purchases = purchases
            if len(self.purchases):
                self.syncing = True
            else:
                self.syncing = False
                self.inventory_checked = True
            self._process_inventory()
        else:
            self.error_msg = 'Could not check inventory'
            self._fail()

    def _process_purchase(self):
        Logger.info('in purchase')
        if not netcheck.connection_available():
            Logger.info('no net avaiable')
            netcheck.ask_connect(self._connection_callback)
        elif not self.setup_complete:
            Logger.info('setup not complete')
            self._setup()
        else:
            Logger.info('doing the purchase')
            Logger.info(str(self.purchase_requested))
            if self.purchase_requested is not None:
                sku = self.purchasing = self.purchase_requested
            else:
                self.purchasing = self.purchase_requested = None
                Logger.info('returning for no good reason')
                return
            if sku not in self.skus:
                raise AttributeError('The sku is not in the skus you initialized with')
            Logger.info('Starting purchase workflow for ' + sku)
            c = cast('android.app.Activity', context)
            r = self.r_code
            p = _OnPurchaseFinishedListener(self._purchase_finished)
            _protect_callback(p)
            self.helper.launchPurchaseFlow(c, sku, r, p)

    def _purchase_finished(self, result, purchase):
        Logger.info('Result was ' + str(result.isSuccess()) + ' for ' + 
                    purchase.getSku())
        if result.isSuccess():
            self._consume(purchase)

    def _process_inventory(self):
        if len(self.purchases):
            self._consume(self.purchases[0])
        else:
            # if we're done with inventory, we go back to purchasing
            self._process_purchase()

    def _consume(self, purchase):
        Logger.info('Consuming ' + purchase.getSku())
        c = _OnConsumeFinishedListener(self._consume_finished)
        _protect_callback(c)
        self.helper.consumeAsync(purchase, c)

    def _consume_finished(self, purchase, result):
        try:
            s = str(purchase.getSku())
        except:
            s = 'unknown sku'
        if result.isSuccess():
            if DEBUG:
                s = self.debug_sku
                # Since we are faking the sku passed in for debug mode,
                # there's no way to know if the consumption happened -really- 
                # for purchase.getSku() or for debug_sku. The information 
                # is gone.  It's in the air.  You can never capture it again.
                self.purchase_requested = None
                Clock.unschedule(self._fail)
            self.consumed[s] = self.consumed.get(s, 0) + 1
            Logger.info(s + ' was successfully purchased.  Time to get rich!')
            self.purchases.remove(purchase)
            if s == self.purchase_requested:
                self.purchase_requested = None
                Clock.unschedule(self._fail)
            self._process_inventory
        else:
            Logger.info('There was a problem consuming ' + s)
            self._fail()

    ######################################
    # Managing timeouts and retry workflow
    ######################################

    def _fail(self, *args):
        Clock.unschedule(self._fail)
        # since the setup and everything in between can fail,
        # we don't want to prompt the user for background stuff
        if self.purchase_requested is not None:
            self._toast(self.error_msg)
            self._ask_retry()

    def _retry_callback(self, retry):
        if retry:
            self._process_purchase()
        else:
            self._processing=False
            self._purchase_requested = None
            self._tries = 0

    def _ask_retry(self):
        self.retry_prompt(self._retry_callback)

    def _connection_callback(self, connected):
        Logger.info('in billing connection callback: ' + str(connected))
        if connected:
            self._process_purchase()
        else:
            self._fail()

    def _dispose(self, *args):
        ''' Let all callbacks be GC'd and destroy helper'''
        self.helper.dispose()
        global _refs
        _refs = []

    def _toast(self, text, length_long=False):
        if self.toasty:
            toast.toast(text, length_long)
