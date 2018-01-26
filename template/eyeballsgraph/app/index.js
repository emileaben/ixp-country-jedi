import * as d3 from "d3";

const SCALEFACTOR = 2;
const DATA_URL = "asgraph-2.json";
const schema = {
  eyeball: "eyeball_asn",
  ixp: "ixp_asn",
  transit: "transit_asn"
};
const WIDTH = 1440,
  HEIGHT = 750;

const getForceRadial = d =>
  (d.type === "eyeball_asn" && 210) || (d.type === "transit_asn" && 140) || 70;

const nodeClass = d =>
  (d.type === "eyeball_asn" && "eyeball") ||
  (d.type === "transit_asn" && "transit") ||
  "";

d3.json(DATA_URL, function(error, data) {
  console.log((error && error) || "loaded without errors");
  console.log(data);
  //   const ticked = () => {
  //     link
  //       .attr("x1", d => d.source.x)
  //       .attr("y1", d => d.source.y)
  //       .attr("x2", d => d.target.x)
  //       .attr("y2", d => d.target.y);
  //     node
  //       .attr("cx", function(d) {
  //         return d.x;
  //       })
  //       .attr("cy", function(d) {
  //         return d.y;
  //       });
  //   };

  function ticked() {
    link.attr("d", positionLink);
    node.attr("transform", positionNode);
  }

  const positionLink = d => {
    return (
      (d[3] === "i" &&
        `M ${d[0].x},${d[0].y} S ${d[1].x},${d[1].y} ${d[2].x},${d[2].y}`) ||
      `M ${d[0].x},${d[0].y} A 0,0 0 0 1 ${d[2].x} ${d[2].y}`
    );
  };
  const positionNode = d => `translate(${d.x},${d.y})`;

  const svg = d3.select("svg");

  var div = d3
    .select("body")
    .append("div")
    .attr("class", "tooltip");

  var nodes = data.nodes,
    nodeById = d3.map(nodes, function(d) {
      return d.id;
    }),
    links = data.edges,
    bilinks = [];

  links.forEach(function(link) {
    console.log(link.type);
    var s = (link.source = nodeById.get(link.source)),
      t = (link.target = nodeById.get(link.target)),
      //i = { index: 100, vx: 0, vy: 0, x: 0, y: 0 }; // intermediate node
      i = {};
    console.log(i);
    nodes.push(i);
    links.push({ source: s, target: i }, { source: i, target: t });
    //link.source.type === "eyeball_asn" &&
    //  link.target.type === "transit_asn" &&
    bilinks.push([s, i, t, link.type]);
  });

  var link = svg
    //.append("g")
    .selectAll(".link")
    .data(bilinks)
    .enter()
    .append("path")
    .attr("class", d => {
      console.log(d);
      const linkClass =
        (d[0].type === "transit_asn" &&
          d[2].type === "transit_asn" &&
          "transit-transit") ||
        (d[0].type === "eyeball_asn" && d[2].type === "ixp" && "eyeball-ixp") ||
        (d[0].type === "ixp" && d[2].type === "eyeball_asn" && "ixp-eyeball") ||
        (d[0].type === "ixp" && d[2].type === "transit_asn" && "ixp-transit") ||
        (d[0].type === "eyeball_asn" && d[2].type === "transit_asn" && "eyeball-transit") ||
        (d[0].type === "transit_asn" && d[2].type === "eyeball_asn" && "transit-eyeball") ||
        (d[0].type === "ixp" && d[2].type === "ixp" && "ixp-ixp") ||
        d[0].type;
      return `link ${linkClass} ${d[3]}`;
    });

  var node = svg
    //.append("g")
    .selectAll(".circle")
    .data(nodes.filter(d => d.id))
    .enter()
    .append("circle")
    .attr("r", d => {
      const scalar =
        (d.eyeball_pct && d.eyeball_pct) ||
        (d.conn_btwn_pct && d.conn_btwn_pct) ||
        1;
      return Math.max(Math.log(scalar * SCALEFACTOR) * 3.5, 2);
    })
    .attr("class", nodeClass)
    .on("mouseover", function(d) {
      const g = d3.select(this);
      div.style("opacity", 0.9);
      div
        .html(
          `<div class="tooltip"><h4>${d.name}</h5><p>${d.eyeball_pct}</p><div>`
        )
        .attr("left", `${d.x}px`)
        .attr("top", `${d.y}px`);
    })
    .on("mouseout", function(d) {
      div.style("opacity", 0);
    });
  //node.append("text").text(d => `${d.name} ${d.eyeball_pct}`);
  // .append("text")
  // .attr("")

  var simulation = d3
    .forceSimulation()
    .force("charge", d3.forceCollide().radius(10))
    //.force("link", d3.forceLink(data.edges).distance(110))
    .force(
      "link",
      d3
        .forceLink(data.edges)
        //.distance(120)
        .strength(0.0)
    )
    .force("r", d3.forceRadial(getForceRadial))
    .nodes(nodes)
    .on("tick", ticked);

  simulation.force("link").links(links);

  // var simulation = d3.forceSimulation().force("link", d3.forceLink().distance(1250).strength(0.001));
  // simulation.nodes(nodes).on("tick", ticked);
  // simulation.force("link").links(links);
});
