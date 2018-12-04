import React from "react";

import * as d3 from "d3";
import "../../../styles/eyeballsgraph.less";

import { SvgToolTip } from "../ui-elements/tooltip.jsx";

// TODO: reconcile the local SvgToolTip with the ui-components library
// is it used by measurement-detail and now tailored for that.
// import { SvgToolTip } from "@ripe-rnd/ui-components";

const TAU = 2 * Math.PI;

function NoSnapshotException(jsonMsg) {
  this.error = jsonMsg;
  this.name = "NoSnapshotException";
}

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
  /*
 * This component renders a graph for one country and one date (a `snapshot`).
 * 
 * It uses a d3.pie to render the ring and a d3.forceSimulation (force graph) to render it.
 * 
 * In order to allow the updates to function correctly please take into account:
 * - d3 uses the .enter()[.append()], exit()[.remove()] and .merge() functions to take cues how to update the graph.
 *   First the initial data is associated with the d3 data structure with .data(<DATASTRUCTURE>). Nothing happens still.
 *   Only when .nodes(DATA_STRUCTURE) is invoked will the graph be rendered or updated.
 * - everything between .nodes() and .enter() is performed on the OLD graph, everything between .enter() and .merge()
 *   is performed on the NEW elements in the datastructure. And everything after merge() is performed on both.
 *   Read more here: https://bl.ocks.org/mbostock/3808218 (general update pattern)
 * 
 * We keep a distinct array on `this.asGraph` (`ringSegments`) for bookkeeping the segments of the circle (although 
 * they are calculated from the same set of nodes). The elements in the array are references to the this.asGraph.nodes,
 * so that we only have to mutate once the original inserted node.
 * This ringSegments array is consumed by the d3.pie that forms the outer ring. 
 * Note that this pie reassembles its data state from the DOM (`selectAll('.segments').data()`) and then compares 
 * to the updated state from `this.asGraph.ringSegments`.
 * 
 * The most important aspect of the datastructure fed into d3 is that it needs to be ONE MUTABLE DATASTRUCTURE -
 * in this component it is called `this.asGraph`.
 * So for every update of the graph the arrays `this.asGraph.nodes` and `this.asGraph.edges` get new elements by
 * performing a push on them, or by performing a splice on them. This complete structure is then fed to d3 again for
 * an update by doing this.simulation.nodes(this.asGraph.nodes).
 * 
 * One side-effect of this mutation (pun intended) is that we *cannot* just feed a transformed datastructure directly
 * a json file into the graph as an update. That would be a completely new datastructure and, even though we use
 * the same set of Ids and set the d => d.id everywhere the update WILL BE BOTCHED. So the onlyway is to go over
 * the original datastructure and mutate it painstakingly according to the changed data, thus creating
 * a state machine.
 * 
 * Just as the `this.asGraph` needs to be a mutable data-structure keeping state for the data, the graph state itself,
 * needs to be a mutable data-structure that is alive throughout the lifetime of the component.
 * This is why the graph state *cannot* live on the react state: the react state needs to be immutable!
 * Hence we create a class property called `this.simulation` (the force graph) and `this.connectedRing` (the outer ring)
 * that contain the complete state for the graph.
 * 
 * Also note that this component goes out on its own to resolve ASNs to names, both by downloading the as2org.json file and
 * resolving with calls to RIPEstat.
 */
  constructor(props) {
    super(props);
    this.state = {
      segAngles: {},
      error: null,
      tooltip: null
    };
  }

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

  /*
  * This is the class property that holds the state for the d3 force graph
  * throughout the lifetime of the component.
  * 
  * Forcing IXPs and Transits into their own orbit looks nicer, but
  * unfortunately that keeps on resulting in transits being drawn over
  * each other.
  * 
  * Also doing multiple force("charge", ...) calls doesn't seem to work.
  */
  simulation = d3
    .forceSimulation()
    // .force(
    //   "charge",
    //   d3.forceRadial(d => (d.type === "ixp" && 60) || 140).strength(0.8)
    // )
    .force(
      "charge",
      d3.forceCollide().radius(d => (d.type === "ixp" && 20) || 30)
    );

  textOutLineSegment = d3
    .arc()
    .innerRadius(245)
    .outerRadius(245);

  // Resolve the ASN to the holder name using RIPEstat
  resolveAsToName = async asn => {
    const fetchUrl = `${this.props.asResolverUrl}${asn}`;
    let response = await fetch(fetchUrl);
    let data = await response.json();
    return data.data.holder;
  };

  showToolTip = (d, i) => {
    const scalar = d.conn_btwn_pct || this.props.ballMinSize;
    const fontSize = 10,
      lineHeight = fontSize + 2,
      marginHor = 1.2 * fontSize,
      isEyeball =
        d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe" || false,
      // Offset the tooltip with ring-size + twice the margin
      dx =
        Math.max(Math.log(scalar * this.props.scaleFactor) * 3.5, 2) +
        1.5 * marginHor,
      dy = ((isEyeball && 6) || 4.5) * lineHeight + 2 * marginHor;
    this.setState({
      tooltip: (
        <SvgToolTip
          header={
            (isEyeball && "END USER NETWORK") ||
            (d.type === "ixp" && "INTERNET EXCHANGE") ||
            (d.type === "transit_asn" && "TRANSIT PROVIDER")
          }
          x={d.x}
          y={d.y}
          dx={dx}
          dy={dy}
          fontsize={fontSize}
          minwidth={100}
          textlines={[
            d.type === "eyeball_asn" && d.transits && "also provides transit",
            //d.type === "eyeball_asn" && d.transits && " ",
            d.type === "eyeball_asn_noprobe" && "not measured",
            " ",
            d.name,
            d.type !== "ixp" && { header: "name", content: d.orgName || "-" },
            isEyeball && {
              header: "end users",
              content: `${(Math.round(d.eyeball_pct * 100) / 100).toFixed(1)}%`
            },
            d.type !== "eyeball_asn_noprobe" && {
              header: "betweenness",
              content: `${Math.round(d.conn_btwn_pct * 100 / 100).toFixed(1)}%`
            }
          ].filter(t => t)}
        />
      )
    });
  };

  hideToolTip = (d, i) => {
    this.setState({
      tooltip: null
    });
  };

  // Resolve ASNs en bloque to names using as2org.json (from CAIDA)
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
        const bgRect = document.querySelector(`rect[data-asn=${node.name}`);

        // add the orgName to the node, so it can be stored in the components
        // state later on.
        node.orgName = orgName.name.split(/\.| |\,/)[0].replace(/_/g, " ");

        if (textNode) {
          const shortOrgName = orgName.name.split(/\.| |\,/)[0].replace(/_/g, " ");
          // Manipulate DOM directly,
          // not sweet, but this is D3 territory, so we cant' use React components here.
          textNode.textContent = shortOrgName;
          if (bgRect) {
            const curWidth = bgRect.getAttribute("width"),
              curX = bgRect.getAttribute("x"),
              nextWidth = 20 + shortOrgName.length * 8;
            bgRect.setAttribute("width", 20 + shortOrgName.length * 8);

            if (textNode.getAttribute("text-anchor") === "end") {
              bgRect.setAttribute("x", curX - (nextWidth - curWidth));
            }
          }
        }
      } else {
        unknownAses.push(node.name);
      }
    }

    return unknownAses;
  };

  // Inserts the ASNs into the DOM directly.
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
        const bgRect = document.querySelector(`bgRect[data-asn="${asn}"]`);
        // add the orgName to the node, so it can be stored in the components
        // state later on.
        const nodeNr = this.asGraph.nodes.findIndex(n => n.name === asn);
        if (this.asGraph.nodes[nodeNr]) {
          this.asGraph.nodes[nodeNr].orgName = orgName.split(/_|\.| |\,/)[0];
        }

        if (textNode) {
          const shortOrgName = orgName.split(/_|\.| |\,/)[0];
          // Manipulate DOM directly
          textNode.textContent = shortOrgName;
          if (bgRect) {
            const curWidth = bgRect.getAttribute("width"),
              curX = bgRect.getAttribute("x"),
              nextWidth = 20 + shortOrgName.length * 8;
            bgRect.setAttribute("width", 20 + shortOrgName.length * 8);

            if (textNode.getAttribute("text-anchor") === "end") {
              bgRect.setAttribute("x", curX - (nextWidth - curWidth));
            }
          }
        }
      }
    }
  };

  loadAsGraphData = async ({ year, month, day, countryCode }) => {
    const countryDataForDateUrl = `${
      this.props.dataBaseUrl
    }${year}-${month}-${day}/${countryCode.toUpperCase()}/eyeballasgraph/asgraph.json`;

    let response = await fetch(countryDataForDateUrl).catch(err => {
      console.log(
        `snapshot ${countryCode} ${year}/${month}/${day} does not exist.`
      );

      // 40x does not throw a NetworkError but a TypeError which is *not* propagated.
      // Beware that a CORS error *does* throw a NetworkError, so then a .catch would work.
      throw new NoSnapshotException({
        msg: `Sorry, there is no data available for this country at this date`,
        countryCode,
        year,
        month,
        day
      });
    });

    if (!response.ok) {
      throw new NoSnapshotException({
        msg: `Sorry, there is no data available for this country at this date`,
        countryCode,
        year,
        month,
        day
      });
    }
    let data = await response.json();
    return data;
  };

  /* 
  * this.asGraph holds the current state of the data associated
  * with the graph.
  * 
  * BE SURE TO MUTATE THIS STRUCTURE BEFORE FEEDING IT INTO d3.nodes
  * DO NOT USE IMMUTABLY BY COPYING. It will botch updates to the graph.
  */
  asGraph = { nodes: [], edges: [], ringSegments: [] };

  transformAsGraphData(nextAsGraph) {
    /* Transforms the data from snapshot files to the format used in the state machine.
     * Updates the state machine by mutating `this.asGraph`.
     * Right now, it features the sub-structures:
     * nodes        : stores all the transformed nodes, including the ones in the ring.
     * edges        : stores all the transformed edges.
     * ringSegments : These are references to the nodes for the ones in the outer ring.
     *
     * Note that the `id` and `index` field in the input data are *not* used, instead
     * a id field is generated from the `name` field (holding the AS) for the nodes
     * and the resolved names of source and target for the edges.
     * 
     * Note that it goes over the old data first to see which elements should be deleted
     * and then iterates over the new data to see what should be added or changed.
     * 
     * arguments:
     * nextAsGraph    : updated AS graph data from asgraph.json snapshot file
     * 
     * returns:
     * diddly, it mutates `this.asGraph` in place.
     * Also sets the React state, as an archive.
     */

    const toInteger = name => {
      // creates a uid for each node or
      // edge by hashing it into an integer.
      // This is the id used in the `this.asGraph` data-structure.
      // The id fields in the json data-files cannot be used for this
      // because their are not unique (they may be reused for different ASNs,
      // they're not unique across snapshots for the same country)
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

    /* NODES */

    // pass 1: delete

    // Deleting nodes from an array while iterating
    // over the structure needs some cleverness, c.q.
    // recursion.
    // Should be optimized probably with a trampoline.
    const nodeSplicer = () => {
      this.asGraph.nodes.forEach((cn, idx) => {
        const matchNIdx = nextAsGraph.nodes
          .map(nn => toInteger(nn.name))
          .indexOf(cn.id);

        // Nodes is not in the next set of nodes, so delete it.
        if (matchNIdx < 0) {
          let changedRingSegment = this.asGraph.ringSegments.findIndex(
            c => c.id === cn.id
          );
          //console.log(`node ${cn.name} deleted...`);
          this.asGraph.nodes.splice(idx, 1);
          if (changedRingSegment !== -1) {
            this.asGraph.ringSegments.splice(changedRingSegment, 1);
            //console.log(`ringSegment ${cn.name} deleted...`);
          }
          nodeSplicer();
        }
      });
    };

    nodeSplicer();

    // pass 2: replace and add.

    nextAsGraph.nodes.forEach(n => {
      const matchNIdx = this.asGraph.nodes
        .map(n => n.id)
        .indexOf(toInteger(n.name));
      const matchRSIdx = this.asGraph.ringSegments.findIndex(
        s => s.id === toInteger(n.name)
      );

      const newNode = { ...n, id: toInteger(n.name) };
      let changeNode =
        (matchNIdx >= 0 && this.asGraph.nodes[matchNIdx]) || null;
      let changeRingSegment =
        (matchRSIdx >= 0 && this.asGraph.ringSegments[matchRSIdx]) || null;

      // Add to the end of the array if the node is new.
      if (isNewGraph || matchNIdx < 0) {
        //console.log(`new node ${n.name} (${toInteger(n.name)}) pushed...`);
        //const newNode = { ...n, id: toInteger(n.name) };

        this.asGraph.nodes.push(newNode);
        if (n.type === "eyeball_asn" || n.type === "eyeball_asn_noprobe") {
          //console.log(`new ringSegment ${n.name} pushed...`);
          this.asGraph.ringSegments.push(newNode);
        }
      }

      // Replace the existing node if the attributes have changed.
      if (
        matchNIdx >= 0 &&
        (this.asGraph.nodes[matchNIdx].type !== n.type ||
          this.asGraph.nodes[matchNIdx].conn_btwn_pct !== n.conn_btwn_pct ||
          this.asGraph.nodes[matchNIdx].eyeball_pct !== n.eyeball_pct)
      ) {
        // console.log(
        //   `change node ${changeNode.name} ${changeNode.type} -> ${n.type}`
        // );
        // console.log(
        //   `change node ${changeNode.name} conn_btwn_pct ${
        //     changeNode.conn_btwn_pct
        //   } -> ${n.conn_btwn_pct}`
        // );
        // console.log(
        //   `change node ${changeNode.name} eyeball_pct ${
        //     changeNode.eyeball_pct
        //   } -> ${n.eyeball_pct}`
        // );

        this.asGraph.nodes[matchNIdx].type = n.type;
        this.asGraph.nodes[matchNIdx].conn_btwn_pct = n.conn_btwn_pct;
        this.asGraph.nodes[matchNIdx].eyeball_pct = n.eyeball_pct;
      }
    });

    /* EDGES a.k.a. links (in d3 speak) */

    // pass 1: delete

    const edgeSplicer = () => {
      this.asGraph.edges.forEach((ce, idx) => {
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
          // console.log(
          //   `edge ${ce[0].name}-${ce[2].name} (${
          //     this.asGraph.edges[idx][4]
          //   }) deleted...`
          // );
          this.asGraph.edges.splice(idx, 1);
          edgeSplicer();
        }
      });
    };

    edgeSplicer();

    // pass 2: replace and add

    nextAsGraph.edges.forEach(e => {
      const sourceN = nextAsGraph.nodes.find(n => n.id === e.source),
        targetN = nextAsGraph.nodes.find(n => n.id === e.target);

      const edgeId = toInteger(`${sourceN.name}-${targetN.name}`);

      // For some reason some edges AS1-AS2 end up in the json file twice in both directions.
      // So that makes four lines connecting AS1 and AS2. We don't want that.
      // So we filter out duplicates by skipping testing for isNewGraph === true.
      if (this.asGraph.edges.map(n => n[4]).indexOf(edgeId) < 0) {
        //console.log(`new edge ${sourceN.name}-${targetN.name} pushed...`);
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

      const changeEdgeIdx = this.asGraph.edges.findIndex(e => e[4] === edgeId);
      if (changeEdgeIdx >= 0) {
        // console.log(
        //   `change edge ${edgeId} ${
        //     this.asGraph.edges[changeEdgeIdx][3]
        //   } -> ${toLinkClass(sourceN, targetN, e.type)}`
        // );
        this.asGraph.edges[changeEdgeIdx][3] = toLinkClass(
          sourceN,
          targetN,
          e.type
        );
      }
    });

    // 'archive' the state of the graph.
    // This isn't used anywhere, just for debugging purposes.
    this.setState({
      asGraph: {
        nodes: this.asGraph.nodes,
        edges: this.asGraph.edges,
        ringSegments: this.asGraph.ringSegments
      }
    });
  }

  connectedRing = d3
    .pie()
    .padAngle(0.01)
    .value(d => d.eyeball_pct);

  renderConnectedRing = ({ svg, update }) => {
    function arcTween(d) {
      var i = d3.interpolate(this._current, d);
      this._current = i(0);
      return function(t) {
        return connectedArcSegment(i(t));
      };
    }

    function findNeighborArc(i, data0, data1, key) {
      var d;
      return (d = findPreceding(i, data0, data1, key))
        ? { startAngle: d.endAngle, endAngle: d.endAngle }
        : (d = findFollowing(i, data0, data1, key))
          ? { startAngle: d.startAngle, endAngle: d.startAngle }
          : null;
    }

    // Find the element in data0 that joins the highest preceding element in data1.
    function findPreceding(i, data0, data1, key) {
      var m = data0.length;
      while (--i >= 0) {
        var k = key(data1[i]);
        for (var j = 0; j < m; ++j) {
          if (key(data0[j]) === k) return data0[j];
        }
      }
    }

    // Find the element in data0 that joins the lowest following element in data1.
    function findFollowing(i, data0, data1, key) {
      var n = data1.length,
        m = data0.length;
      while (++i < n) {
        var k = key(data1[i]);
        for (var j = 0; j < m; ++j) {
          if (key(data0[j]) === k) return data0[j];
        }
      }
    }

    const key = d => d.data.id;

    // Only use the nodes that should go in to the ring
    // var nextringSegments = nextAsGraph.nodes.filter(
    //   d => d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe"
    // );
    var segAngles = this.state.segAngles;

    //this.ringPath = svg.selectAll("g.connected-ring");
    this.ringPath = svg.selectAll(".segment");

    var data0 = this.ringPath.data(),
      data1 = this.connectedRing.endAngle(
        TAU *
          (this.asGraph.ringSegments.reduce(
            (acc, cur) => acc + cur.eyeball_pct,
            0
          ) /
            100)
      )(this.asGraph.ringSegments);

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

    this.ringPath = this.ringPath.data(data1, key);

    this.ringPath
      .enter()
      .append("g")
      .call(p =>
        p
          .append("path")
          .each(function(d, i) {
            this._current = findNeighborArc(i, data0, data1, key) || d;
            segAngles[d.data.id] = eyeBallsRing.centroid(d);
          })
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
      .merge(this.ringPath)
      .attr(
        "class",
        d =>
          `segment ${(d.data.type === "eyeball_asn_noprobe" &&
            "eyeball-no-probe") ||
            "eyeball-probe"}`
      );

    this.ringPath
      .exit()
      .datum(function(d, i) {
        return findNeighborArc(i, data1, data0, key) || d;
      })
      // .transition()
      // .duration(750)
      // .attrTween("d", arcTween)
      .remove();

    this.ringPath
      .transition()
      .duration(750)
      .attrTween("d", arcTween);

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
      .merge(link)
      .attr("class", d => d[3]);

    var node = svg.selectAll("g.node").data(this.asGraph.nodes, d => {
      if (d.type === "eyeball_asn" || d.type === "eyeball_asn_noprobe") {
        try {
          const sA = this.state.segAngles;
          d.fx = this.state.segAngles[d.id][0];
          d.fy = this.state.segAngles[d.id][1];
        } catch (e) {
          // This would happen if a node is updated and moves from the inner circle area
          // (a transit or ixp) to the outer ring (a end-user network).
          // In that case it gets moved to the center of the graph.
          console.error(`no segAngles for: ${d.id}`);
          d.fx = d.fy = 0;
        }
      }
      return d.id;
    });

    node.exit().remove();

    var node = node
      .enter()
      .append("g")
      .call(parent =>
        parent
          .append("circle")
          //.merge(node)
          //.select("circle")
          .attr("r", d => {
            const scalar =
              // (d.type === "eyeball_asn" && Math.max(d.eyeball_pct, BALL_MIN_SIZE)) ||
              // ((d.type === "transit_asn" || d.type === "ixp") &&
              d.conn_btwn_pct || props.ballMinSize;
            return Math.max(Math.log(scalar * props.scaleFactor) * 3.5, 2);
          })
          .on("mouseenter", this.showToolTip)
          .on("mouseleave", this.hideToolTip)
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
            .attr("class", "org-name")
      )
      // .call(parent =>
      //   parent
      //     .append("text")
      //     .text(d => `${d.name} (${Math.round(d.conn_btwn_pct * 10) / 10})`)
      //     .attr("class", "tooltip")
      //     .attr("dy", -15)
      // )
      .merge(node)
      // This call is only used when the circle is already present, i.e.
      // when the node is updated, hence the `'.select` instead of `.append`
      .call(parent =>
        parent
          //.append("circle")
          //.merge(node)
          .select("circle")
          .attr("r", d => {
            const scalar =
              // (d.type === "eyeball_asn" && Math.max(d.eyeball_pct, BALL_MIN_SIZE)) ||
              // ((d.type === "transit_asn" || d.type === "ixp") &&
              d.conn_btwn_pct || props.ballMinSize;
            return Math.max(Math.log(scalar * props.scaleFactor) * 3.5, 2);
          })
      )
      .attr("class", n => `node ${this.nodeClass(n)}`);

    if (!update) {
      this.simulation
        .on("end", () => {
          const unknownAses =
            this.props.primary &&
            this.replaceAs2OrgNames(
              this.asGraph.nodes.filter(n => !n.orgName),
              props.orgNames
            );
          console.log(`not found in as2org :\t${unknownAses.length}`);
          unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
        })
        .on("tick", ticked)
        .nodes(this.asGraph.nodes);
    } else {
      this.simulation
        .on("end", () => {
          const unknownAses =
            this.props.primary &&
            this.replaceAs2OrgNames(
              this.asGraph.nodes.filter(n => !n.orgName),
              props.orgNames
            );
          console.log(`not found in as2org :\t${unknownAses.length}`);
          unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
        })
        .on("tick", ticked)
        .nodes(this.asGraph.nodes);
      this.simulation.alpha(1).restart();
    }
  };

  componentWillReceiveProps(nextProps) {
    if (nextProps.orgNames) {
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
      nextProps.day !== this.props.day ||
      nextProps.countryCode !== this.props.countryCode
    ) {
      console.log("update now...");

      this.loadAsGraphData({
        ...nextProps,
        countryCode: nextProps.countryCode
      }).then(
        data => {
          // reset any error state that might have been set earlier on
          this.setState({ error: null });

          const nextAsGraph = this.transformAsGraphData(data);
          this.renderD3Ring({ update: true });
        },
        error => {
          this.asGraph = { nodes: [], edges: [], ringSegments: [] };
          this.setState({ error: error.error });
          this.renderD3Ring({ update: true });
        }
      );
    }
  }

  componentDidMount() {
    this.loadAsGraphData(this.props).then(
      data => {
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
          // propagated as a prop to this component when it has arrived
          // in parent.
          const unknownAses =
            this.props.orgNames &&
            !this.props.hideText &&
            this.replaceAs2OrgNames(this.asGraph.nodes, this.props.orgNames);
          console.log(`not found in as2org :\t${unknownAses.length}`);
          unknownAses.length > 0 && this.getOrgNamesFromRipeStat(unknownAses);
        }
      },
      error => {
        this.setState({ error: error.error });
      }
    );
  }

  render() {
    if (!this.props.countryCode) {
      console.log("skip rendering...");
      return (
        <div className="status-msg">
          <h5>{this.props.status}</h5>
        </div>
      );
    }

    return (
      <div>
        {this.state.error && (
          <div className="status-msg">
            <h5>{this.state.error.msg}</h5>
            <p>
              {this.state.error.countryCode} {this.state.error.year}-{
                this.state.error.month
              }-{this.state.error.day}
            </p>
          </div>
        )}
        {!this.props.primary && <PeerToPeerFabricFacts {...this.props} />}
        {
          <svg
            key="primary-graph"
            width="100%"
            viewBox="-400 -250 800 500"
            className={`p-t-p-fabric ${this.props.className || ""}`}
            transform={`scale(${this.props.scaleFactor / 2})`}
            id={this.getRingId()}
          >
            <defs>
              <linearGradient id="linear" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#05a" />
                <stop offset="100%" stopColor="#0a5" />
              </linearGradient>
            </defs>
            <circle
              r="240"
              cx="0"
              cy="0"
              className={`interior-circle ${this.state.error && "error-state"}`}
            />
            {this.state.tooltip}
          </svg>
        }
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
