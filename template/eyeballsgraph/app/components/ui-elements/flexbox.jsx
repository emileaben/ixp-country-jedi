import React from "react";

export class SmallGraphs extends React.Component {
  render() {
    return (
      <div className="small-graphs">
        {React.Children.map(this.props.children, child =>
          React.cloneElement(child, {
            countryinfo:
              (child.props.countryCode && this.props.countries && 
                this.props.countries.geometries.find(
                  c => c.properties.countryCode === child.props.countryCode
                )) ||
              null,
            orgnames: (child.props.countryCode && this.props.orgnames) || null
          })
        )}
      </div>
    );
  }
}
