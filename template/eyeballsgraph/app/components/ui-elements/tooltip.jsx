import React from "react";
import PropTypes from "prop-types";

export class SvgToolTip extends React.Component {
  constructor(props) {
    super(props);
    this.numTextLines = this.props.textlines.reduce(
      (acc, t) => acc + ((typeof t === "object" && 3) || 2),
      1
    );
    this.margin = 1.2 * this.props.fontsize;
    this.lineHeight = this.props.fontsize + 2;
    this.height = this.numTextLines * this.lineHeight + 2 * this.margin;
    this.y = this.props.y - this.height;
    this.x = this.props.x;
  }

  render() {
    let curLine = this.numTextLines;
    return (
      <g
        className="tooltip"
        transform={`matrix(1 0 0 1 ${this.props.dx} ${this.props.dy})`}
      >
        <rect
          className="tooltip-bg"
          width={Math.max(
            24 + this.props.header.length * 8,
            this.props.minwidth
          )}
          height={this.height}
          y={this.y}
          x={this.x}
          rx="4"
          ry="4"
        />
        <text
          className="tooltip-header"
          x={this.props.x + this.margin}
          y={this.props.y - curLine * this.lineHeight - 2}
        >
          {this.props.header}
        </text>
        {(curLine -= 2)}
        {this.props.textlines.map((child, i) => {
          if (typeof child === "string") {
            //curLine -= 1;
            return (
              <text
                x={this.props.x + this.margin}
                y={this.props.y - curLine * this.lineHeight}
                key={`tt_s${child.id}_${i}`}
              >
                {child}
              </text>
            );
          }
          curLine -= 3;
          return [
            <text
              className="tooltip-subheader"
              x={this.props.x + this.margin}
              y={this.props.y - (curLine + 1) * this.lineHeight}
              key={`tt_h${child.id}_${i}`}
            >
              {child.header}
            </text>,
            <text
              x={this.props.x + this.margin}
              y={this.props.y - curLine * this.lineHeight}
              textAnchor="start"
              key={`tt_c${child.id}_${i}`}
            >
              {child.content}
            </text>
          ];
        })}
        {/* ///////
      <text
        x={this.props.x + this.margin}
        y={this.props.y - 11 * this.lineHeight - 3}
      >
        {d.name}
      </text>
      <text
        x={this.props.x + this.margin}
        y={this.props.y - 9 * this.lineHeight}
        className="tooltip-subheader"
        textAnchor="start"
      >
        name
      </text>
      <text
        x={this.props.x + this.margin}
        y={this.props.y - 8 * this.lineHeight}
      >
        {(d.orgName !== "" && d.orgName) || "-"}
      </text>
      {isEyeball && [
        <text
          key={`${d.name}_1`}
          x={this.props.x + this.margin}
          y={this.props.y - 6 * this.lineHeight}
          className="tooltip-subheader"
          textAnchor="start"
        >
          end users
        </text>,
        <text
          x={this.props.x + this.margin}
          y={this.props.y - 5 * this.lineHeight}
          key={`${d.name}_2`}
        >
          {(Math.round(d.eyeball_pct * 100) / 100).toFixed(1)}%
        </text>
      ]}
      <text
        x={this.props.x + this.margin}
        y={this.props.y - ((isEyeball && 3) || 6) * this.lineHeight}
        className="tooltip-subheader"
        textAnchor="start"
      >
        connectedness
      </text>
      <text
        x={this.props.x + this.margin}
        y={this.props.y - ((isEyeball && 2) || 5) * this.lineHeight}
      >
        {(d.type !== "eyeball_asn_noprobe" &&
          `${Math.round(d.conn_btwn_pct * 100 / 100).toFixed(1)}%`) ||
          "-"}
      </text>


    ////// */}
        <polyline
          points={`${this.props.x},${this.props.y -
            this.props.dy -
            this.margin / Math.sqrt(2)} ${this.props.x - this.margin},${this
            .props.y - this.props.dy} ${this.props.x},${this.props.y -
            this.props.dy +
            this.margin / Math.sqrt(2)}`}
        />
      </g>
    );
  }
}

SvgToolTip.propTypes = {
  dx: PropTypes.number,
  dy: PropTypes.number,
  x: PropTypes.number,
  y: PropTypes.number,
  header: PropTypes.string,
  textlines: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.object, PropTypes.string])
  ),
  fontsize: PropTypes.number,
  minwidth: PropTypes.number
};
