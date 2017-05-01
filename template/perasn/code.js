d3.select("body").append("div").attr("class", "tooltipTraceroutes").style("display", "none");
var traceroute_details = d3.select("body").append("div").attr("class", "tooltipTraceroutes").style("display", "none");

function sortNumber(a,b) {
  return a - b;
}

$(function () {

  d3.json("../common/details/MsmDescr.json", function(error,data) {

    var load_first_asn = null
    
    var asns_list = []

    for (i in data["ASV4"]){
      asns_list.push(data["ASV4"][i])
    
    }
    asns_list = asns_list.sort(sortNumber)
    console.log(asns_list)
    for (i in asns_list){
      if(i==0) load_first_asn = data["ASV4"][i]
      
      $('#selectASN').append('<option value="'+ asns_list[i] +'">AS ' + asns_list[i] +'</option>');
    }

    loadASN(load_first_asn);
  });
    
});
        


function fetchTraceroute(proto, src_id, dst_id, traceroute_detail, pageX, pageY){

  json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, src_id, dst_id );
    $.ajax({url: json_file, 
      async: true
    }).done(function( data_forward ) {
      data_fwd = data_forward
      msm_id_forward = data_fwd.msm_id

      json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, dst_id, src_id );
            $.ajax({url: json_file, 
              async: true
            }).done(function( data_reverse ) {
              data_rv = data_reverse
              msm_id_reverse = data_rv.msm_id

              var txt = '<button style="text-align:center" type="button" onclick="close_details()">Close</button> <pre>{0}</b><b>Reverse path</b></br>{1}</pre>'.format(data_fwd["tracetxt"], data_rv["tracetxt"]);
              
              traceroute_detail.style("display", "block"); 

              traceroute_detail.html( txt )
                .style("left", (pageX + 20) + "px") 
                .style("top",  pageY + "px")
      });
  });
}

function close_details(){

  traceroute_details.style("display", "none");

}

        

function loadASN(name){
  var data_to_plot = []


  $.getJSON( name+ ".json", function( data ) {
    data_to_plot['name'] = "Source AS " +name;
    data_to_plot['children'] = [];

    for (var type in data['facets']){
          
      var dst_tmp = [];
      dst_tmp['name'] = type + " (" + Object.keys(data['facets'][type]['asns']).length + " Destination ASNS)";
      dst_tmp['children'] = [];
         
      for (var dst_asn in data['facets'][type]['asns']){


        dict_of_results = []
          
        for (var result in data['facets'][type]['asns'][dst_asn]){

          var result_tmp = [];
                 
          asn_name_str = "AS " + dst_asn
          result_tmp['name'] = []

          str_tmp = data['facets'][type]['asns'][dst_asn][result]["src_prb_id"] + " -> "
          str_tmp += data['facets'][type]['asns'][dst_asn][result]["dst_prb_id"] + " (" + data['facets'][type]['asns'][dst_asn][result]["proto"] +  ') (Source Probe Id -> Dest Probe Id)'

          result_tmp['name'] = str_tmp;

          if (dict_of_results[asn_name_str] == undefined ){
            dict_of_results[asn_name_str] = []
          }
          dict_of_results[asn_name_str].push({name: str_tmp, 
            src_id: data['facets'][type]['asns'][dst_asn][result]["src_prb_id"],
            dst_id: data['facets'][type]['asns'][dst_asn][result]["dst_prb_id"],
            proto: data['facets'][type]['asns'][dst_asn][result]["proto"]

          })
              
        }
              
              
        for (var item in dict_of_results){

            dst_tmp['children'].push({name: item, children: dict_of_results[item]})
            
        }
              
      } 

      data_to_plot['children'].push(dst_tmp);
    }
    d3.select("svg").remove();

    loadvis(data_to_plot)

  });
}

function loadvis(data_to_plot){

  var margin = {top: 30, right: 20, bottom: 30, left: 20},
  width = 960 - margin.left - margin.right,
  barHeight = 20,
  barWidth = width * .8;

  var i = 0,
      duration = 400,
      root;

  var tree = d3.layout.tree()
      .nodeSize([0, 20]);

  var diagonal = d3.svg.diagonal()
      .projection(function(d) { return [d.y, d.x]; });

  var svg = d3.select("#graph").append("svg")
      .attr("width", width + margin.left + margin.right)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");


  data_to_plot.x0 = 0
  data_to_plot.y0 = 0
  update(root = data_to_plot);

  function update(source) {

    // Compute the flattened node list. TODO use d3.layout.hierarchy.
    var nodes = tree.nodes(root);

    var height = Math.max(500, nodes.length * barHeight + margin.top + margin.bottom);

    d3.select("svg").transition()
        .duration(duration)
        .attr("height", height);

    d3.select(self.frameElement).transition()
        .duration(duration)
        .style("height", height + "px");

    // Compute the "layout".
    nodes.forEach(function(n, i) {
      n.x = i * barHeight;
    });

    // Update the nodes…
    var node = svg.selectAll("g.node")
        .data(nodes, function(d) { return d.id || (d.id = ++i); });

    var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
        .style("opacity", 1e-6);

    // Enter any new nodes at the parent's previous position.
    nodeEnter.append("rect")
        .attr("y", -barHeight / 2)
        .attr("height", barHeight)
        .attr("width", barWidth)
        .style("fill", color)
        .on("click", click);

    nodeEnter.append("text")
        .attr("dy", 3.5)
        .attr("dx", 5.5)
        .text(function(d) {
              return d.name; 
          })

    // Transition nodes to their new position.
    nodeEnter.transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
        .style("opacity", 1);

    node.transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
        .style("opacity", 1)
      .select("rect")
        .style("fill", color);

    // Transition exiting nodes to the parent's new position.
    node.exit().transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
        .style("opacity", 1e-6)
        .remove();

    // Update the links…
    var link = svg.selectAll("path.link")
        .data(tree.links(nodes), function(d) { return d.target.id; });

    // Enter any new links at the parent's previous position.
    link.enter().insert("path", "g")
        .attr("class", "link")
        .attr("d", function(d) {
          var o = {x: source.x0, y: source.y0};
          return diagonal({source: o, target: o});
        })
      .transition()
        .duration(duration)
        .attr("d", diagonal);

    // Transition links to their new position.
    link.transition()
        .duration(duration)
        .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(duration)
        .attr("d", function(d) {
          var o = {x: source.x, y: source.y};
          return diagonal({source: o, target: o});
        })
        .remove();

    // Stash the old positions for transition.
    nodes.forEach(function(d) {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  // Toggle children on click.
  function click(d) {
    if (d.children) {
      d._children = d.children;
      d.children = null;
    } else {
      d.children = d._children;
      d._children = null;
    }
    if(d.src_id != undefined){

      fetchTraceroute(d.proto, d.src_id, d.dst_id, traceroute_details, d3.event.pageX, d3.event.pageY);

    }
    update(d);
  }

  function color(d) {
    return d._children ? "#3182bd" : d.children ? "#c6dbef" : "#fd8d3c";
  }
}