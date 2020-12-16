const fs = require("fs");
const path = require("path");
const fetch = require("node-fetch");
const turf = require("@turf/turf");
const createThrottle = require("async-throttle");
const throttle = createThrottle(4);

const cacache = require("cacache/en");
const ipLocsCachePath = "/tmp/iplocs-cache";
const probeLocsCachePath = "/tmp/probeslocs-cache";

const resolveIpLocMap = ipSet =>
    ipSet.map(ip =>
        cacache.get(ipLocsCachePath, ip).then(
            cachedIp => {
                process.stdout.write(`R ${ip} - `);
                return JSON.parse(cachedIp.data);
            },
            _ =>
                throttle(async () => {
                    process.stdout.write("F");
                    return await fetch(
                        `https://ipmap-api.ripe.net/v1/locate/${ip}/partials`,
                        {
                            method: "GET",
                            headers: {
                                "Content-Type": "application/json"
                            }
                        }
                    )
                        .then(
                            d => d.json(),
                            err => {
                                console.err(err);
                            }
                        )
                        .then(
                            d => {
                                process.stdout.write(`W ${ip} -> `);
                                // console.log(ipLocsCachePath);
                                if (!d.partials) {
                                    console.err("incorrect ipmap answer");
                                    console.err(d);
                                    console.err("----");
                                }
                                const location =
                                    (d.partials.find(
                                        e => e.engine === "crowdsourced"
                                    ).locations &&
                                        d.partials.find(
                                            e => e.engine === "crowdsourced"
                                        ).locations[0]) ||
                                    (d.partials.find(
                                        e => e.engine === "single-radius"
                                    ).locations &&
                                        d.partials.find(
                                            e => e.engine === "single-radius"
                                        ).locations[0]);
                                process.stdout.write(`${location.id}\n`);
                                return cacache.put(
                                    ipLocsCachePath,
                                    ip,
                                    JSON.stringify({
                                        ip: ip,
                                        location: location
                                    })
                                );
                            },
                            err => {
                                console.log(err);
                            }
                        );
                })
        )
    );

const resolveProbesLoc = async prbIdSet => {
    let uncachedPrbIdSet = [];

    // go over the cache for all probes
    const cachedProbesLocs = prbIdSet.map(prbId => {
        return cacache.get(probeLocsCachePath, String(prbId)).then(
            cachedPrb => {
                process.stdout.write(`!R ${prbId} - `);
                return JSON.parse(cachedPrb.data);
            },
            _ => {
                process.stdout.write(`M ${prbId}`);
                if (prbId) {
                    uncachedPrbIdSet.push(prbId);
                } else {
                    console.error(
                        "\nundefined prbId in cached probes. Cannot continue. Probably you want to delete the cache and start over."
                    );
                    process.exit(1);
                }

                // return prbId;
            }
        );
    });

    // resolve all the cached probes then and....
    return Promise.all(cachedProbesLocs).then(async _ => {
        // all the probes are already in the cache,
        // return the data from the cache and be
        // done with it.
        if (uncachedPrbIdSet.length === 0) {
            console.log("all probes cached");
            return cachedProbesLocs;
        } else {
            // download the coordinates for all uncached probes
            const probesFetchUrl = `https://atlas.ripe.net/api/v2/probes/?id__in=${uncachedPrbIdSet.join(
                ","
            )}&fields=geometry`;
            // console.log(uncachedPrbIdSet);
            // console.log(probesFetchUrl);
            const probeGeomReq = await fetch(probesFetchUrl);

            const probesAPI = await probeGeomReq.json();

            //...go over all the probes to create
            // the complete array of both cached *and* uncached probes
            return prbIdSet.map(prbId =>
                cacache.get(probeLocsCachePath, String(prbId)).then(
                    cachedPrb => {
                        process.stdout.write(`!R ${prbId} - `);
                        return JSON.parse(cachedPrb.data);
                    },
                    _ =>
                        throttle(async () => {
                            process.stdout.write(`!F ${prbId} - `);
                            const p = probesAPI.results.find(
                                pp => pp.id === prbId
                            );
                            const coords = p.geometry.coordinates;
                            return await fetch(
                                `https://ipmap-api.ripe.net/v1/worlds/reverse/${
                                    coords[1]
                                }/${coords[0]}`
                            )
                                .then(d => d.json())
                                .then(d => {
                                    process.stdout.write(
                                        `!W ${p.id} - ${d.locations[0]} - `
                                    );
                                    const cacheData = {
                                        prbId: p.id,
                                        location: d.locations[0]
                                    };
                                    cacache.put(
                                        probeLocsCachePath,
                                        String(p.id),
                                        JSON.stringify(cacheData)
                                    );
                                    return cacheData;
                                });
                        })
                )
            );
        }
    });
};

const prettyPrintLocation = location =>
    `${l.location.cityName}, ${l.location.stateName}, ${l.location.countryName}`;

const debugPrint = s => {
    // just for printing
    // console.log(s.properties.locationString);
    // console.log(s.properties.hops);
    s.properties.hops.map(l => {
        const location = s.properties.locationString.find(
            ll => (l.prbId && ll.prbId === l.prbId) || (l.ip && ll.ip === l.ip)
        );
        console.log(
            `${(l.ip && l.ip) ||
                (l.prbId && `Probe ${l.prbId}`)} -> ${(location &&
                location.locationId) ||
                "no ip (*)"}`
        );
    });
    process.stdout.write("location String : ");
    s.properties.locationString.map((h, i) => {
        process.stdout.write(
            `${h.locationId || "noloc"}${(i <
                s.properties.locationString.length - 1 &&
                " -> ") ||
                "\n"}`
        );
    });
    console.log(`pathLength : ${s.properties.pathLength}`);
};

const EmilesGeoLoc = rp => {
    console.log("------");
    console.log("Emile's dataset");
    console.log(
        rp.geojson.reduce((locs, g) => {
            locs = locs.concat(
                ` -> ${(g.properties.sloc !== "Probe" && g.properties.sloc) ||
                    `Probe ${rp.dst_prb_id}`}`
            );
            return locs;
        }, "")
    );
    console.log("-----");
};

const createIpLocMap = msmResults => {
    const probesIds = Array.from(
        new Set(
            msmResults
                .flatMap(r => r)
                .flatMap(rp => [rp.dst_prb_id, rp.src_prb_id])
        )
    );

    const ipSet = Array.from(
        new Set(
            msmResults
                .flatMap(r => r)
                .reduce((ipArr, data) => {
                    const ipInnerArr = Array.from(
                        new Set(
                            data.result.reduce((ips, r) => {
                                if (!r.result) {
                                    console.log(r);
                                }
                                ips =
                                    (r.result &&
                                        ips.concat(
                                            Array.from(
                                                new Set(
                                                    r.result.map(h => h.from)
                                                )
                                            ).filter(
                                                i =>
                                                    i &&
                                                    !(
                                                        i.split(".")[0] ===
                                                            "192" &&
                                                        i.split(".")[1] ===
                                                            "168"
                                                    ) &&
                                                    !(
                                                        i.split(".")[0] === "10"
                                                    ) &&
                                                    !(
                                                        i.split(".")[0] ===
                                                            "169" &&
                                                        i.split(".")[1] ===
                                                            "254"
                                                    ) &&
                                                    !(
                                                        i.split(".")[0] ===
                                                            "172" &&
                                                        i.split(".")[1] >= 16 &&
                                                        i.split(".")[1] <= 31
                                                    )
                                            )
                                        )) ||
                                    ips;
                                return ips;
                            }, [])
                        )
                    );
                    ipArr = ipArr.concat(ipInnerArr);
                    return ipArr;
                }, [])
        )
    );

    const ipLocMap = resolveIpLocMap(ipSet);
    return resolveProbesLoc(probesIds).then(pm => {
        return Promise.allSettled([...ipLocMap, pm]);
    });
};

const createLineStrings = (rawPaths, ipLocs) => {
    console.log(`measurement file ${rawPaths[0].msm_id}`);
    return rawPaths.map((rp, i) => {
        // console.log(ipLocs.filter(l => l.prbId));
        // console.log(ipLocs.find(prb => prb.prbId === rp.src_prb_id));

        const prbSrcLoc = ipLocs.find(prb => prb.prbId === rp.src_prb_id)
            .location;
        const prbDstLoc = ipLocs.find(prb => prb.prbId === rp.dst_prb_id)
            .location;

        const string = [
            {
                ip: null,
                prbId: rp.src_prb_id,
                location: prbSrcLoc
            }
        ]
            .concat(
                (rp.result &&
                    rp.result
                        .map(r => {
                            if (!r.result) {
                                console.error(r);
                                return null;
                            }
                            const ip = Array.from(
                                new Set(
                                    r.result.map(h => h.from).filter(f => f)
                                )
                            )[0];
                            const location = (ip &&
                                ipLocs.find(l => l.ip === ip)) || {
                                location: null
                            };
                            return {
                                ip: ip || null,
                                location: location.location
                            };
                        })
                        .filter(l => l)) ||
                    []
            )
            .concat({
                ip: null,
                prbId: rp.dst_prb_id,
                location: prbDstLoc
            });
        const locsString = string.filter(
            h => h.location && h.location.longitude
        );
        return {
            type: "Feature",
            geometry: {
                type: "LineString",
                coordinates: locsString.map(l => [
                    l.location.longitude,
                    l.location.latitude
                ])
            },
            properties: {
                dst_prb_id: rp.dst_prb_id,
                src_prb_id: rp.src_prb_id,
                idx: i,
                hops: string.map(
                    l => (l.ip && { ip: l.ip }) || { prbId: l.prbId }
                ),
                locationString: locsString.map(l => ({
                    locationId: l.location.id,
                    ip: l.ip,
                    prbId: l.prbId
                })),
                farthestLocation: locsString.reduce(
                    ([fLoc, dist], hop) => {
                        const hopDist = turf.distance(
                            [
                                locsString[0].location.longitude,
                                locsString[0].location.latitude
                            ],
                            [hop.location.longitude, hop.location.latitude]
                        );

                        if (hopDist > dist) {
                            fLoc = hop.location.id;
                            dist = hopDist;
                        }

                        return [fLoc, dist];
                    },
                    [locsString[0].location.id, 0]
                ),
                pathLength: locsString.reduce((pathLength, hop, idx) => {
                    stringLength =
                        (locsString[idx + 1] &&
                            turf.distance(
                                [hop.location.longitude, hop.location.latitude],
                                [
                                    locsString[idx + 1].location.longitude,
                                    locsString[idx + 1].location.latitude
                                ]
                            )) ||
                        0;
                    return pathLength + stringLength;
                }, 0)
            }
        };
    });
};

//main

const msmResults = fs
    .readdirSync("./")
    .filter(fN => fN.split(".")[0] === "msm")
    .reduce((results, f) => {
        results.push(JSON.parse(fs.readFileSync(f)));
        return results;
    }, []);

const filePrefix = path.resolve("./").split("/")[
    path.resolve("./").split("/").length - 1
];

// move and wipe file if exists, otherwise create empty one.
try {
    fs.renameSync(
        `${filePrefix}.linestrings.geo.json`,
        `${filePrefix}.linestrings.geo.json.old`
    );
} catch {
    console.log("no old linestrings geojson file. creating...");
}

createIpLocMap(msmResults).then(p => {
    const buf = {
        geo: { type: "FeatureCollection", features: [] },
        locations: []
    };
    const ipLocs = p.filter(p => p.status === "fulfilled").map(p => p.value);

    Promise.allSettled(p[p.length - 1].value).then(p => {
        const probesLocs = p
            .filter(pp => pp.status === "fulfilled")
            .map(pp => pp.value);

        buf.locations = [
            ...probesLocs.map(pl => pl.location),
            ...ipLocs.map(pl => pl.location)
        ].reduce((set, loc) => {
            if (loc && !set.some(l => l.id === loc.id)) {
                set.push(loc);
            }
            return set;
        }, []);

        msmResults.forEach(r => {
            lineStrings = createLineStrings(r, [...ipLocs, ...probesLocs]);
            buf.geo.features = buf.geo.features.concat(lineStrings);
            lineStrings.forEach(s => {
                debugPrint(s);
                EmilesGeoLoc(r[s.properties.idx]);
            });
        });

        fs.writeFileSync(
            `${filePrefix}.linestrings.geo.json`,
            JSON.stringify(buf)
        );
    });
});
