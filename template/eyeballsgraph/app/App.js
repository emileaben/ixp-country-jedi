import React from "react";
import { PeerToPeerContainer } from "./containers/story.jsx";

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

const App = props => {
  return <PeerToPeerContainer />;
}

export default App;
