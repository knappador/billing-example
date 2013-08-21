from kivy import platform

Billing = None

if platform() == 'android':
    from androidbilling import AndroidBilling
    Billing = AndroidBilling
else:
    from mockbilling import MockBilling
    Billing = MockBilling
