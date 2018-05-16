import React from "react";

import { Legend } from "../components/legend.jsx";
import { SmallGraphs } from "../components/ui-elements/flexbox";
import { PeerToPeerDialog } from "../components/dialogs/peertopeerdialog.jsx";
import { PeerToPeerFabricGraph } from "../components/graphs/fabric.jsx";
import OtherCountries from "../../texts/other-countries.md";
import PeerToPeerStoryText from "../../texts/ptp-story.md";
import { SnapShotTimeLine } from "../components/ui-elements/timeline";
import {
  ExplainCircle1,
  ExplainCircle2,
  ExplainCircle3,
  ExplainSmallCircles1,
  ExplainSmallCircles2,
  ExplainSmallCircles3,
  ExplainLines1,
  ExplainLines2,
  ExplainLines3
} from "../components/explanations.jsx";

const countryGeoInfoUrl = "./world-geo150_ne50m.topo.json";
const primaryFromUrl = () =>
  window.location.pathname.match(
    /([a-zA-Z]{2})[\/\-]([0-9]{4})[\/\-]([0-9]{2})[\/\-]([0-9]{2})/
  );

export class PeerToPeerContainer extends React.Component {
  constructor(props) {
    super(props);
    this.state = { currentSnapshotDate: null };
  }

  destructureCountryInfoFromUrl = () => {
    const paths = primaryFromUrl() || null;
    return (paths && paths.slice(1, 6)) || [null, null, null, null];
    // console.log({
    //     countryCode,
    //     year,
    //     month,
    //     day
    //   })
    // return {
    //   countryCode,
    //   year,
    //   month,
    //   day
    // };
  };

  loadCountryGeoInfo = async countryGeoInfoUrl => {
    let response = await fetch(countryGeoInfoUrl);
    let data = await response.json();
    return data.objects;
  };

  loadAs2OrgNames = async nodes => {
    const fetchUrl = "./as2org.json";
    let response = await fetch(fetchUrl);
    let orgNames = await response.json();
    return orgNames;
  };

  whatsMyGeoLocation = async () => {
    const fetchMyIpUrl = "https://stat.ripe.net/data/whats-my-ip/data.json";
    const fetchGeoUrl = "https://stat.ripe.net/data/geoloc/data.json";
    let ipResponse = await fetch(fetchMyIpUrl);
    let ipAddress = await ipResponse.json();
    let geoResponse = await fetch(
      `${fetchGeoUrl}?resource=${ipAddress.data.ip}`
    );
    let geoLocation = await geoResponse.json();
    return (
      (geoLocation.data.locations && geoLocation.data.locations[0]) || null
    );
  };

  loadAs2GeojsonIndex = async () => {
    const fetchUrl =
      "https://sg-pub.ripe.net/emile/ixp-country-jedi/history/country-timelines.json";
    let response = await fetch(fetchUrl);
    let countrySnapshots = await response.json();
    return countrySnapshots;
  };

  componentDidMount() {
    // load all AS,orgName pairs
    this.loadAs2OrgNames().then(o => {
      this.setState({
        orgnames: o
      });
    });

    // load country geometry and metadata and .then
    // figure out which country to render.
    this.loadCountryGeoInfo(countryGeoInfoUrl).then(o => {
      console.log(o);
      this.setState({
        countries: o["openipmapCountries-ne50m"],
        cities: o["openipmapCities-geo150"]
      });

      // try to get the country of the user
      this.whatsMyGeoLocation().then(l => {
        const now = new Date(),
          mostRecentFirstInMonth = `${now.getYear() + 1900}/${(
            "0" + (now.getMonth() + 1).toString()
          ).slice(-2)}/01`;

        // load the generic country data
        this.loadAs2GeojsonIndex().then(cA => {
          // try to construct country and snapshot date from url,
          // if it is not there then use the guessed country based on
          // the user IP address.
          console.log(this.destructureCountryInfoFromUrl());
          let [
            urlCountryCode,
            urlYear,
            urlMonth,
            urlDay
          ] = this.destructureCountryInfoFromUrl();
          const countryCode =
            (urlCountryCode && urlCountryCode.toUpperCase()) ||
            l.country.toUpperCase();
          console.log(countryCode);

          // Now see which snapshot dates we have for this country
          // if we don't find anything (either because the user put a countrycode in the url
          // or we have guessed the country) we're using the first of the current month.
          const snaps = (
            cA.find(snap => snap.country === countryCode) || {
              dates: [mostRecentFirstInMonth]
            }
          ).dates.map(d => {
            const [year, month, day] = d
              .match(/([0-9]{4})[\/\-]([0-9]{2})[\/\-]([0-9]{2})/)
              .slice(1, 4);
            return {
              year,
              month,
              day
            };
          });

          console.log(snaps);
          let [year, month, day] = [
            urlYear || snaps.slice(-1)[0].year,
            urlMonth || snaps.slice(-1)[0].month,
            urlDay || snaps.slice(-1)[0].day
          ];
          this.setState({
            snapshots: snaps,
            allCountriesWithValidSnaps: cA
              .filter(
                snapsForC =>
                  snapsForC.dates.filter(
                    d => new Date(d) >= new Date("2018-01-01")
                  ).length > 0
              )
              .map(snapsForC => ({
                ...this.state.countries.geometries.find(
                  c => c.properties.countryCode === snapsForC.country
                ),
                dates: snapsForC.dates.filter(
                  d => new Date(d) >= new Date("2018-01-01")
                )
              })),
            countryCode: countryCode,
            currentSnapshotDate: { year, month, day },
            countryInfo: this.state.countries.geometries.find(
              c => c.properties.countryCode === countryCode.toUpperCase()
            )
          });
          console.log(new Date(`${year}/${month}/${day} 00:00`));
        });
      });
    });

    // See if the URL has parameters for the primary graph.

    //const [urlYear, urlMonth, urlDay] = this.destructureCountryInfoFromUrl();

    // ready collecting info, try to assemble the parameters for the primary graph:
    // 1. See if the URL has parameters, if so, 'move' to the nearest available snapshot, if not:
    // 2. Use the geolocated IP address to use as the country for the primary graph
    // 3. If we still don't have a date, use the most recent snapshot.
  }

  changeSnapshotDate = newSnapshotDate => {
    const stateObj = {
      country: this.state.countryCode,
      snapshotDate: this.state.currentSnapshotDate
    };
    window.history.pushState(
      stateObj,
      "",
      `${(primaryFromUrl() &&
        window.location.pathname.replace(primaryFromUrl()[0], "")) ||
        window.location.pathname.replace(
          /\/?$/,
          "/"
        )}${this.state.countryCode.toLowerCase()}/${newSnapshotDate.year}/${
        newSnapshotDate.month
      }/${newSnapshotDate.day}`
    );

    this.setState({
      currentSnapshotDate: newSnapshotDate
    });
  };

  changeCountry = newCountry => {
    const countryCode = newCountry.properties.countryCode.toLowerCase(),
      snapshotDate = this.state.currentSnapshotDate;
    const stateObj = {
      country: this.state.countryCode,
      snapshotDate: snapshotDate
    };

    // load all available snapshotdates for this country
    const snapshots = (newCountry.dates || []).map(d => ({
      year: d.slice(0, 4),
      month: d.slice(5, 7),
      day: d.slice(8, 10)
    }));

    console.log("new snapshots");
    console.log(newCountry.dates);

    window.history.pushState(
      stateObj,
      "",
      `${(primaryFromUrl() &&
        window.location.pathname.replace(primaryFromUrl()[0], "")) ||
        window.location.pathname.replace(/\/?$/, "/")}${countryCode}/${
        snapshotDate.year
      }/${snapshotDate.month}/${snapshotDate.day}`
    );

    this.setState({
      countryCode: countryCode,
      snapshots: snapshots
    });
  };

  render() {
    return (
      <div id="ptp-fabric-panel">
        <PeerToPeerStoryText />
        {this.state.currentSnapshotDate && (
          <PeerToPeerDialog
            countryInfo={
              this.state.countryCode &&
              this.state.countries &&
              this.state.countries.geometries.find(
                c =>
                  c.properties.countryCode ===
                  this.state.countryCode.toUpperCase()
              )
            }
            countryCode={this.state.countryCode}
            countries={this.state.allCountriesWithValidSnaps}
            changeCountry={this.changeCountry}
          >
            <SnapShotTimeLine
              snapshots={this.state.snapshots || []}
              currentSnapshotDate={this.state.currentSnapshotDate}
              handleChangeSnapshot={this.changeSnapshotDate}
            />
          </PeerToPeerDialog>
        )}

        {
          <PeerToPeerFabricGraph
            primary={true}
            countryInfo={
              this.state.countryCode &&
              this.state.countries &&
              this.state.countries.geometries.find(
                c =>
                  c.properties.countryCode ===
                  this.state.countryCode.toUpperCase()
              )
            }
            countryCode={this.state.countryCode}
            year={
              this.state.currentSnapshotDate &&
              this.state.currentSnapshotDate.year
            }
            month={
              this.state.currentSnapshotDate &&
              this.state.currentSnapshotDate.month
            }
            day={
              this.state.currentSnapshotDate &&
              this.state.currentSnapshotDate.day
            }
            orgNames={this.state.orgnames}
            status={
              (this.state.countryCode &&
                this.state.countries &&
                this.state.currentSnapshotDate &&
                "ready") ||
              "waiting"
            }
          />
        }

        <Legend />
        <div className="small-graphs">
          <ExplainCircle1 />
          <ExplainCircle2 />
          <ExplainCircle3 />
        </div>
        <div className="small-graphs">
          <ExplainSmallCircles1 />
          <ExplainSmallCircles2 />
          <ExplainSmallCircles3 />
        </div>
        <div className="small-graphs">
          <ExplainLines1 />
          <ExplainLines2 />
          <ExplainLines3 />
        </div>
        <OtherCountries />
        {this.state.countries && (
          <SmallGraphs hasGraphs={true}>
            <PeerToPeerFabricGraph
              countryInfo={this.state.countries.geometries.find(
                c => c.properties.countryCode === "KR"
              )}
              countryCode="KR"
              year="2018"
              month="05"
              day="01"
              hideText={true}
            />
            <PeerToPeerFabricGraph
              countryInfo={this.state.countries.geometries.find(
                c => c.properties.countryCode === "IE"
              )}
              countryCode="IE"
              year="2018"
              month="05"
              day="01"
              hideText={true}
            />
            <PeerToPeerFabricGraph
              countryInfo={this.state.countries.geometries.find(
                c => c.properties.countryCode === "CZ"
              )}
              countryCode="CZ"
              year="2018"
              month="05"
              day="01"
              hideText={true}
            />
          </SmallGraphs>
        )}
      </div>
    );
  }
}
