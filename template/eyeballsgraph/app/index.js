import * as d3 from "d3";

const SCALEFACTOR = 100;

const getForceRadial = d =>
  (d.type === "prb" && 210) || (d.type === "asn" && 140) || 70;

const nodeClass = d =>
  (d.type === "prb" && "prb") || (d.type === "asn" && "asn") || "";

d3.json("asgraph.json", function(error, data) {
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

  function positionLink(d) {
    return (
      "M" +
      d[0].x +
      "," +
      d[0].y +
      "S" +
      d[1].x +
      "," +
      d[1].y +
      " " +
      d[2].x +
      "," +
      d[2].y
    );
  }

  function positionNode(d) {
    return "translate(" + d.x + "," + d.y + ")";
  }

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
    var s = (link.source = nodeById.get(link.source)),
      t = (link.target = nodeById.get(link.target)),
      i = {}; // intermediate node
    nodes.push(i);
    //links.push({ source: s, target: i }, { source: i, target: t });
    bilinks.push([s, i, t, link.source.type, link.target.type]);
  });

  var link = svg
    //.append("g")
    .selectAll(".link")
    .data(bilinks.map(l => [l[0],l[1],l[2]]))
    .enter()
    .append("path")
    .attr("class", d => { console.log(d); return `link ${d[2].type}` });

  var node = svg
    //.append("g")
    .selectAll(".circle")
    .data(nodes.filter(d => d.id))
    .enter()
    .append("circle")
    .attr("r", function(d) {
      return Math.max(Math.log(d.count * SCALEFACTOR) * 3.5, 2);
    })
    .attr("class", nodeClass)
    .on("mouseover", function(d) {
      const g = d3.select(this);
      div.style("opacity", 0.9);
      div
        .html(`<div class="tooltip"><h4>${d.name}</h5><p>${d.count}</p><div>`)
        .attr("left", `${d.x}px`)
        .attr("top", `${d.y}px`);
    })
    .on("mouseout", function(d) {
      div.style("opacity", 0);
    });
  //node.append("text").text(d => `${d.name} ${d.count}`);
  // .append("text")
  // .attr("")

  var simulation = d3
    .forceSimulation()
    .force("charge", d3.forceCollide().radius(8))
    //.force("link", d3.forceLink(data.edges).distance(110))
    .force(
      "link",
      d3
        .forceLink(data.edges)
        .distance(1750)
        .strength(0.0001)
    )
    .force("r", d3.forceRadial(getForceRadial))
    .nodes(nodes)
    .on("tick", ticked);

  simulation.force("link").links(links);

  // var simulation = d3.forceSimulation().force("link", d3.forceLink().distance(1250).strength(0.001));
  // simulation.nodes(nodes).on("tick", ticked);
  // simulation.force("link").links(links);
});
