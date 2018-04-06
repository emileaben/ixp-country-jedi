import React from "react";

import * as d3 from "d3";
import "../../../styles/eyeballsgraph.less";

const TAU = 2 * Math.PI;

export class PeerToPeerFabricFacts extends React.Component {
  loadCountryGeoInfo = async countryGeoInfoUrl => {
    let response = await fetch(countryGeoInfoUrl);
    let data = await response.json();
    return data.objects;
  };

  render() {
    return (
      <div>
        <h2>
          {(this.props.countryInfo &&
            this.props.countryInfo.properties.countryNameLong) ||
            ""}
        </h2>
        <p>
          {this.props.year}-{this.props.month}-{this.props.day}
        </p>
      </div>
    );
  }
}

export class PeerToPeerFabricGraph extends React.Component {
  constructor(props) {
    super(props);

    const schema = {
      eyeball: "eyeball_asn",
      ixp: "ixp_asn",
      transit: "transit_asn"
    };
  }

  // puts eyeball asns on the outer circle
  getForceRadial = d => (d.type === "eyeball_asn" && 210) || 0;

  getForceX = d => d.type === "eyeball_asn";

  nodeClass = d =>
    (d.type === "eyeball_asn" && d.transits && "eyeball-with-transit") ||
    (d.type === "eyeball_asn_noprobe" && "eyeball-no-probe") ||
    (d.type === "eyeball_asn" && "eyeball") ||
    (d.type === "transit_asn" && "transit") ||
    (d.type === "ixp" && "ixp") ||
    "";

  resolveAsToName = async asn => {
    const fetchUrl = `${this.props.asResolverUrl}${asn}`;
    let response = await fetch(fetchUrl);
    let data = await response.json();
    //console.log(`${asn} => ${data.data.holder}`);
    return data.data.holder;
  };

  replaceAs2OrgNames = async nodes => {
    let unknownAses = [];
    for (let node of nodes.filter(n => n.name && n.name.slice(0, 2) === "AS")) {
      let orgName =
        this.props.orgnames &&
        this.props.orgnames.find(
          o => o.asn === node.name.replace("AS", "") && o.name !== ""
        );
      if (orgName) {
        console.log(`inject ${orgName.name}`);
        const textNode = document.querySelector(
          `text[data-asn="${node.name}"]`
        );
        if (textNode) {
          textNode.textContent = orgName.name.split(/_|\.| |\,/)[0];
        }
      } else {
        console.log(`skipping ${node.name}`);
        unknownAses.push(node.name);
      }
    }
    return unknownAses;
  };

  getOrgNamesFromRipeStat = async asns => {
    for (let asn of asns.filter(
      n => n.slice(0, 2) === "AS" //&&
      //n.type !== "eyeball_asn" &&
      //n.type !== "eyeball_asn_noprobe"
    )) {
      let orgName = await this.resolveAsToName(asn);
      if (orgName !== "") {
        console.log(`inject ${orgName}`);
        // console.log(
        //   document.querySelector(`text[data-asn='${asn}']`).textContent
        // );
        const textNode = document.querySelector(`text[data-asn="${asn}"]`);
        if (textNode) {
          textNode.textContent = orgName.split(/_|\.| |\,/)[0];
        }
      }
    }
  };

  componentDidMount() {
    if (!this.props.countryCode) {
        console.log(this.props);
        console.log('skipping...');
        return;
    }
    console.log(`rendering ${this.props.countryCode}`);
    const countryDataForDateUrl = `${this.props.dataBaseUrl}${
      this.props.year
    }-${this.props.month}-${
      this.props.day
    }/${this.props.countryCode.toUpperCase()}/eyeballasgraph/asgraph.json`;

    d3.json(countryDataForDateUrl, (error, data) => {
      console.log((error && error) || "loaded without errors");
      console.log(this.props.countryCode);
      const countryCode = this.props.countryCode,
        year = this.props.year,
        month = this.props.month,
        day = this.props.day;
      const unknownAses =
        !this.props.hideText &&
        this.replaceAs2OrgNames(data.nodes).then(
          unknownAses =>
            unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses)
        );

      function ticked() {
        link.attr("d", positionLink);
        node.attr("transform", positionNode);
      }

      const positionLink = d => {
        return (
          //(d[3] === "i" &&
          //`M ${d[0].x},${d[0].y} S ${d[1].x},${d[1].y} ${d[2].x},${d[2].y}`) ||
          `M ${d[0].x},${d[0].y} A 800,800 0 0 1 ${d[2].x} ${d[2].y}`
        ); //||
        // `M ${d[0].x},${d[0].y} S 0,0 ${d[2].x} ${d[2].y}`) ||
        //   (d[0].type === "eyeball_asn" &&
        //     d[2].type === "eyeball_asn" &&
        //`M ${d[0].x},${d[0].y} A 350,350 0 0 1 ${d[2].x} ${d[2].y}`) ||
        //`M ${d[0].x},${d[0].y} A 0,0 0 0 0 ${d[2].x} ${d[2].y}`
        // );
      };
      const positionNode = d => `translate(${d.x},${d.y})`;

      const svg = d3.select(
        `svg#${countryCode.toLowerCase()}-${year}-${month}-${day}`
      );

      //   var div = d3
      //     .select("body")
      //     .append("div")
      //     .attr("class", "tooltip");

      var nodes = data.nodes,
        nodeById = d3.map(nodes, function(d) {
          return d.id;
        }),
        links = data.edges,
        bilinks = [];

      links.forEach(function(link) {
        //console.log(link.type);
        var s = (link.source = nodeById.get(link.source)),
          t = (link.target = nodeById.get(link.target)),
          //i = { index: 100, vx: 0, vy: 0, x: 0, y: 0 }; // intermediate node
          i = {};
        //console.log(i);
        nodes.push(i);
        links.push({ source: s, target: i }, { source: i, target: t });
        //link.source.type === "eyeball_asn" &&
        //  link.target.type === "transit_asn" &&
        bilinks.push([s, i, t, link.type]);
      });

      var connectedRing = d3
        .pie()
        .padAngle(0.01)
        .endAngle(
          TAU *
            (nodes
              .filter(
                d =>
                  d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
              )
              // calculate which percentage we're actually representing,
              // so that we can have an open ring.
              .reduce((acc, cur) => acc + cur.eyeball_pct, 0) /
              100)
        )
        .value(d => d.eyeball_pct)(
        nodes.filter(
          d => d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
        )
      );
      //console.log(connectedRing);
      var connectedArcSegment = d3.arc().innerRadius(220);
      //.outerRadius(230);
      //.endAngle(Math.PI / 2);

      var textOutLineSegment = d3
        .arc()
        .innerRadius(245)
        .outerRadius(245);

      var eyeBallsRing = d3
        .arc()
        .innerRadius(220)
        .outerRadius(220);

      connectedRing.forEach(d => {
        const textCoords = textOutLineSegment.centroid(d);
        let group = svg
          .append("g")
          .attr(
            "class",
            (d.data.type === "eyeball_asn_noprobe" && "eyeball-no-probe") || ""
          );

        group
          .append("path")
          .attr(
            "d",
            connectedArcSegment.outerRadius(d => 240)(d)
            //connectedArcSegment.outerRadius(d => d.data.eyeball_pct + 220)(d)
          )
          .attr("class", "c-ring");

        if (!this.props.hideText) {
          group
            .append("text")
            .text(d.data.name)
            .attr("data-asn", d.data.name)
            .attr("x", textCoords[0])
            .attr("y", textCoords[1])
            .attr(
              "text-anchor",
              d =>
                (textCoords[0] < 0 && "end") ||
                (textCoords[0] > 0 && "start") ||
                "middle"
            );
        }
      });

      var link = svg
        //.append("g")
        .selectAll(".link")
        .data(bilinks)
        .enter()
        .append("path")
        .attr("class", d => {
          //console.log(d);
          const linkClass =
            (d[0].type === "transit_asn" &&
              d[2].type === "transit_asn" &&
              "transit-transit") ||
            (d[0].type === "eyeball_asn" &&
              d[2].type === "ixp" &&
              "eyeball-ixp") ||
            (d[0].type === "ixp" &&
              d[2].type === "eyeball_asn" &&
              "ixp-eyeball") ||
            (d[0].type === "ixp" &&
              d[2].type === "transit_asn" &&
              "ixp-transit") ||
            (d[0].type === "eyeball_asn" &&
              d[2].type === "transit_asn" &&
              "eyeball-transit") ||
            (d[0].type === "transit_asn" &&
              d[2].type === "eyeball_asn" &&
              "transit-eyeball") ||
            (d[0].type === "ixp" && d[2].type === "ixp" && "ixp-ixp") ||
            (d[2].type === "eyeball_asn" && "eyeball") ||
            (d[2].type === "transit_asn" && "transit") ||
            (d[2].type === "ixp" && "ixp");
          //d[0].type;
          return `link ${linkClass} ${d[3]}`;
        });

      var node = svg
        .selectAll(".circle")
        .data(nodes.filter(d => d.id || d.id === 0))
        .enter()
        .append("g")
        .attr("class", this.nodeClass);

      node.append("circle").attr("r", d => {
        const scalar =
          // (d.type === "eyeball_asn" && Math.max(d.eyeball_pct, BALL_MIN_SIZE)) ||
          // ((d.type === "transit_asn" || d.type === "ixp") &&
          d.conn_btwn_pct || this.props.ballMinSize;
        return Math.max(Math.log(scalar * this.props.scaleFactor) * 3.5, 2);
      });
      // .on("mouseover", function(d) {
      //   const g = d3.select(this);
      //   div.style("opacity", 0.9);
      //   div
      //     .html(
      //       `<div class="tooltip"><h4>${d.name}</h5><p>${
      //         d.eyeball_pct
      //       }</p><div>`
      //     )
      //     .attr("left", `${d.x}px`)
      //     .attr("top", `${d.y}px`);
      // })
      // .on("mouseout", function(d) {
      //   div.style("opacity", 0);
      // });

      if (!this.props.hideText) {
        node
          .append("text")
          .text(
            d =>
              (d.type !== "eyeball_asn" &&
                d.type !== "eyeball_asn_noprobe" &&
                d.name) ||
              ""
          )
          .attr("data-asn", d => d.name);
      }

      var simulation = d3
        .forceSimulation()
        .force(
          "charge",
          d3.forceCollide().radius(d => (d.type !== "eyeball_asn" && 12) || 0)
        )
        .force(
          "x",
          d3.forceX(d => {
            let seg = connectedRing.find(c => c.data.index === d.index);
            //seg && console.log(eyeBallsRing.centroid(seg));
            return (seg && eyeBallsRing.centroid(seg)[0]) || 0;
            //return 0;
          })
        )
        .force(
          "y",
          d3.forceY(d => {
            let seg = connectedRing.find(c => c.data.index === d.index);
            //seg && console.log(eyeBallsRing.centroid(seg));
            return (seg && eyeBallsRing.centroid(seg)[1]) || 0;
          })
        )
        .nodes(nodes)
        .on("tick", ticked);
    });
  }

  render() {
    if (!this.props.countryCode) {
        console.log('skip rendering...');
      return null;
    }

    return (
      <div>
        <PeerToPeerFabricFacts {...this.props} key="primary-facts" />
        <svg
          key="primary-graph"
          width="100%"
          viewBox="-400 -250 800 500"
          className="p-t-p-fabric"
          transform={`scale(${this.props.scaleFactor / 2})`}
          id={`${this.props.countryCode.toLowerCase()}-${this.props.year}-${
            this.props.month
          }-${this.props.day}`}
        >
          <defs>
            <linearGradient id="linear" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#05a" />
              <stop offset="100%" stopColor="#0a5" />
            </linearGradient>
          </defs>
          <circle r="245" cx="0" cy="0" className="interior-circle" />
        </svg>
      </div>
    );
  }
}

PeerToPeerFabricGraph.defaultProps = {
  primary: false,
  scaleFactor: 2,
  dataBaseUrl: "https://sg-pub.ripe.net/emile/ixp-country-jedi/history/",
  asResolverUrl: "https://stat.ripe.net/data/as-overview/data.json?resource=",
  width: 1440,
  height: 750,
  ballMinSize: 2.0,
  hideText: false
};

export default PeerToPeerFabricGraph;
