#!/bin/bash
# Invokes build.py script appropriately for testing
if [[ -z $1 ]]
then
    echo "You need to supply the sample directory as the first argument"
    exit
fi
#debug
./build.py --package org.kivy.billing_sample --version 0.1 --orientation landscape --name "Kivy Billing Sample" --dir $1 --permission INTERNET debug installd
#release
#./build.py --package org.kivy.billing_sample --version 0.1 --orientation landscape --name "Kivy Billing Sample" --dir $1 --permission INTERNET release && echo "don't forget to sign"
