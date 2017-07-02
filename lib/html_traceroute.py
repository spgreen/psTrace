
def create_html_traceroute_page(route_stats, source_ip, destination_ip, start_date, end_date, historical_routes):
    html_traceroute = ""
    html_historical = []

    if historical_routes:
        html_historical.append("<h2>Historical Routes</h2>")
        for h_route in historical_routes:
            html_historical.append("<p>{ts}</p>\n"
                                   "<table border='1'><tr><td>Hop:</td><td>IP:</td></tr>\n".format(ts=h_route["ts"]))
            for (index, hop) in enumerate(h_route["route"]):
                html_historical.append("<tr><td>{index}</td><td>{ip}</td></tr>\n".format(index=index+1, ip=hop))
            html_historical.append("</table>\n")
        html_historical = "".join(html_historical)

    for (index, hop) in enumerate(route_stats):
        threshold = str(hop["threshold"])
        if hop["status"] == "warn":
            html_status = "&#10008; - WARN: Latency > " + threshold
        elif hop["status"] == "okay":
            html_status = "&#10004; - OK"
        else:
            html_status = "&#10008; - UNKNOWN: " + threshold

        route = "<tr><td>{index}</td><td>{domain}</td><td>{ip}</td><td>{rtt} ms</td><td>{min} ms</td><td>{median} ms</td><td>{threshold} ms</td><td>{web_status}</td></tr>\n"
        html_traceroute += route.format(index=index+1, web_status=html_status, **hop)

    traceroute_web_page = ("<!DOCTYPE html>\n"
                           "<html>\n"
                           "<head>\n"
                           "<meta charset='UTF-8'>\n"
                           "<meta http-equiv='refresh' content='1800'>\n"
                           "<style>\n"
                           "</style>\n"
                           "</head>\n"
                           "<body>\n"
                           "<h2>Traceroute: {source_ip} to {destination_ip}</h2>\n"
                           "<p><strong>Latest Test:</strong>{end_date}</p>\n"
                           "<p><strong>Source Node: </strong>{source_ip}<br>\n"
                           "<strong>Destination node: </strong>{destination_ip}</p>\n"
                           "<p><strong>Median Hop RRT</strong> calculated from the last 7 days worth of traceroute data: <strong>{start_date} &#8594; {end_date}</strong>\n"
                           "<table border='1'>\n"
                           "<tr><td>Hop:</td><td>Domain:</td><td>IP:</td><td>RTT:</td><td>Min. RTT:</td><td>Median RTT:</td><td>Threshold (Upper Fence RTT):</td><td>Notification:</td></tr>\n"
                           "{traceroute}\n"
                           "</table>\n"
                           "{historical}\n"
                           "<br>\n"
                           "<hr>\n"
                           "<p style='color:grey; font-size:7pt;'>This page will refresh every 30 minutes</p>\n"
                           "</body>\n"
                           "</html>")

    return traceroute_web_page.format(source_ip=source_ip,
                                      destination_ip=destination_ip,
                                      start_date=start_date,
                                      end_date=end_date,
                                      traceroute=html_traceroute,
                                      historical=html_historical)


def create_matrix(matrix, end_date="", rdns=""):
    matrix_table = []
    table_header_contents = ""
    matrix_table_append = matrix_table.append
    for source in matrix:
        # Since matrix is nxn we can use source as destination label
        table_header_contents += "<td><div><span>{destination}</span></div></td>".format(destination=source)
        matrix_table_append("<tr><td>{source}</td>".format(source=source))

        for destination in matrix:
            trace = matrix[source][destination]
            matrix_table_append('<td id="{status}"><a href=".{fp_html}">{rtt}</a></td>'.format(**trace))
        #mat.append(['<td id="{status}"><a href=".{fp_html}">{rtt}</a></td>'.format(**matrix[source][destination]) for destination in matrix])
        matrix_table_append("</tr>\n")

    matrix_table = "<tr><td>S/D</td>{header}</tr>\n".format(header=table_header_contents) + "".join(matrix_table)

    html_header = ("<!DOCTYPE html>\n"
                   "<html>\n"
                   "<head>\n"
                   "<meta charset='UTF-8'>\n"
                   "<meta http-equiv = 'refresh' content ='1135'>\n"
                   "<style>\n"
                   " body {font-family: Arial, Helvetica, sans-serif;}\n"
                   " table {border-collapse: collapse; font-size: 100%; width: 75%;}\n"
                   " td {text-align:center; border: 1px solid #ddd; padding: 3px;}\n"
                   " a {font-size: 10pt; font-weight: bold; color: #000064; text-decoration: none;}\n"
                   "\n"
                   " tr:first-child {height:140px; white-space: nowrap;}\n"
                   " tr:first-child td {border: 0; text-align: center;}\n"
                   " tr:first-child > td > div{\n"
                   "  transform:\n"
                   "    /* Magic Numbers */\n"
                   "    translate(25px, 51px)\n"
                   "    /* 45 is really 360 - 45 */\n"
                   "    rotate(315deg);\n"
                   "  width: 30px;\n"
                   " }\n"
                   " tr:first-child > td > div > span{padding: 5px 5px;}\n"
                   " tr:nth-child(even) {background-color: #f2f2f2}\n"
                   "\n"
                   " #error0 {background-color: lightgreen}\n"
                   " #error1 {background-color: yellow}\n"
                   " #error2 {background-color: #FF1E1E}\n"
                   "\n"
                   " .link {fill: none; stroke: #666; stroke-width: 1.5px;}\n"
                   "\n"
                   " #okay {fill: green;}\n"
                   " .link.okay {stroke: green;}\n"
                   "\n"
                   " #unknown {fill: orange;}\n"
                   " .link.unknown{stroke: orange;}\n"
                   "\n"
                   " #warn {fill: red;}\n"
                   " .link.warn {stroke: red;}\n"
                   "\n"
                   " circle {fill: #ccc; stroke: #333; stroke-width: 1.5px;}\n"
                   "\n"
                   " text {font: 10px sans-serif; pointer-events: none;\n"
                   "  text-shadow: 0 1px 0 #fff, 1px 0 0 #fff, 0 -1px 0 #fff, -1px 0 0 #fff;\n"
                   "}\n"
                   "\n"
                   "</style>\n"
                   "<script src='http://d3js.org/d3.v3.min.js'></script>\n"
                   "<script src='traceroute_force_graph.json'></script>\n"
                   "\n"
                   "</head>")

    html_body = ("<body>\n"
                 " <h2>PerfSONAR Traceroute Matrix</h2>\n"
                 " <p><strong>Last updated:</strong> {end_date}</p>\n"
                 " <table>\n"
                 "{matrix}\n"
                 "</table>")

    html_footer = ("<script>\n"
                   "d3.json('traceroute_force_graph.json', function(link_data){\n"
                   "    var links = link_data;\n"
                   "\n"
                   "//sort links by source, then target\n"
                   "links.sort(function(a,b) {\n"
                   "    if (a.source > b.source) {return 1;}\n"
                   "    else if (a.source < b.source) {return -1;}\n"
                   "    else {\n"
                   "        if (a.target > b.target) {return 1;}\n"
                   "        if (a.target < b.target) {return -1;}\n"
                   "        else {return 0;}\n"
                   "    }\n"
                   "});\n"
                   "//any links with duplicate source and target get an incremented 'linknum'\n"
                   "for (var i=0; i<links.length; i++) {\n"
                   "    if (i != 0 &&\n"
                   "        links[i].source == links[i-1].source &&\n"
                   "        links[i].target == links[i-1].target) {\n"
                   "            links[i].linknum = links[i-1].linknum + 1;\n"
                   "        }\n"
                   "    else {links[i].linknum = 1;};\n"
                   "};\n"
                   "var nodes = {};\n"
                   "// Compute the distinct nodes from the links.\n"
                   "links.forEach(function(link) {\n"
                   "  link.source = nodes[link.source] || (nodes[link.source] = {name: link.source, size: link.size });\n"
                   "  link.target = nodes[link.target] || (nodes[link.target] = {name: link.target, value: link.value});\n"
                   "});\n"
                   "\n"
                   "var width = 1300,\n"
                   "    height = 1250;\n"
                   "\n"
                   "var force = d3.layout.force()\n"
                   "    .nodes(d3.values(nodes))\n"
                   "    .links(links)\n"
                   "    .size([width, height])\n"
                   "    .linkDistance(48)\n"
                   "    .charge(-300)\n"
                   "    .gravity(0.075)\n"
                   "    .on('tick', tick)\n"
                   "    .start();\n"
                   "\n"
                   "var svg = d3.select('body').append('svg')\n"
                   "    .attr('width', width)\n"
                   "    .attr('height', height);\n"
                   "\n"
                   "// Per-type markers, as they don't inherit styles.\n"
                   "svg.append('defs').selectAll('marker')\n"
                   "    .data(['warn', 'okay', 'unknown'])\n"
                   "  .enter().append('marker')\n"
                   "    .attr('id', function(d) { return d; })\n"
                   "    .attr('viewBox', '0 -5 10 10')\n"
                   "    .attr('refX', 15)\n"
                   "    .attr('refY', -1.5)\n"
                   "    .attr('markerWidth', 6)\n"
                   "    .attr('markerHeight', 6)\n"
                   "    .attr('orient', 'auto')\n"
                   "  .append('path')\n"
                   "    .attr('d', 'M0,-5L10,0L0,5');\n"
                   "var path = svg.append('g').selectAll('path')\n"
                   "    .data(force.links())\n"
                   "  .enter().append('path')\n"
                   "    .attr('class', function(d) { return 'link ' + d.type; })\n"
                   "    .attr('marker-end', function(d) { return 'url(#' + d.type + ')'; });\n"
                   "\n"
                   "var circle = svg.append('g').selectAll('circle')\n"
                   "    .data(force.nodes())\n"
                   "  .enter().append('circle')\n"
                   "    .attr('r', 8)\n"
                   "    .attr('r', function(d) {  if (typeof d.size != 'undefined' || d.size != null) {return d.size;} else {return  8; }} )\n"
                   "    .style('fill', function(d) {  if (typeof d.size != 'undefined' || d.size != null) {return '#545454'} else if (d.value != null) {return 'white'} })\n"
                   "    .call(force.drag);\n"
                   "\n"
                   "var text = svg.append('g').selectAll('text')\n"
                   "    .data(force.nodes())\n"
                   "  .enter().append('text')\n"
                   "    .attr('x', -40)\n"
                   "    .attr('y', '.31em')\n"
                   "    .text(function(d) { return d.name; });\n"
                   "// Use elliptical arc path segments to doubly-encode directionality.\n"
                   "function tick() {\n"
                   "  path.attr('d', linkArc);\n"
                   "  circle.attr('transform', transform);\n"
                   "  text.attr('transform', transform);\n"
                   "}\n"
                   "function linkArc(d) {\n"
                   "  var dx = d.target.x - d.source.x,\n"
                   "      dy = d.target.y - d.source.y,\n"
                   "      //dr = Math.sqrt(dx * dx + dy * dy);\n"
                   "      dr = 225/d.linknum;\n"
                   "  return 'M' + d.source.x + ',' + d.source.y + 'A' + dr + ',' + dr + ' 0 0,1 ' + d.target.x + ',' + d.target.y;\n"
                   "}\n"
                   "function transform(d) {\n"
                   "  return 'translate(' + d.x + ',' + d.y + ')';\n"
                   "}\n"
                   "});\n"
                   "</script>\n"
                   "</body>\n"
                   "</html>")

    return "\n".join([html_header.strip(), html_body.format(matrix=matrix_table, end_date=end_date).strip(), html_footer.strip()])