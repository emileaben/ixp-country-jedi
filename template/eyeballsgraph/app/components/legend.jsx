import React from "react";

export class Legend extends React.Component {
  render() {
    return (
      <div className="legend-container">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="legend"
        >
          <path
            className="c-ring"
            d="M0,26.55A360.59,360.59,0,0,1,45.28,0L58.35,27A329.14,329.14,0,0,0,17.19,51.14Z"
          />
          <g className="eyeball">
            <circle cx="34.95" cy="35.38" r="17.9" />
          </g>
          <text transform="translate(72.68 30.16)">
            A network that serves end-users
          </text>
          <path
            className="c-ring"
            d="M0,89.33A360.66,360.66,0,0,1,45.28,62.77l13.07,27a329.21,329.21,0,0,0-41.16,24.14Z"
          />
          <g className="eyeball-with-transit">
            <circle cx="34.95" cy="96.09" r="17.21" />
          </g>
          <text transform="translate(72.68 70.86)">
            A network that serves end-users and
            <tspan x="0" y="17">
              provides transit to other end-user net
            </tspan>
            <tspan x="0" y="34">
              works within the country
            </tspan>
          </text>
        </svg>
        <svg >
          <g className="transit">
            <circle className="transit" cx="34.75" cy="35.38" r="14.58" />
          </g>
          <text transform="translate(72.48 28.39)">
            A transit network or an IXP external to
            <tspan x="0" y="18">
              this country
            </tspan>
          </text>
          <g className="ixp">
            <circle cx="34.91" cy="77.89" r="13.6" />
          </g>
          <text transform="translate(72.64 81.41)">
            An IXP that is identified with this country
          </text>
          </svg>
          <svg >
          <g className="eyeball-no-probe">
            <path
              className="c-ring"
              d="M0,78.42 a359.38,359.38,0,0,1,45.28-26.55l13.07,27a329.21,329.21,0,0,0-41.16,24.14Z"
            />
          </g>
          <text transform="translate(72.68 71.35)">
            <tspan>A sizable end-user network for which we </tspan>
            <tspan x="0" y="18">
              have no data
            </tspan>
          </text>
          <path
            className="c-ring"
            d="M0,25.87 a360.59,360.59,0,0,1,45.28-26.55l13.07,27a329.21,329.21,0,0,0-41.16,24.14Z"
          />
          <text transform="translate(72.68 17.9)">
            A sizable end-user network for which
            <tspan x="0" y="18">
              we have data
            </tspan>
          </text>
        </svg>
      </div>
    );
  }
}
