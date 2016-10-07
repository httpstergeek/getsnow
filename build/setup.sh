#!/usr/bin/env bash

BASEDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )
FILENAME_BASE=${BASEDIR##*/}

echo $(pip install --prefix=${BASEDIR}/bin  'splunk-sdk==1.6.0' )
$(mv "${BASEDIR}/bin/lib/python2.7/site-packages/splunklib" "${BASEDIR}/bin")
$(rm -rf "${BASEDIR}/bin/lib")