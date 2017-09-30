// .format() for strings
// First, checks if it isn't implemented yet.
if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}

// requires files in the right place
// requires jquery to have been loaded
// args:
//   d: d3 data elt
//   jquery_elt: a jquery_elt to put the resulting html at
function jedi_cell_detail_to_jquery_elt( proto, src_id , dst_id , jquery_elt ) {
   json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, src_id, dst_id );
   $.ajax({url: json_file, 
      async: true
   }).done(function( data ) {
      var txt = '<pre>{0}</pre>'.format( data['tracetxt'] );
      jquery_elt.html( txt );
   });
}


// Display the source and destination ASN of each cell
function jedi_cell_show_source_dest_asn( proto, src_as , dst_as , source_asn, dest_asn, pageX, pageY) {


        source_asn.style("display", "block");  //The tooltip appears
        dest_asn.style("display", "block");  //The tooltip appears
        
        source_asn.html( "Source ASN: <b>" + src_as +"</b>"  )
        .style("left", pageX - 270 + "px") 
        .style("top", pageY - 15 + "px");

        dest_asn.html( "Dest ASN: <b>" + dst_as +"</b>"  )
        .style("left", pageX - 110 + "px") 
        .style("top", pageY - 70 + "px");
              
}

// Display the traceroute information
function jedi_cell_show_traceroute_on_click( proto, src_id , dst_id , traceroute_detail, pageX, pageY) {

  if (proto == "v4"){
    u_proto = "v6";
  }else{
    u_proto = "v4";
  }

  json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, src_id, dst_id );
    $.ajax({url: json_file, 
      async: true
    

    ,"success": function(data) {

      as_path_str = "AS("+ proto + ") Path:</br>"
      for(var i in data['as_links']['ordered_as_path']){
        as_path_str += "{0}) ".format((parseInt(i) + 1)) + data['as_links']['ordered_as_path'][i] + "</br>";
      }

      var parsed_traceroute_one = parse_traceroute_info(data['tracetxt']);

      var txt = '<button style="text-align:center" type="button" onclick="close_details(0)">Close</button>';
      txt += '<pre><div id="as_path_fw" style="width: 100%;height: 164px;"><div id="as_path_a" style="width: 50%;float:left;"><div style="font-size:18px;margin-top:6px;margin-bottom:5px;">IP' + proto + ' Traceroute: </div>'
      txt +='<div class="as_path">' + as_path_str + '</div></div></div></br>'
      txt += '<div style="width:100%;"><h3>{0}</h3><b>{1}</b><div id="bars_one"></div><div id="trac_2"></div></div>'.format( proto, parsed_traceroute_one['first_line'] );
      txt += '<small>Grey bar: max median RTT of all hops.</small></br><small>Blue bar: median RTT of the hop.</small></pre>'
      traceroute_detail.style("display", "block"); 

    
      traceroute_detail.html( txt )
        .style("left", (pageX + 20) + "px") 
        .style("top", pageY + "px")


      json_file = "../common/details/{0}/{1}/{2}/latest.json".format( u_proto, src_id, dst_id );

    
    
      $.ajax({url: json_file, 
          async: true
          

          ,"success": function(data_u) {
              tmp_as_path = "";
              as_path_str = "AS("+ u_proto + ") Path:</br>"

              var parsed_traceroute_two = parse_traceroute_info(data_u['tracetxt']);

              for(var i in data_u['as_links']['ordered_as_path']){
                as_path_str += "{0}) ".format((parseInt(i) + 1)) + data_u['as_links']['ordered_as_path'][i] + "</br>";
              }
              tmp_as_path += '<div id="as_path_b" style="width:50%;float:right;"><div style="font-size:18px;margin-top:6px;margin-bottom:5px;">IP' + u_proto + ' Traceroute: </div>'
              tmp_as_path +='<div class="as_path">' + as_path_str + '</div></br>'

              $("#as_path_fw").append(tmp_as_path);
              $("#trac_2").append('<h3>{0}</h3><b>{1}</b><div id="bars_two"></div>'.format( u_proto,  parsed_traceroute_two['first_line']));
              
              maxRTT = parsed_traceroute_one['maxRTT']

              if(maxRTT < parsed_traceroute_two['maxRTT']){
                maxRTT = parsed_traceroute_two['maxRTT']
              }

              plot_bars(parsed_traceroute_one, maxRTT ,"#bars_one")

              plot_bars(parsed_traceroute_two, maxRTT ,"#bars_two")

          },


          "error": function(jqXHR, status, error) {
            
            plot_bars(parsed_traceroute_one, parsed_traceroute_one['maxRTT'] ,"#bars_one")

          }

    });

  },

    "error": function(jqXHR, status, error) {
        
  }
  

  });            
}


function parse_traceroute_info(traceroute_txt){
  arrayOfLines = traceroute_txt.match(/[^\r\n]+/g);

  var match_AS = /\(.*\)/
  var match_hostName = /\s[a-z0-9-.:]+ /;
  var match_RTTs = /\[([0-9]+[.][0-9]*)[(,\s+)]*(([0-9]+[.])[0-9]*[(,\s+)]*)?(([0-9]+[.])[0-9]*[(,\s+)]*)?\]/;
  var match_location = /\|.*\|/

  var traceroute_obj = {ASN: new Array(), hostName: new Array(), rtts: new Array(), median: new Array(), maxRTT: 0, location: new Array(), first_line: "" }

  traceroute_obj['first_line'] = arrayOfLines[0]
  //Parse every line of the traceroute
  for(var i = 1; i < arrayOfLines.length; i++){
    //RTTs
    RTTs_str = arrayOfLines[i].match(match_RTTs);
    
    if(RTTs_str == null){
      traceroute_obj['rtts'].push(['*','*','*'])
      traceroute_obj['median'].push(0)

    }else{
      RTTs_str = RTTs_str[0].replace('[','').replace(']','');
      tmp_l = RTTs_str.split(",").map(Number);
      traceroute_obj['rtts'].push(tmp_l);

      median = get_median(tmp_l)
      traceroute_obj['median'].push(median)
      
      if(traceroute_obj['maxRTT'] < median){
        traceroute_obj['maxRTT'] = median;
      }
    }

    //HostName
    hostName_str = arrayOfLines[i].match(match_hostName)
    if(hostName_str == null){
      traceroute_obj['hostName'].push('Uknown (*)')

    }else{
      traceroute_obj['hostName'].push(arrayOfLines[i].match(match_hostName)[0]);
    }

    //AS
    ASN_str = arrayOfLines[i].match(match_AS)
    if(ASN_str == null){
      traceroute_obj['ASN'].push('(AS*)');
    }else{
      traceroute_obj['ASN'].push(arrayOfLines[i].match(match_AS)[0]);
    }

    //Location
    Location_str = arrayOfLines[i].match(match_location)
    if(Location_str == null){
      traceroute_obj['location'].push('|*|')
    }else{
       traceroute_obj['location'].push(arrayOfLines[i].match(match_location)[0])
    }
    
  }

  return traceroute_obj;

}

function plot_bars(traceroute_obj, maxRTT, where){

  
  var code_to_append = '<div class="bar-chart"><div class="chart clearfix">'

  for (var i = 0; i < traceroute_obj['ASN'].length; i++){
    var text_str = ""
    var percent = 0
    if(traceroute_obj['median'][i] != '*'){
      percent = (traceroute_obj['median'][i]/maxRTT) * 100
    }
    
    var rtts_str = ""

    for(var y = 0; y < traceroute_obj['rtts'][i].length; y++){
      if(y == traceroute_obj['rtts'][i].length -1){
        rtts_str += traceroute_obj['rtts'][i][y]
      }else{
        rtts_str += traceroute_obj['rtts'][i][y] + " ";
      }
    }

    var text_str = i + ": " + traceroute_obj['ASN'][i] + " " + traceroute_obj['hostName'][i] + ' (' + rtts_str + ') ' + traceroute_obj['location'][i]

    code_to_append += '<div class="item"><div class="bar"><div class="item-progress" data-percent="' + percent + '">'
    code_to_append += '<div style="margin-left:4px;width:820px;overflow-y:hidden;overflow-x:scroll;height:14px;"><span class="title">' + text_str + '</span></div></div></div></div>'
    

  }
  code_to_append += '</div></div>'
  
  $(where).append(code_to_append);

  barChart();

}


function get_median(values){
  values.sort((a, b) => a - b);
  return (values[(values.length - 1) >> 1] + values[values.length >> 1]) / 2
}



function barChart(){
    $('.bar-chart').find('.item-progress').each(function(){
        var itemProgress = $(this),
        itemProgressWidth = $(this).parent().width() * ($(this).data('percent') / 100);
        itemProgress.css('width', itemProgressWidth);
    });
};
