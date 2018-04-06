import React from "react";

export class SnapShotTimeLine extends React.Component {
  render() {
    return (
      <svg
        className="snapshot-timeline"
        x="0px" y="0px"
        width="377.4px" height="91.7px"
        viewBox="0 0 377.4 91.7"
        style={{"enableBackground": "new 0 0 377.4 91.7"}}
      >
        <g>
          <line className="st0" x1="48.7" y1="79.2" x2="329.3" y2="79.2" />
          <g>
            <g>
              <line className="st1" x1="1" y1="79.2" x2="24.3" y2="79.2" />
              <g>
                <path
                  d="M6.5,83.1c0.1-0.2,0.1-0.4-0.1-0.6l-5.2-3.3l5.2-3.3c0.2-0.1,0.2-0.4,0.1-0.6c-0.1-0.2-0.4-0.2-0.6-0.1l-5.7,3.6
					C0.1,78.9,0,79.1,0,79.2s0.1,0.3,0.2,0.3l5.7,3.6c0.1,0,0.1,0.1,0.2,0.1C6.3,83.3,6.4,83.2,6.5,83.1z"
                />
              </g>
            </g>
          </g>
          <circle className="st2" cx="39.3" cy="79.2" r="9" />
          <circle className="st2" cx="338.3" cy="79.2" r="9" />
          <circle className="st2" cx="137.1" cy="79.2" r="9" />
          <polyline
            className="st0"
            points="338.4,31.2 338.4,22.2 338.4,21.5 38.6,21.5 38.6,30.5 	"
          />
          <g>
            <g>
              <line className="st1" x1="376.4" y1="79.2" x2="353" y2="79.2" />
              <g>
                <path
                  d="M370.9,75.3c-0.1,0.2-0.1,0.4,0.1,0.6l5.2,3.3l-5.2,3.3c-0.2,0.1-0.2,0.4-0.1,0.6c0.1,0.2,0.4,0.2,0.6,0.1l5.7-3.6
					c0.1-0.1,0.2-0.2,0.2-0.3s-0.1-0.3-0.2-0.3l-5.7-3.6c-0.1,0-0.1-0.1-0.2-0.1C371.1,75.2,371,75.2,370.9,75.3z"
                />
              </g>
            </g>
          </g>
          <text
            transform="matrix(1 0 0 1 14.6255 55.998)"
          >
            August
          </text>
          <text
            transform="matrix(1 0 0 1 101.7588 55.998)"
          >
            September
          </text>
          <text
            transform="matrix(1 0 0 1 203.9561 55.998)"
          >
            1 October
          </text>
          <text
            transform="matrix(1 0 0 1 302.0596 55.998)"
          >
            December
          </text>
          <text
            transform="matrix(1 0 0 1 165.8276 13.7109)"
          >
            2018
          </text>
          <circle className="st2" cx="237.3" cy="79.2" r="12" />
          <circle className="st3" cx="237.3" cy="79.2" r="9" />
        </g>
      </svg>
    );
  }
}
