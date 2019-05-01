import React from "react";

const MIN_SNAPSHOT_DATE = new Date("2018/01/01");
// TODO: horizontal lines + arrows are still hardcoded in their spots.
const MONTHS_NO = 4;

class SnapshotDot extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      currentSnapshotDate: props.currentSnapshotDate
    };
  }

  render() {
    return [
      <text
        transform={`matrix(1 0 0 1 ${this.props.i * 100 + 40} 55.998)`}
        key={`t-${this.props.i}`}
      >
        {this.props.monthName}
      </text>,
      this.props.isCurrentDate && (
        <circle
          className="st2"
          cx={this.props.i * 100 + 40}
          cy="79.2"
          r="12"
          key={"cc-${this.props.i}"}
        />
      ),
      <circle
        className={(this.props.isCurrentDate && "st3") || "st2"}
        cx={this.props.i * 100 + 40}
        cy="79.2"
        r="9"
        onClick={() => this.props.handleChangeSnapshot(this.props.snapshotDate)}
        key={`c-${this.props.i}`}
      />
    ];
  }
}

export class SnapShotTimeLine extends React.Component {
  render() {
    const currentSnapshots = this.props.snapshots.filter(
      s => new Date(`${s.year}-${s.month}-${s.day}`) >= MIN_SNAPSHOT_DATE
    );
    // const firstDate = (currentSnapshots && currentSnapshots[0]) || null;
    const snapshotSlice = currentSnapshots.slice(-MONTHS_NO);
    const yearSlices = snapshotSlice.reduce((slices, s, i) => {
      slices[s.year] = (slices[s.year] && [
        slices[s.year][0],
        slices[s.year][1] + 1
      ]) || [i, i];
      return slices;
    }, {});
    console.log(yearSlices);
    // const endYear = snapshotSlice[3].year;
    // const startYear = snapshotSlice[0].year;
    // console.log(endYear);
    // console.log(snapshotSlice);
    // console.log(startYear);
    return (
      <svg
        className="snapshot-timeline"
        x="0px"
        y="0px"
        width="377.4px"
        height="91.7px"
        viewBox="0 0 377.4 91.7"
        style={{ enableBackground: "new 0 0 377.4 91.7" }}
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
          {/* <circle className="st2" cx="39.3" cy="79.2" r="9" />
          <circle className="st2" cx="338.3" cy="79.2" r="9" />
    <circle className="st2" cx="137.1" cy="79.2" r="9" /> */}

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
          {/* by default show the four most recent snapshots in the timeline */}
          {snapshotSlice.map((s, i) => {
            const date = new Date(`${s.year}-${s.month}-${s.day} 00:00`);
            // JS is funny like that: a Date is never equal to a Date.
            const isCurrentDate =
              (this.props.currentSnapshotDate.year === s.year &&
                this.props.currentSnapshotDate.month === s.month &&
                this.props.currentSnapshotDate.day === s.day) ||
              false;
            const monthName = date.toLocaleDateString("en-us", {
              month: "long"
            });

            return (
              <SnapshotDot
                monthName={monthName}
                isCurrentDate={isCurrentDate}
                snapshotDate={s}
                i={i}
                handleChangeSnapshot={s => this.props.handleChangeSnapshot(s)}
                key={`ssdot-${i}`}
              />
            );
          })}
          {/*<text transform="matrix(1 0 0 1 14.6255 55.998)">August</text>
          <text transform="matrix(1 0 0 1 101.7588 55.998)">September</text>
          <text transform="matrix(1 0 0 1 203.9561 55.998)">1 October</text>
        <text transform="matrix(1 0 0 1 302.0596 55.998)">December</text>*/}
          {Object.entries(yearSlices).map((s, i) => {
            const maxX = 38.4 + s[1][1] * 100;
            const minX = s[1][0] * 100 + 38.4;
            return (
              <>
                <polyline
                  className="st0"
                  points={`${minX},31.2 ${minX},21.5 ${maxX},21.5 ${maxX},31.2`}
                />
                <text
                  transform={`matrix(1 0 0 1 ${maxX - (maxX - minX) / 2 } 13.7109)`}
                >
                  {s[0]}
                </text>
              </>
            );
          })}
          {/* <circle className="st2" cx="237.3" cy="79.2" r="12" /> */}
          {/* <circle className="st3" cx="237.3" cy="79.2" r="9" /> */}
        </g>
      </svg>
    );
  }
}
