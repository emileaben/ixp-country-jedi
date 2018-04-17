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

  nodeClass = d =>
    (d.type === "eyeball_asn" && d.transits && "eyeball-with-transit") ||
    (d.type === "eyeball_asn_noprobe" && "eyeball-no-probe") ||
    (d.type === "eyeball_asn" && "eyeball") ||
    (d.type === "transit_asn" && "transit") ||
    (d.type === "ixp" && "ixp") ||
    "";

  simulation = d3
    .forceSimulation()
    .force(
      "charge",
      d3.forceCollide().radius(d => {
        return (d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe" && 0) || 24;
      })
    )
    .force(
      "x",
      d3.forceX(d => {
        let segAngle = this.state.segAngles[d.id];
        return (segAngle && segAngle[0]) || 0;
      })
    )
    .force(
      "y",
      d3.forceY(d => {
        let segAngle = this.state.segAngles[d.id];
        return (segAngle && segAngle[1]) || 0;
      })
    );

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
        console.log(`inject from as2org\t: ${orgName.name} (${node.name})`);
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
        // manipulate the DOM directly
        const textNode = document.querySelector(`text[data-asn="${asn}"]`);
        if (textNode) {
          textNode.textContent = orgName.split(/_|\.| |\,/)[0];
        }
        const newAsNode = this.asGraph.nodes.find(n => n.name === asn);
      }
    }
  };

  loadAsGraphData = async ({ year, month, day, countryCode }) => {
    const countryDataForDateUrl = `${
      this.props.dataBaseUrl
    }${year}-${month}-${day}/${countryCode.toUpperCase()}/eyeballasgraph/asgraph.json`;

    let response = await fetch(countryDataForDateUrl);
    let data = await response.json();
    console.log("as-graph loaded without errors.");
    console.log(data);
    return data;
  };

  // One stop-shop for transforming
  // the input data from the json files to the actual format
  // we need to diff it efficiently with
  // the the state.asGraph data-structure.
  //
  // data       : raw input from asgraph.json file
  // returns data: { nodes, links }
  asGraph = { nodes: [], edges: [] };

  transformAsGraphData(nextAsGraph) {
    const toInteger = name => {
      var hash = 0,
        i,
        chr;
      if (name.length === 0) return hash;
      for (i = 0; i < name.length; i++) {
        chr = name.charCodeAt(i);
        hash = (hash << 5) - hash + chr;
        hash |= 0; // Convert to 32bit integer
      }
      return hash;
    };

    const toLinkClass = (s, t, type) => {
      return `link ${s.type.replace("_asn", "")}-${t.type.replace(
        "_asn",
        ""
      )} ${type}`;
    };

    const isNewGraph = this.asGraph.nodes.length === 0;

    const nodeSplicer = () => {
      this.asGraph.nodes.forEach((cn, idx) => {
        const matchNIdx = nextAsGraph.nodes
          .map(nn => toInteger(nn.name))
          .indexOf(cn.id);

        // Nodes is not in the next set of nodes, so delete it.
        if (matchNIdx < 0) {
          console.log(`node ${cn.name} deleted...`);
          this.asGraph.nodes.splice(idx, 1);
          nodeSplicer();
        }
      });
    };

    nodeSplicer();

    nextAsGraph.nodes.forEach(n => {
      const matchNIdx = this.asGraph.nodes
        .map(n => n.id)
        .indexOf(toInteger(n.name));

      // Add to the end of the array if the node is new.
      if (isNewGraph || matchNIdx < 0) {
        console.log(`new node ${n.name} (${toInteger(n.name)}) pushed...`);
        this.asGraph.nodes.push({ ...n, id: toInteger(n.name) });
      }

      // Replace the existing node if the attributes have changed.
      if (matchNIdx >= 0 && this.asGraph.nodes[matchNIdx].type !== n.type) {
        console.log(`change node ${n.name}...`);
        this.asGraph.nodes[matchNIdx].type = n.type;
        this.asGraph.nodes[matchNIdx].conn_btwn_pct = n.conn_btwn_pct;
      }
    });

    const edgeSplicer = () => {
      this.asGraph.edges.forEach((ce, idx) => {
        console.log(ce);
        console.log(idx);
        const matchEIdx = nextAsGraph.edges
          .map(ne =>
            toInteger(
              `${nextAsGraph.nodes[ne.source].name}-${
                nextAsGraph.nodes[ne.target].name
              }`
            )
          )
          .indexOf(ce[4]);

        if (matchEIdx < 0) {
          console.log(
            `edge ${ce[0].name}-${ce[2].name} (${
              this.asGraph.edges[idx][4]
            }) deleted...`
          );
          this.asGraph.edges.splice(idx, 1);
          edgeSplicer();
        }
      });
    };

    edgeSplicer();

    nextAsGraph.edges.forEach(e => {
      const sourceN = nextAsGraph.nodes.find(n => n.id === e.source),
        targetN = nextAsGraph.nodes.find(n => n.id === e.target);

      const edgeId = toInteger(`${sourceN.name}-${targetN.name}`);

      // For some reason some edges AS1-AS2 end up in the json file twice in both directions.
      // So that makes four lines connecting AS1 and AS2. We don't want that.
      // So we filter out duplicates by skipping testing for isNewGraph === true.
      if (this.asGraph.edges.map(n => n[4]).indexOf(edgeId) < 0) {
        console.log(`new edge ${sourceN.name}-${targetN.name} pushed...`);
        this.asGraph.edges.push([
          this.asGraph.nodes[
            this.asGraph.nodes.map(n => n.id).indexOf(toInteger(sourceN.name))
          ],
          {},
          this.asGraph.nodes[
            this.asGraph.nodes.map(n => n.id).indexOf(toInteger(targetN.name))
          ],
          toLinkClass(sourceN, targetN, e.type),
          edgeId
        ]);
      }
    });

    // 'archive' the state of the graph.
    this.setState({
      asGraph: { nodes: this.asGraph.nodes, edges: this.asGraph.edges }
    });
  }

  renderConnectedRing = ({ svg, update }) => {
    const arcTween = a => {
      var i = d3.interpolate(this._current, a);
      this._current = i(0);
      return t => connectedArcSegment(i(t));
    };

    var segAngles = {};

    var connectedRing = d3
      .pie()
      .padAngle(0.01)
      .endAngle(
        TAU *
          (this.asGraph.nodes
            .filter(
              d => d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
            )
            // calculate which percentage we're actually representing,
            // so that we can have an open ring.
            .reduce((acc, cur) => acc + cur.eyeball_pct, 0) /
            100)
      )
      .value(d => d.eyeball_pct);

    const eyeBallsRing = d3
      .arc()
      .innerRadius(220)
      .outerRadius(220);

    const connectedArcSegment = d3
      .arc()
      .innerRadius(220)
      .outerRadius(240);
    //.endAngle(Math.PI / 2);

    const textOutLineSegment = d3
      .arc()
      .innerRadius(245)
      .outerRadius(245);

    var ringPath0 = svg
      .datum(
        this.asGraph.nodes.filter(
          d => d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
        ),
        d => d.id
      )
      .selectAll("g.connected-ring", d => d.id)
      .data(connectedRing, d => d.id);

    if (!update) {
      ringPath0
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
              connectedArcSegment //.outerRadius(d => 240)(d)
              //connectedArcSegment.outerRadius(d => d.data.eyeball_pct + 220)(d)
            )
            .attr("class", "c-ring")
        )
        .call(
          p =>
            !this.props.hideText &&
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
        .each(d => {
          segAngles[d.data.id] = eyeBallsRing.centroid(d);
          this._current = d;
        });
      this.setState({ ringPath: ringPath0 });
    }

    const updateRing = () => {
      //console.log(this._current);
      ringPath0 = this.state.ringPath.data(connectedRing, d => d.id);
      ringPath0.transition().duration(750);
      //.attrTween("d", arcTween.bind(this));

      ringPath0.enter().each(d => {
        segAngles[d.data.id] = eyeBallsRing.centroid(d);
        this._current = d;
      });
    };

    //.merge(ringPath0);

    ringPath0.exit().remove();

    if (update) {
      updateRing();
    }

    this.setState({ segAngles: segAngles });
  };

  renderD3Ring = ({ update }) => {
    if (!this.state) {
      console.log("skipping ring rendering (not good)...");
      return;
    }

    const data = this.asGraph,
      props = this.props;
    console.log("render ring...");
    console.log(data);
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
    const positionNode = d => {
      return `translate(${d.x},${d.y})`;
    };

    const svg = d3.select(`svg#${this.getRingId()}`, d => d.id);

    this.renderConnectedRing({
      svg,
      update: update
    });

    var link = svg
      //.append("g")
      .selectAll(".link", d => d[4])
      .data(this.asGraph.edges, d => d[4]);

    link.exit().remove();

    var link = link
      .enter()
      .append("path")
      .attr("class", d => d[3])
      .merge(link);

    var node = svg.selectAll("g.node").data(this.asGraph.nodes, d => d.id);

    node.exit().remove();

    var node = node
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
      .merge(node);

    if (!update) {
      this.simulation.on("tick", ticked).nodes(this.asGraph.nodes);
    } else {
      this.simulation.on("tick", ticked).nodes(this.asGraph.nodes);
      this.simulation.alpha(1).restart();
    }
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
        this.replaceAs2OrgNames(
          this.asGraph.nodes.filter(n => !n.orgName),
          nextProps.orgNames
        );
      console.log(`not found in as2org :\t${unknownAses.length}`);
      unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
    }

    if (
      nextProps.month !== this.props.month ||
      nextProps.year !== this.props.year ||
      nextProps.day !== this.props.day
    ) {
      console.log("update now...");
      this.loadAsGraphData({
        ...nextProps,
        countryCode: this.props.countryCode
      }).then(
        data => {
          const nextAsGraph = this.transformAsGraphData(data);
          this.renderD3Ring({ update: true });
        },
        error => console.log(error)
      );
    }
  }

  componentDidMount() {

    this.loadAsGraphData(this.props).then(data => {
      const tData = this.transformAsGraphData(data);
      this.renderD3Ring({ update: false });

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
          this.replaceAs2OrgNames(this.asGraph.nodes, this.props.orgNames);
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
