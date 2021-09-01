# Misc

This file/directory has various partly implemented ideas

# doit-country-pairs.py

This explores the idea of measuring between 2 neighboring countries (idea by
Hisham Ibrahim during a RIPE NCC Hackathon)
Uses a geonames API call to get neighbor countries

# get-ips.py improvements

As traceroutes contain IPv4-mapped IPv6 addresses I've been playing with
actually getting the hostname/ASN for the mapped address. To do that you
will have to extract the IPv4 address out, and only after that do the lookups:

```
    for ip in ips:
            if ip[:7] == "::ffff:":
                    ip = ip[7:]
```

Didn't put this live yet, as it may not be strictly correct to do this.



