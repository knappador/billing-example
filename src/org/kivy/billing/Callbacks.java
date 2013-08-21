package org.kivy.billing;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.ImageView;
//import org.kivy.billing.R;
import org.kivy.billing.IabHelper;
import org.kivy.billing.IabResult;
import org.kivy.billing.Inventory;
import org.kivy.billing.Purchase;


public class Callbacks{
    public Inventory mInventory;
    // Listener that's called when we finish querying the items we own
    public IabHelper.QueryInventoryFinishedListener mGotInventoryListener = new IabHelper.QueryInventoryFinishedListener() {
        public void onQueryInventoryFinished(IabResult result, Inventory inventory) {
            /*
            Log.d(TAG, "Query inventory finished.");
            if (result.isFailure()) {
                complain("Failed to query inventory: " + result);
                return;
            }

            Log.d(TAG, "Query inventory was successful.");

            // Do we have the premium upgrade?
            mIsPremium = inventory.hasPurchase(SKU_PREMIUM);
            Log.d(TAG, "User is " + (mIsPremium ? "PREMIUM" : "NOT PREMIUM"));

            // Check for gas delivery -- if we own gas, we should fill up the tank immediately
            if (inventory.hasPurchase(SKU_GAS)) {
                Log.d(TAG, "We have gas. Consuming it.");
                mHelper.consumeAsync(inventory.getPurchase(SKU_GAS), mConsumeFinishedListener);
                return;
            }

            updateUi();
            setWaitScreen(false);
            Log.d(TAG, "Initial inventory query finished; enabling main UI."); */
            mInventory = inventory;
        }
    };
}
