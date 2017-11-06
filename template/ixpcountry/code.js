
//Global Variables
var rows, cols, cells, row_count, col_count, row_by_idx, data_n, proto, uniq_asns = [], filter_ASNs, _6to4;

var rows_f = [], cols_f = [], row_count_f, col_count_f, row_by_idx_f, ids_of_rows = [], ids_of_cols = [], cells_f = [];

// BEGIN CODE FOR SHARE LINK

//Hide show the share link box
function showShareLink(flag){
    if(flag == "show"){
        document.getElementById('shareDiv').style.display = 'none';
        document.getElementById('shareDetails').style.display = 'block';
    }else{
        document.getElementById('shareDiv').style.display = 'block';
        document.getElementById('shareDetails').style.display = 'none';
    }
    
}

//Create the share link on each update
function shareLink(ASN_LIST){
    var currentLocation = window.location.href.split("index.html")[0];
    var shareLink = currentLocation + "index.html";
    
    if(ASN_LIST == undefined || ASN_LIST == "all"){
        shareLink += "?ASNS=all"

    }else if(ASN_LIST.length > 0){
        shareLink += "?ASNS=";
        for (i in ASN_LIST){
            shareLink += ASN_LIST[i] + ",";
        }
    }else if(ASN_LIST.length == 0){
        shareLink += "?ASNS=none";
    }
    shareLink = shareLink + '&ipv=' + proto
    document.getElementById('shareURL').innerHTML = shareLink ;
    return;
}

// END CODE FOR SHARE LINK



function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}


//Display the number of selected ASNs
function numberOfASNshowingText(selectedASN){
    total_of_asns = uniq_asns.length + tmp_6to4.length
    document.getElementById("infoASNtext").innerHTML =  selectedASN.length + " of " + total_of_asns + " ASNs";
}

function filter_arguments(asn){
    //Remove AS from ASXXX
    if(Number.isInteger(Number(asn))){
        return asn
    
    }else if('AS' == asn.substring(0, 2)){
        return asn.substring(2,asn.length)
    
    }else{
        return asn
    }
}

function asn_list_from_url(){
        
    asns_list = getParameterByName('ASNS')

    if(asns_list != null){
        asns_list = asns_list.split(",");
    }else{
        return "all";
    }
    //Check if ASNs appear on the dataset
    var valid_ASNS_from_url = []

    //Check if url contains all ASNs 
    if (asns_list[0] == "all"){
        return "all";
    }else{
        //Check if given ASNs are valid numbers
        for (i in asns_list){
            asns_list[i] = filter_arguments(asns_list[i])
            if (! isNaN(asns_list[i])){
                valid_ASNS_from_url.push(Number(asns_list[i]))
            }else if(asns_list[i].substring(0,4) == '6to4'){
                valid_ASNS_from_url.push(asns_list[i])
            }
        }
        return valid_ASNS_from_url;
    }
}

function start_processing(){

    var asns_url = asn_list_from_url();

    function sortNumber(a,b) {
        return a - b;
    }
    tmp_6to4 = []
    if(proto == 'v4'){ 
        for (i in rows){
            if (!(uniq_asns.includes(Number(rows[i].asn_v4)))){
                uniq_asns.push(rows[i].asn_v4);
            }
        }
    }else{
        for (i in rows){

            if(rows[i].asn_v6 == null && _6to4.includes(Number(rows[i].id))){
                tmp_6to4.push('6to4' +  ' (v4: AS' + rows[i].asn_v4 + ')')
            }

            if (!(Number(rows[i].asn_v6) in uniq_asns)){
                uniq_asns.push(rows[i].asn_v6);
            }
        }
    }
    uniq_asns = Array.from(new Set(uniq_asns));
    uniq_asns.sort(sortNumber)

    for ( i in uniq_asns){
        if( (isInArray(uniq_asns[i], asns_url) || asns_url == "all") && asns_url != "none"){
            $("#listASNs").append(' <li class="list-group-item" data-checked="true">AS' + uniq_asns[i] + '</li>');
        }else{
            $("#listASNs").append(' <li class="list-group-item">AS' + uniq_asns[i] + '</li>');
        }
    }
    
    tmp_6to4 = Array.from(new Set(tmp_6to4));
    for ( i in tmp_6to4){
        if( (isInArray(tmp_6to4[i], asns_url) || asns_url == "all") && asns_url != "none"){
            $("#listASNs").append(' <li class="list-group-item" data-checked="true">' + tmp_6to4[i] + '</li>');
        }else{
            $("#listASNs").append(' <li class="list-group-item">' + tmp_6to4[i] + '</li>');
        }
    }

    init_filter_options();
    filter_ASNs = ret_checked_values().get();
    for (i in filter_ASNs){
        filter_ASNs[i] = filter_arguments(filter_arguments(filter_ASNs[i]))
    }
    numberOfASNshowingText(filter_ASNs);

    if(window.location.href.indexOf("all") > -1) {
       shareLink("all");
    }else{
        shareLink(filter_ASNs);
    }
    redraw();
}

function applyClearAll(){
    $(".list-group.checked-list-box .list-group-item").map(function () {
        $(this).attr('class', "list-group-item");
        $(this).removeAttr( "data-checked" );
        $(this).find("span").attr('class', "state-icon glyphicon glyphicon-unchecked");
    });
}

function applySelectAll(){
    $(".list-group.checked-list-box .list-group-item").map(function () {
        $(this).attr('class', "list-group-item list-group-item-primary active");
        $(this).attr("data-checked", "true" );
        $(this).find("span").attr('class', "state-icon glyphicon glyphicon-check");
    });
}

function ret_checked_values(){
    return $(".list-group.checked-list-box .list-group-item").map(function () {
        if($(this).attr('class') == "list-group-item list-group-item-primary active"){
            asn = $(this).text()
            return asn;
        }
    });
}


function applyFilter(){
    var checkedValues = $(".list-group.checked-list-box .list-group-item").map(function () {
        if($(this).attr('class') == "list-group-item list-group-item-primary active"){
            return $(this).text();
        }

    });
    filter_ASNs = ret_checked_values().get();
    
    for (i in filter_ASNs){
        filter_ASNs[i] = filter_arguments(filter_arguments(filter_ASNs[i]))
    }

    initVariables();
    numberOfASNshowingText(filter_ASNs);

    if(filter_ASNs.length == uniq_asns.length){
        shareLink("all");
    }else{
        shareLink(filter_ASNs);
    }
    redraw();
}

function initVariables(){
    rows_f = []
    cols_f = []
    ids_of_rows = []
    ids_of_cols = []
    cells_f = []
    row_count_f = []
}

function isInArray(value, array) {
    return array.indexOf(value) > -1;
}

function redraw(){
    if(proto == 'v4'){
        for (i in data_n['rows']){
            if( isInArray( (data_n['rows'][i].asn_v4).toString(),filter_ASNs)) {

                rows_f.push(data_n['rows'][i])
                ids_of_rows.push(data_n['rows'][i].id)
            }
            if( isInArray( (data_n['cols'][i].asn_v4).toString(),filter_ASNs)) {

                cols_f.push(data_n['cols'][i])
                ids_of_cols.push(data_n['cols'][i].id)
            }
        }
    }else{
        for (i in data_n['rows']){
            if (data_n['rows'][i].asn_v6 == null && _6to4.includes(data_n['rows'][i].id)){

                tmp_str = '6to4' +  ' (v4: AS' + data_n['rows'][i].asn_v4 + ')'
                if(isInArray(tmp_str,filter_ASNs)){
                    rows_f.push(data_n['rows'][i])
                    ids_of_rows.push(data_n['rows'][i].id)
                }

            }else{
                if( isInArray( (data_n['rows'][i].asn_v6).toString(),filter_ASNs)) {

                    rows_f.push(data_n['rows'][i])
                    ids_of_rows.push(data_n['rows'][i].id)
                }
            }

            if (data_n['cols'][i].asn_v6 == null && _6to4.includes(data_n['cols'][i].id)){

                tmp_str = '6to4' +  ' (v4: AS' + data_n['cols'][i].asn_v4 + ')'
                if(isInArray(tmp_str,filter_ASNs)){
                    cols_f.push(data_n['cols'][i])
                    ids_of_cols.push(data_n['cols'][i].id)
                }

            }else{
                if( isInArray( (data_n['cols'][i].asn_v6).toString(),filter_ASNs)) {
                    cols_f.push(data_n['cols'][i])
                    ids_of_cols.push(data_n['cols'][i].id)
                }
            }
        }
    }
    for (i in cells){
        
        if( isInArray(cells[i].col, ids_of_cols) && isInArray(cells[i].row, ids_of_rows) ){
            cells_f.push(cells[i])
        }

    }
    row_count_f = rows_f.length;
    col_count_f = cols_f.length;
    row_by_idx_f = _.indexBy(rows_f, 'id'); 

    //Delete previous visualization matrix
    d3.select("svg").remove();

    if(row_count_f > 0){
        plot_vizualization(rows_f, cols_f, cells_f, row_count_f, col_count_f, row_by_idx_f);
    }

}

//BEGIN CODE FOR MENU

var legends_button = document.getElementById('displayFilter');
legends_button.onclick = function() {
    var div = document.getElementById('filterASNs');
    if (div.style.display !== 'none') {
        div.style.display = 'none';
        document.getElementById('displayFilter').innerHTML = "Show Filter ASNs"

    }
    else {
        div.style.display = 'block';
        document.getElementById('displayFilter').innerHTML = "Hide Filter ASNs"
    }
};

var legends_button = document.getElementById('displayLegend');
legends_button.onclick = function() {
    var div = document.getElementById('legends');
    if (div.style.display !== 'none') {
        div.style.display = 'none';
        document.getElementById('displayLegend').innerHTML = "Show Legend"

    }
    else {
        div.style.display = 'block';
        document.getElementById('displayLegend').innerHTML = "Hide Legend"
    }
};

//END CODE FOR MENU


if( getParameterByName('ipv') == null || getParameterByName('ipv') == 'v4'){
    proto = 'v4'
    document.getElementById("infoIPv").innerHTML = "(IPv4)";
    document.getElementById("info_viewIPv").innerHTML = "<a href=\"index.html?ipv=v6\">IPv6</a>"
}else{
    proto = 'v6'
    document.getElementById("infoIPv").innerHTML = "(IPv6)";
    document.getElementById("info_viewIPv").innerHTML = "<a href=\"index.html?ipv=v4\">IPv4</a>"
}
   
//Read the main .json file 
d3.json("ixpcountry.{0}.json".format( proto ), function(error,data) {

    rows = data['rows'];
    cols = data['cols'];
    cells = data['cells'];
    row_count = rows.length;
    col_count = cols.length;
    row_by_idx = _.indexBy(rows, 'id'); 
    data_n = data;
    _6to4 = data['_6to4']

    start_processing();
});
    

var row_details = d3.select("body").append("div").attr("class", "tooltipASNs").style("display", "none");
var col_details = d3.select("body").append("div").attr("class", "tooltipASNs").style("display", "none");
var traceroute_details = d3.select("body").append("div").attr("class", "tooltipTraceroutes").style("display", "none");


function close_details(flag){
    switch(flag) {
        case 0:
            traceroute_details.style("display", "none");
            break;
        default:
            return;
    }
}

//If window resizes plot again
window.onresize = function() {
    initVariables();
    redraw();
};

  
function plot_vizualization(rows, cols, cells, row_count, col_count, row_by_idx) {

    var height = 1200;
    var width = height;
    var border_width = 200;

    var new_width = window.innerWidth;

    var zoom = d3.behavior.zoom()
        .scaleExtent([1, 10])
        .on("zoom", zoomed);

    // Set init value for zooma
    zoom.translate([((new_width*0.8)/4), 60]);

    var svg = d3.select("body")
        .append("svg")
        .attr("id", "map")
        .attr("width", "90%")
        .attr("height", "85%")
        .style("position", "absolute")
        .style("margin-left", "5%")
        .call(zoom);

    var map = svg.append("g");
    
    function zoomed(){
        map.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");  
    }


    map.attr("id", "adjacencyG")
    map.attr("transform", "translate(" + ((new_width*0.8)/3.2) + "," + 60 + ")scale(1)");


    var xScale = d3.scale.ordinal().rangeBands([0, width - border_width]); //width - border_width]);
    var yScale = d3.scale.ordinal().rangeBands([0, width - border_width]);//width - border_width]);
    var thinglist = [];
    var probe_info;
    var count = 0

    var sort_orders = {
         'id':     _.pluck( rows.sort( function(a,b) { return d3.ascending( a.id, b.id ) } ), 'id'),
         'asn_v4': _.pluck( rows.sort( function(a,b) { return d3.ascending( a.asn_v4, b.asn_v4 ) } ), 'id'),
         'asn_v6': _.pluck( rows.sort( function(a,b) { return d3.ascending( a.asn_v6, b.asn_v6 ) } ), 'id')
        };

    function get_label(proto, index, prefix){

        if(proto == 'v4'){
            if(row_by_idx[index].asn_v6 != row_by_idx[index].asn_v4 && row_by_idx[index].asn_v6 != null){
                return prefix + row_by_idx[ index ].asn_v4 + ' (v6: ' + prefix + row_by_idx[index].asn_v6 +')'
            }else{
                return prefix + row_by_idx[ index ].asn_v4
            }
        }else{
            if(row_by_idx[index].asn_v6 == null && _6to4.includes(row_by_idx[index].id)){
                tmp_str = '6to4' + ' (v4: AS' + row_by_idx[index].asn_v4 + ')'
                return tmp_str
            }else if(row_by_idx[index].asn_v6 != row_by_idx[index].asn_v4){
                return prefix + row_by_idx[index].asn_v6 + ' (v4: ' + prefix + row_by_idx[index].asn_v4 +')'
            }else{
                return prefix + row_by_idx[ index ].asn_v6 
            }
        }
    }

    if(proto == 'v4'){
        xScale.domain( sort_orders.asn_v4 )
        yScale.domain( sort_orders.asn_v4 )

        xAxis = d3.svg.axis().scale(xScale).orient("top").tickSize(2);
        yAxis = d3.svg.axis().scale(yScale).orient("left").tickSize(2);
        xAxis.tickFormat(function(d) { 
            return get_label(proto, d, 'AS');
        });
        yAxis.tickFormat(function(d) { 
            return get_label(proto, d, 'AS');
        });
    }else{
        xScale.domain( sort_orders.asn_v6 )
        yScale.domain( sort_orders.asn_v6 )

        xAxis = d3.svg.axis().scale(xScale).orient("top").tickSize(2);
        yAxis = d3.svg.axis().scale(yScale).orient("left").tickSize(2);

        xAxis.tickFormat(function(d) { 
            return get_label(proto, d, 'AS');
        });
        yAxis.tickFormat(function(d) { 
            return get_label(proto, d, 'AS');
        });
    }

    d3.select("#adjacencyG").append("g").attr("class",'axis').call(xAxis).selectAll("text").style("text-anchor", "end").attr("transform", "translate(-10,-10) rotate(90)");
    d3.select("#adjacencyG").append("g").attr("class",'axis').call(yAxis);
    /*
    function text_from_datacell( d ) {
        var txt = [];
        txt.push(d.data.in_country ? 'incc: yes' : 'incc: no');
        txt.push(d.data.via_ixp    ? 'ixp: yes' : 'ixp: no');
        txt.push("srcAS" + row_by_idx[ d.row ].asn_v4);
        txt.push("dstAS" + row_by_idx[ d.col ].asn_v4);
        txt.push("srcPrb" + d.row);
        txt.push("dstPrb" + d.col);
        return txt.join("\n");
    };
    */
    function cellcolor( d ) {
        // http://colorbrewer2.org/#type=diverging&scheme=BrBG&n=4
        if (  d.data.via_ixp &&   d.data.in_country) { return "#018571"; }
        if (! d.data.via_ixp &&   d.data.in_country) { return "#80cdc1";}
        if (  d.data.via_ixp && ! d.data.in_country) { return "#a6611a";}
        if (! d.data.via_ixp && ! d.data.in_country) { return "#dfc27d";}
        return "pink"; // should not happen
    };

    var boxes_viz = map.append('g')
        .attr('class', 'boxes')
        .selectAll('rect')
        .data( cells )
        .enter()
        .append("rect")
        .datum( function(d) { d.x = xScale( d.col ), d.y = yScale( d.row ) ; return d } )
        .attr('x', function(d) { return d.x } )
        .attr('y', function(d) { return d.y } )
        .attr('width', Math.floor(( width - border_width) / col_count ) -1)
        .attr('height', Math.ceil(( height - border_width) / col_count ) -1) 
        .on('mouseover', function (d) { 
            jedi_cell_show_source_dest_asn(proto, get_label(proto, d.row, ''), get_label(proto, d.col, '') , row_details,
            col_details, d3.event.pageX, d3.event.pageY)
         } )
        .on('mouseout', function (d){
            row_details.style("display", "none");
            col_details.style("display", "none");
        })
        .on('click', function (d){

            jedi_cell_show_traceroute_on_click( proto, d.row, d.col , traceroute_details, d3.event.pageX, d3.event.pageY)

        })
        .style('fill', cellcolor )
}


function init_filter_options(){
    $(function () {
        $('.list-group.checked-list-box .list-group-item').each(function () {
            
            // Settings
            var $widget = $(this),
                $checkbox = $('<input type="checkbox" class="hidden" />'),
                color = ($widget.data('color') ? $widget.data('color') : "primary"),
                style = ($widget.data('style') == "button" ? "btn-" : "list-group-item-"),
                settings = {
                    on: {
                        icon: 'glyphicon glyphicon-check'
                    },
                    off: {
                        icon: 'glyphicon glyphicon-unchecked'
                    }
                };
                
            $widget.css('cursor', 'pointer')
            $widget.append($checkbox);

            // Event Handlers
            $widget.on('click', function () {
                $checkbox.prop('checked', !$checkbox.is(':checked'));
                $checkbox.triggerHandler('change');
                updateDisplay();
            });
            $checkbox.on('change', function () {
                updateDisplay();
            });
              

            // Actions
            function updateDisplay() {
                var isChecked = $checkbox.is(':checked');

                // Set the button's state
                $widget.data('state', (isChecked) ? "on" : "off");

                // Set the button's icon
                $widget.find('.state-icon')
                    .removeClass()
                    .addClass('state-icon ' + settings[$widget.data('state')].icon);

                // Update the button's color
                if (isChecked) {
                    $widget.addClass(style + color + ' active');
                } else {
                    $widget.removeClass(style + color + ' active');
                }
            }

            // Initialization
            function init() {
                
                if ($widget.data('checked') == true) {
                    $checkbox.prop('checked', !$checkbox.is(':checked'));
                }
                
                updateDisplay();

                // Inject the icon if applicable
                if ($widget.find('.state-icon').length == 0) {
                    $widget.prepend('<span class="state-icon ' + settings[$widget.data('state')].icon + '"></span>');
                }
            }
            init();
        });
    });
}



//Code to support button copy (Share Link)
document.getElementById("copyButton").addEventListener("click", function() {
    copyToClipboard(document.getElementById("shareURL"));
});

function copyToClipboard(elem) {

    var targetId = "_hiddenCopyText_";
    var isInput = elem.tagName === "INPUT" || elem.tagName === "TEXTAREA";
    var origSelectionStart, origSelectionEnd;
    if (isInput) {

        target = elem;
        origSelectionStart = elem.selectionStart;
        origSelectionEnd = elem.selectionEnd;
    } else {

        target = document.getElementById(targetId);
        if (!target) {
            var target = document.createElement("textarea");
            target.style.position = "absolute";
            target.style.left = "-9999px";
            target.style.top = "0";
            target.id = targetId;
            document.body.appendChild(target);
        }
        target.textContent = elem.textContent;
    }

    var currentFocus = document.activeElement;
    target.focus();
    target.setSelectionRange(0, target.value.length);
    
    var succeed;
    try {
          succeed = document.execCommand("copy");
    } catch(e) {
        succeed = false;
    }

    if (currentFocus && typeof currentFocus.focus === "function") {
        currentFocus.focus();
    }
    
    if (isInput) {
        elem.setSelectionRange(origSelectionStart, origSelectionEnd);
    } else {
        target.textContent = "";
    }
    return succeed;
}   
