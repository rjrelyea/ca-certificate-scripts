#/bin/sh
verbose=1
 if [ "$1" = "-q" ]; then
   verbose=0;
 fi
 rm -f neutral
 rm -f info.trust
 rm -f info.distrust
 rm -f info.notrust
 rm -f trusted_all_bundle
 touch neutral
 for f in certs/*.crt; do 
   if [ ${verbose} -eq 1 ]; then
       echo "processing $f"
   fi
   tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
   distbits=`sed -n '/^# openssl-distrust/{s/^.*=//;p;}' $f`
   alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
   targs=""
   if [ -n "$tbits" ]; then
      for t in $tbits; do
         targs="${targs} -addtrust $t"
      done
      echo "trust flags $targs for $f" >> info.trust
      #openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> trusted_all_bundle
      openssl x509 -text -fingerprint -md5 -in "$f" >> trusted_all_bundle
   fi
   if [ -n "$distbits" ]; then
      for t in $distbits; do
         targs="${targs} -addreject $t"
      done
      echo "disttrust flags $targs for $f" >> info.distrust
   fi

   if [ -z "$targs" ]; then
      echo "no trust flags for $f" >> info.notrust
      # p11-kit-trust defines empty trust lists as "rejected for all purposes".
      # That's why we use the simple file format
      #   (BEGIN CERTIFICATE, no trust information)
      # because p11-kit-trust will treat it as a certificate with neutral trust.
      # This means we cannot use the -setalias feature for neutral trust certs.
      openssl x509 -text -fingerprint -md5 -in "$f" >> neutral
   fi
 done
