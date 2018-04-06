import React from "react";
import ReactDOM from "react-dom";

import * as d3 from "d3";
import "../styles/eyeballsgraph.less";

import "babel-polyfill";

import { AppContainer } from "react-hot-loader";
import App from "./App";

export const render = (Component, props) => {
  ReactDOM.render(
    <AppContainer>
      <Component {...props} />
    </AppContainer>,
    document.querySelector(props.domElement)
  );
};

render(App, { domElement: "#content" });

// Hot Module Replacement API
if (module.hot) {
  module.hot.accept("./App", props => {
    render(App, { domElement: "#content" });
  });
}
