#!/bin/sh
#
# This script fetches the object signing list from the Microsoft list. It then
# mergest that list into the fetched certdata.txt.
#
#baseurl="https://ccadb-public.secure.force.com/microsoft/IncludedRootsPEMTxtForMSFT?TrustBitsInclude=Code%20Signing"
#target="microsoft_code_siging.pem"
baseurl="https://gist.githubusercontent.com/richlander/800fcac88d595cea225649b76a5361f4/raw/f7f340ec81e81503a6518d0fbb701ff978dc87bd/"
target="codesignctl.pem"
certdata="./certdata.txt"
merge=1
diff=0
while [ -n "$1" ]; do
   case $1 in
   "-u")
        shift
	baseurl=$1
	;;
   "-o")
        shift
	target=$1
	;;
   "-c")
        shift
	certdata=$1
	;;
   "-n")
        merge=0
        ;;
   "-d")
        diff=1
        difffile=$1
        ;;
    *)
	echo "usage: $0 [-u URL] [-o target] [-c certdata] [-n]"
	echo "-u URL      base URL to fetch code signing list"
	echo "-o target   name of the codesigning target"
	echo "-c certdata patch to certdata.txt to merge with"
	echo "-d diff     optional diff file"
        echo "-n          don't merge"
	exit 1
	;;
    esac
    shift
done


wget ${baseurl} -O ${target}

if [ ${merge} -eq 0 ]; then
    exit 0;
fi

out=${certdata}
if [ ${diff} -eq 1 ]; then
   out=${certdata}.out
fi

python3 ./mergepem2certdata.py -c "${certdata}" -p "${target}" -o "${out}" -t "CKA_TRUST_CODE_SIGNING" -l "Microsoft Code Signing Only Certificate"

if [ ${diff} -eq 1 ]; then
    diff -u ${certdata} ${out} > ${difffile}
    mv ${out} ${certdata}
fi
