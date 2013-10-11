#In-App Billing v3 PyJNIus Module

Buy things from Kivy apps on Android.

###Features
* Checks for network, prompts user and has hooks to implement your own prompts.  
* Automatically set itself up and check inventory and buy products automatically with a configureable time.  
* Alternatively, will setup when user makes a purchase.  Will not interfere with automatic setup.
* Has `purchased` property to capture purchase consumptions.  Times out and has hook to prompt for retry.

###License
Some code in Trivial Drive java classes (for Base64.java) has strange license.  Most of the Java classes are Apache2 from Android SDK.  This code is MIT

###Goal
PyJNIus implementation of billing.  Has Kivy as dependency.  You like Kivy.

###External Java Code
Uses Android Trivial Drive java classes mostly unmodified.  The IabHelper class provides most of the API used in androidbilling.py.  

###Status
Going straight into some production code  If something is broken, file bug.  Post logcat preferably.

###Todo
Want callbacks?  Saving data?  My Twitter example uses both of these.

###Mock Module
Please maintain any API changes in the mock module so that developers can test locally.  The method of import I don't care about.

##Building (Advise using fresh P4A dist)
1.  link the src/org/kivy directory to your P4A src/ directory `ln -s src/org/kivy ~/mydist/src/org/kivy`
2.  add the billing permission to mydist/templates/AndroidManifest.tmpl.xml.  See AndroidManifest.extras.xml
3.  use the billing.sh inside your dist/mydist with `./billing.sh ~/my/cloned/billing`