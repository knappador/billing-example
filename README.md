#In-App Billing v3 PyJNIus Module

##Goal
Old Billing uses JNI and Cython.  It was based on API v2 and cannot consume purchases.  This one aims to be more maintainable and expose more API.

##Overview
Uses Android Trivial Drive example code mostly unused.  The IabHelper class provides most of the API used in androidbilling.py.  

##Status
Installs as-is with debug key and can make a purchase.  Every purchase is automatically consumed and a button shows up on the UI. This code is based on **production code in the middle of cleaning up**.  You can use this code with minor work in a real app.  It's really ugly.

##Todo
Most immediately, the PyJNIus warnings, Dalkvik auto-correcting errors, and the error that happens in purchase callback need to be taken care of.  The code can't be made clean if the result doesn't work.

##Mock Module
Please maintain any API changes in the mock module so that developers can test locally.  The method of import I don't care about.

#Building (Advise using fresh P4A dist)
1.  link the src directory to your P4A src directory `ln -s src ~/my/cloned/billing/src`
2.  copy AndroidManifest over
3.  use the billing_build.sh from `billing/script` from inside the dist.  `./billing_build.sh ~/my/cloned/billing`

Obviously I want to fix a lot of things and impement a more useful API, but the PyJNIus useage might not be correct yet.  That's a good place to start.
