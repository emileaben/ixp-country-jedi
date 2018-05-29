import React from "react";

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

export class Legend extends React.Component {
  render() {
    return (
      <div className="legend-container">
        <h2>LEGEND</h2>
        <span onClick={this.props.onClick} className="more-text">
          {(this.props.showMore && "collapse") || "expand"}
        </span>
        <div className="legend-flexbox">
          <svg xmlns="http://www.w3.org/2000/svg" className="legend">
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
          <svg>
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
          <svg>
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
        {this.props.children}
      </div>
    );
  }
}

export class MoreLegend extends React.Component {
  render() {
    return (
      <div className="more-panel">
        <div
          className={`more ${(this.props.showMore && "emerge") || `disappear`}`}
        >
          <div className="small-graphs">
            <div>
              <ExplainCircle1 />
              <p>
                The full circle represents 100% of the end-users in a country.
              </p>
            </div>
            <div>
              <ExplainCircle2 />
              <p className="small">
                Each network that provides connectivity to more than 1% of the
                end-users is represented by a colored circle segment. The length
                of the arc of the segment represents the percentage of the
                end-users in a country.
              </p>
              <p>
                The darker green denotes an network for which we have
                peer-to-peer data. The lighter green color denotes networks for
                which we don’t have peer-to-peer data.
              </p>
            </div>
            <div>
              <ExplainCircle3 />
              <p>
                The open part of the circle represents the sum of all ASes that
                provide connectivity to less than 1% of the end-users in a
                country
              </p>
            </div>
          </div>
          <div className="small-graphs">
            <div>
              <ExplainSmallCircles1 />
              <p>
                Each ring or circle represents the percentage of the
                peer-to-peer fabric in a country that passes through this point.
              </p>
              <p>
                The color of the circle or ring denotes the type of location.
              </p>
            </div>
            <div>
              <ExplainSmallCircles2 />
              <p>
                A blue circle on the outer ring represents a network that both
                serves end-users and provides transit to others end-user
                networks within the country.
              </p>
              <p>
                A green circle on the outer ring represents a network that
                (mainly) serves end-users.
              </p>
            </div>
            <div>
              <ExplainSmallCircles3 />
              <p>
                A blue circle in the interior indicates a transit network or an
                IXP that is external to this country.
              </p>
              <p>
                An orange circle in the interior indicates an IXP identified
                with this country.
              </p>
            </div>
          </div>
          <div className="small-graphs">
            <div>
              <ExplainLines1 />
              <p>
                Orange lines indicate that two end-user networks are connected
                through an IXP.
              </p>
            </div>
            <div>
              <ExplainLines2 />
              <p>
                Green lines indicate that two end-user networks are directly
                connected.
              </p>
            </div>
            <div>
              <ExplainLines3 />
              <p>
                Blue lines indicate two end-user networks are connected through
                a transit network.
              </p>
              <p>
                Dotted lines of any color indicate that we cannot fully map this
                path.
              </p>
            </div>
          </div>

          {this.props.showMore && (
            <div className="more-text" onClick={this.props.onClick}>
              collapse legend
            </div>
          )}
        </div>
      </div>
    );
  }
}
