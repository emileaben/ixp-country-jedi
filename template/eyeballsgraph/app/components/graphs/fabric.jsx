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
  getRingId = () => {
    return `${this.props.countryCode.toLowerCase()}-${this.props.year}-${
      this.props.month
    }-${this.props.day}`;
  };

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

  replaceAs2OrgNames = (nodes, orgNames = []) => {
    let unknownAses = [];
    for (let node of nodes.filter(n => n.name && n.name.slice(0, 2) === "AS")) {
      let orgName = orgNames.find(
        o => o.asn === node.name.replace("AS", "") && o.name !== ""
      );
      if (orgName) {
        console.log(`inject from as2org\t: ${orgName.name}`);
        const textNode = document.querySelector(
          `text[data-asn="${node.name}"]`
        );

        // add the orgName to the node, so it can be stored in the components
        // state later on.
        node.orgName = orgName.name.split(/_|\.| |\,/)[0];

        if (textNode) {
          // Manipulate DOM directly
          textNode.textContent = orgName.name.split(/_|\.| |\,/)[0];
        }
      } else {
        unknownAses.push(node.name);
      }
    }

    // batch update all the nodes in the current state
    this.state &&
      this.setState({
        asGraph: {
          ...this.state.asGraph,
          nodes: [...nodes]
        }
      });
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
        console.log(`inject from RIPEstat\t: ${orgName}`);
        // console.log(
        //   document.querySelector(`text[data-asn='${asn}']`).textContent
        // );
        // manipulate the DOM directly
        const textNode = document.querySelector(`text[data-asn="${asn}"]`);
        if (textNode) {
          textNode.textContent = orgName.split(/_|\.| |\,/)[0];
        }
        const newAsNode = this.state.asGraph.nodes.find(n => n.name === asn);
        this.setState({
          asGraph: {
            ...this.state.asGraph,
            nodes: [
              ...this.state.asGraph.nodes.filter(n => n.id !== newAsNode.id),
              { ...newAsNode, orgName: orgName.split(/_|\.| |\,/)[0] }
            ]
          }
        });
      }
    }
  };

  loadAsGraphData = async ({ year, month, day }) => {
    const countryDataForDateUrl = `${this.props.dataBaseUrl}${
      this.props.year
    }-${this.props.month}-${
      this.props.day
    }/${this.props.countryCode.toUpperCase()}/eyeballasgraph/asgraph.json`;

    let response = await fetch(countryDataForDateUrl);
    let data = await response.json();
    console.log("as-graph loaded without errors.");
    console.log(data);
    return data;
  };

  renderD3Ring = ({ data, ...props }) => {
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

    const svg = d3.select(`svg#${this.getRingId()}`);

    //   var div = d3
    //     .select("body")
    //     .append("div")
    //     .attr("class", "tooltip");

    var nodes = data.nodes,
      nodeById = d3.map(nodes, d => d.id),
      bilinks = [];

    // rework link data to include the
    // link type
    data.edges.forEach(function(link) {
      //console.log(link.type);
      var s = (link.source = nodeById.get(link.source)),
        t = (link.target = nodeById.get(link.target)),
        //i = { index: 100, vx: 0, vy: 0, x: 0, y: 0 }; // intermediate node
        i = {};
      //console.log(i);
      nodes.push(i);
      //links.push({ source: s, target: i }, { source: i, target: t });
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
              d => d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
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

    var ringPath0 = svg.selectAll("g.connected-ring").data(connectedRing);

    var ringPath = ringPath0
      .enter()
      .append("g")
      .attr(
        "class",
        d =>
          `segment ${(d.data.type === "eyeball_asn_noprobe" &&
            "eyeball-no-probe") ||
            "eyeball-probe"}`
      )
      .call(p =>
        p
          .append("path")
          .attr(
            "d",
            d => connectedArcSegment.outerRadius(d => 240)(d)
            //connectedArcSegment.outerRadius(d => d.data.eyeball_pct + 220)(d)
          )
          .attr("class", "c-ring")
      )
      .call(
        p =>
          !props.hideText &&
          p
            .append("text")
            .text(d => d.data.orgName || d.data.name)
            .attr("data-asn", d => d.data.name)
            .attr("x", d => textOutLineSegment.centroid(d)[0])
            .attr("y", d => textOutLineSegment.centroid(d)[1])
            .attr(
              "text-anchor",
              d =>
                (textOutLineSegment.centroid(d)[0] < 0 && "end") ||
                (textOutLineSegment.centroid(d)[0] > 0 && "start") ||
                "middle"
            )
      )
      .merge(ringPath0);

    ringPath.exit().remove();

    // connectedRing.forEach(d => {
    //   const textCoords = textOutLineSegment.centroid(d);

    //   let group = svg
    //     .append("g")
    //     .attr(
    //       "class",
    //       `segment ${(d.data.type === "eyeball_asn_noprobe" &&
    //         "eyeball-no-probe") ||
    //         "eyeball-probe"}`
    //     );

    //   group
    //     .append("path")
    //     .attr(
    //       "d",
    //       connectedArcSegment.outerRadius(d => 240)(d)
    //       //connectedArcSegment.outerRadius(d => d.data.eyeball_pct + 220)(d)
    //     )
    //     .attr("class", "c-ring");

    //   if (!props.hideText) {
    //     group
    //       .append("text")
    //       .text(d.data.name)
    //       .attr("data-asn", d.data.name)
    //       .attr("x", textCoords[0])
    //       .attr("y", textCoords[1])
    //       .attr(
    //         "text-anchor",
    //         d =>
    //           (textCoords[0] < 0 && "end") ||
    //           (textCoords[0] > 0 && "start") ||
    //           "middle"
    //       );
    //   }
    // });

    var link0 = svg
      //.append("g")
      .selectAll(".link")
      .data(bilinks);

    var link = link0
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
      })
      .merge(link0);

    link0.exit().remove();

    var node0 = svg
      .selectAll("g.node")
      .data(nodes.filter(n => n.id || n.id === 0));

    var node = node0
      .enter()
      .append("g")
      .attr("class", n => `node ${this.nodeClass(n)}`)
      .call(parent =>
        parent
          .append("circle")
          //.select("circle")
          .attr("r", d => {
            const scalar =
              // (d.type === "eyeball_asn" && Math.max(d.eyeball_pct, BALL_MIN_SIZE)) ||
              // ((d.type === "transit_asn" || d.type === "ixp") &&
              d.conn_btwn_pct || props.ballMinSize;
            return Math.max(Math.log(scalar * props.scaleFactor) * 3.5, 2);
          })
      )
      .call(
        parent =>
          !props.hideText &&
          parent
            .append("text")
            .text(
              d =>
                (d.type !== "eyeball_asn" &&
                  d.type !== "eyeball_asn_noprobe" &&
                  (d.orgName || d.name)) ||
                ""
            )
            .attr("data-asn", d => d.name)
      )
      .merge(node0);

    node0.exit().remove();

    // node.append("circle").attr("r", d => {
    //   const scalar =
    //     // (d.type === "eyeball_asn" && Math.max(d.eyeball_pct, BALL_MIN_SIZE)) ||
    //     // ((d.type === "transit_asn" || d.type === "ixp") &&
    //     d.conn_btwn_pct || props.ballMinSize;
    //   return Math.max(Math.log(scalar * props.scaleFactor) * 3.5, 2);
    // });
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

    //node.exit().remove();

    // if (!props.hideText) {
    //   node
    //     .append("text")
    //     .text(
    //       d =>
    //         (d.type !== "eyeball_asn" &&
    //           d.type !== "eyeball_asn_noprobe" &&
    //           d.name) ||
    //         ""
    //     )
    //     .attr("data-asn", d => d.name);
    //  }

    var simulation = d3
      .forceSimulation()
      .force(
        "charge",
        d3.forceCollide().radius(d => (d.type !== "eyeball_asn" && 12) || 0)
      )
      .force(
        "x",
        d3.forceX(d => {
          let seg = connectedRing.find(c => c.data.name === d.name);
          //seg && console.log(eyeBallsRing.centroid(seg));
          return (seg && eyeBallsRing.centroid(seg)[0]) || 0;
          //return 0;
        })
      )
      .force(
        "y",
        d3.forceY(d => {
          let seg = connectedRing.find(c => c.data.name === d.name);
          //seg && console.log(eyeBallsRing.centroid(seg));
          return (seg && eyeBallsRing.centroid(seg)[1]) || 0;
        })
      )
      .nodes(nodes)
      .on("tick", ticked);

    //return { nodes: simulation.nodes(), links: links };
  };

  componentWillReceiveProps(nextProps) {
    if (this.state && nextProps.orgNames) {
      console.log("as2org loaded, looking up...");
      // now lookup all the organisation names for ASes
      // in two steps:
      // 1. lookup in a json file (from CAIDA) that we'll load async
      // 2. lookup with a call to RIPEstat
      // doing this sync should be fast, because the as2org file
      // is loaded async by the parent and then
      // propagates as a prop to this component when it has arrived
      // in parent.
      const unknownAses =
        !this.props.hideText &&
        this.replaceAs2OrgNames(this.state.asGraph.nodes, nextProps.orgNames);
      console.log(`not found in as2org :\t${unknownAses.length}`);
      unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
    }

    if (
      nextProps.month !== this.props.month ||
      nextProps.year !== this.props.year ||
      nextProps.day !== this.props.day
    ) {
      console.log("update now...");

      this.loadAsGraphData(nextProps).then(
        data => {
          console.log(this.state.asGraph.nodes);

          const d3GraphNodesLinks = this.renderD3Ring({
            ...this.props,
            data: {
              nodes: this.state.asGraph.nodes,
              edges: [...data.edges]
            }
          });
          this.setState({
            asGraph: data
          });
        },
        error => console.log(error)
      );
    }
  }

  componentDidMount() {
    // if (!this.props.countryCode) {
    //   console.log(this.props);
    //   return;
    // }

    this.loadAsGraphData(this.props).then(data => {
      // artificially reduce number of nodes
      //data.nodes = data.nodes.filter(d => d.id < 10);
      //data.edges = data.edges.filter(l => l.source < 10 && l.target < 10);
      const d3GraphNodesLinks = this.renderD3Ring({
        ...this.props,
        data: {
          nodes: [...data.nodes].sort((a, b) => {
            a.id < b.id;
          }),
          edges: [...data.edges]
        }
      });
      this.setState({
        asGraph: data
      });

      if (this.props.orgNames) {
        console.log("as2org loaded fast, looking up...");
        // now lookup all the organisation names for ASes
        // in two steps:
        // 1. lookup in a json file (from CAIDA) that we'll load async
        // 2. lookup with a call to RIPEstat
        // doing this sync should be fast, because the as2org file
        // is loaded async by the parent and then
        // propagates as a prop to this component when it has arrived
        // in parent.
        const unknownAses =
          this.props.orgNames &&
          !this.props.hideText &&
          this.replaceAs2OrgNames(
            this.state.asGraph.nodes,
            this.props.orgNames
          );
        console.log(`not found in as2org :\t${unknownAses.length}`);
        unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
      }
    });
  }

  render() {
    if (!this.props.countryCode) {
      console.log("skip rendering...");
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
          id={this.getRingId()}
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
