from kivy import platform

__all__ = ('Billing',)

if platform() == 'android':
    from androidbilling import AndroidBilling as Billing
else:
    from mockbilling import MockBilling as Billing
