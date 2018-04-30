import React from "react";
import { CountryAutoCompleteInput } from "@ripe-rnd/ui-components";

export class PeerToPeerDialog extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      selectedLocation: null
    };
  }

  render() {
    return (
      <div className="small-graphs">
        <CountryAutoCompleteInput
          title="Country"
          countries={this.props.countries}
          initialCountry={this.props.countryInfo}
          emptyHint="type a country name, country code or space"
          onSubmit={this.props.changeCountry}
        />
        {this.props.children}
      </div>
    );
  }
}
