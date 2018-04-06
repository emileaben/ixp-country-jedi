import React from "react";

import { Legend } from "../components/legend.jsx";
import { SmallGraphs } from "../components/ui-elements/flexbox";
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
const primaryFromUrl = window.location.pathname.match(
  /([a-zA-Z]{2})[\/\-]([0-9]{4})[\/\-]([0-9]{2})[\/\-]([0-9]{2})/
);

const destructureCountryInfoFromUrl = () => {
  const paths = primaryFromUrl || null;
  let [countryCode, year, month, day] = (paths && paths.slice(1, 6)) || [
    null,
    null,
    null,
    null
  ];

  // let [propsYear, propsMonth, propsDay] = props.date
  //   .match(/([0-9]{4})[\/\-]([0-9]{2})[\/\-]([0-9]{2})/)
  //   .slice(1, 6) || [null, null, null];
  return {
    countryCode,
    year,
    month,
    day
  };
};

export class PeerToPeerContainer extends React.Component {
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
    const fetchMyIpUrl = `https://stat.ripe.net/data/whats-my-ip/data.json`;
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

  componentDidMount() {
    // load country geometry and metadata
    this.loadCountryGeoInfo(countryGeoInfoUrl).then(o => {
      console.log(o);
      this.setState({
        countries: o["openipmapCountries-ne50m"],
        cities: o["openipmapCities-geo150"]
      });
    });

    // load all AS,orgName pairs
    this.loadAs2OrgNames().then(o => {
      this.setState({
        orgnames: o
      });
    });

    // try to get the country of the user
    this.whatsMyGeoLocation().then(l => {
      const countryCode = (l.country && l.country.toLowerCase()) || null;
      console.log(`user country:\t${countryCode}`);
      if (countryCode) {
        this.setState({
          countryCode: countryCode
        });
      }
    });
  }

  render() {
    return (
      <div id="ptp-fabric-panel">
        {/* id="ptp-fabric-panel"
      countryGeoInfoUrl={countryGeoInfoUrl}
    > */}
        <PeerToPeerStoryText />
        <SnapShotTimeLine />
        {(primaryFromUrl &&
          this.state &&
          this.state.countries && (
            <PeerToPeerFabricGraph
              primary={true}
              {...destructureCountryInfoFromUrl()}
            />
          )) ||
          (this.state &&
            this.state.countryCode &&
            this.state.countries && (
              <PeerToPeerFabricGraph
                primary={true}
                countryInfo={
                  this.state &&
                  this.state.countries &&
                  this.state.countries.geometries.find(
                    c =>
                      c.properties.countryCode ===
                      this.state.countryCode.toUpperCase()
                  )
                }
                countryCode={this.state && this.state.countryCode}
                year="2018"
                month="03"
                day="01"
              />
            )) || <div>waiting...</div>}

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
        {this.state &&
          this.state.countries && (
            <SmallGraphs hasGraphs={true}>
              <PeerToPeerFabricGraph
                countryInfo={this.state.countries.geometries.find(
                  c => c.properties.countryCode === "ES"
                )}
                countryCode="ES"
                //countries={this.state.countries}
                year="2018"
                month="03"
                day="01"
                hideText={true}
              />
              <PeerToPeerFabricGraph
                countryInfo={this.state.countries.geometries.find(
                  c => c.properties.countryCode === "IE"
                )}
                countryCode="IE"
                //countries={this.state.countries}
                year="2018"
                month="03"
                day="01"
                hideText={true}
              />
              <PeerToPeerFabricGraph
                countryInfo={this.state.countries.geometries.find(
                  c => c.properties.countryCode === "CZ"
                )}
                //countries={this.state.countries}
                countryCode="CZ"
                year="2018"
                month="02"
                day="01"
                hideText={true}
              />
            </SmallGraphs>
          )}
      </div>
    );

    //////////////////
    // return (
    //   <div id={this.props.id}>
    //     {/* propagate all loaded general info to all the children */}
    //     {React.Children.map(this.props.children, child => {
    //       return React.cloneElement(child, {
    //         // select the country for this particular child component
    //         // based on the presence of the `countryCode` property of the child.
    //         countryinfo:
    //           (this.state &&
    //             this.state.countries &&
    //             (child.props.countryCode &&
    //               this.state.countries.geometries.find(
    //                 c =>
    //                   c.properties.countryCode ===
    //                   child.props.countryCode.toUpperCase()
    //               ))) ||
    //           (this.state &&
    //             this.state.countryCode &&
    //             this.state.countries &&
    //             this.state.countries.geometries.find(
    //               c =>
    //                 c.properties.countryCode ===
    //                 this.state.countryCode.toUpperCase()
    //             )) ||
    //           null,
    //         // pass on the countryCode that was acquired from the geolocation of the user's ip,
    //         // if this is the primary graph.
    //         countryCode:
    //           (this.state && child.props.primary && this.state.countryCode) ||
    //           child.props.countryCode,
    //         // pass on all countries if the child indicates that it has children
    //         // itself that need specific country info.
    //         countries:
    //           child.props.hasGraphs && this.state && this.state.countries,
    //         orgnames:
    //           ((this.state || child.props.hasGraphs) &&
    //             this.state &&
    //             child.props.countryCode &&
    //             this.state.orgnames) ||
    //           null
    //       });
    //     })}
    //   </div>
    //);
  }
}
