#!/bin/bash
CUR_DIR="${pwd}"
myv=`curl -s http://localhost:9999/blazegraph/sparql?query=SELECT%20%3Fs%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201`

if [ -z "$myv" ] || [[ $myv != *"results"* ]];
then
    ./stop.sh
    cd ..
    java -server -Xmx1g -Dbigdata.propertyFile=occ.properties -Djetty.port=9999 -Djetty.host=127.0.0.1 -jar blazegraph.jar &
    cd $CUR_DIR
    exit 0
fi

cd $CUR_DIR
exit 1