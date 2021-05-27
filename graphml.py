#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import re

#TODO rename ports in edges, make sure to target outports when nessessary
nodemap = "e"

#indent text within another block for propper nesting
def indent(string):
    indentation = "  "
    return (indentation + string.replace("\n", "\n" + indentation))#.strip()
# ~ <graphml
  # ~ xmlns="http://graphml.graphdrawing.org/xmlns"

  # ~ xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        # ~ xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns
          # ~ http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
def make_document(content):
    return '<?xml version="1.0" encoding="UTF-8"?>\n'\
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n\n'\
           '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'\
           '  xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n'\
           '    http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n\n'\
           '    <key id="type" for="node" attr.name="nodetype" attr.type="string"/>\n'\
           '    <key id="location" for="node" attr.name="location" attr.type="string" />\n\n\n'\
           '  %s\n'\
           '\n\n</graphml>' % indent(content)

def make_edge(from_ , to, src_port, dst_port, type):
    return f'<edge source="{from_}" target="{to}" sourceport="{src_port}" targetport="{dst_port}">\n'\
         f'  <data key="type">{type}</data>\n'\
         f'</edge>'\

'''
id:       string,
name:     string,
location: string,
inPorts:  Port[],
outPorts: Port[],
props:    Map<string, string>,
subGraph: string = ""
'''

props_to_save = { #name in graphml: #name in IR node:
                  #   ↓                ↓
                    "type":         "name",
                    "functionName": "functionName",
                    "value":        "value",
                    "operator":     "operator",
                    "location":     "location",
                    "callee":       "callee",
                }

def make_graph(id, contents):
    return f'<graph id="{id}" edgedefault="directed">\n{indent(contents)}\n</graph>'

def make_node(node):
    
    def is_parent(n1, n2):
        global nodemap
        if not "nodes" in nodemap[n1]:
            return False
        if any([n for n in nodemap[n1]["nodes"] if n["id"]==n2]):
            return True
        return False
    
    def make_edges():    
        edges_string = ""
        if "edges" in node:
            for e in node["edges"]:
                source_port_type = "in" if is_parent(e[0]["nodeId"], e[1]["nodeId"]) else "out"
                target_port_type = "out" if is_parent(e[1]["nodeId"], e[0]["nodeId"]) else "in"
                
                edges_string += "\n" + make_edge(
                e[0]["nodeId"],e[1]["nodeId"],
                source_port_type + str(e[0]["index"])
                , target_port_type + str(e[1]["index"]), 
                e[0]["type"]["name"])
        return edges_string
    
    props_str =  "\n".join(
                    [f'<data key=\"{key}\">{node[ir_name]}</data>'
                    for key, ir_name in props_to_save.items()
                    if ir_name in node])
    #<port name="in0" type="integer" />
    ports_str = ""
    if "inPorts" in node:
        ports_str =  "".join(
                    [f'<port name=\"in{n}\" type=\"{port["type"]["name"]}\"/>\n'
                        for n, port in enumerate(node["inPorts"])]
                   )
                   
    if "outPorts" in node:
        ports_str +=  "\n".join(
                    [f'<port name=\"out{n}\" type=\"{port["type"]["name"]}\"/>'
                        for n, port in enumerate(node["outPorts"])]
                   )

    if "nodes" in node and node["nodes"]:
        contents = "\n".join([make_node(node) for node in node["nodes"]])
        contents += make_edges()
        contents = make_graph(node["id"]+"_graph", contents)
    elif "branches" in node:
        contents  = make_node(node["condition"])
        contents += make_node(node["branches"][0]) + make_node(node["branches"][1])
        contents += make_edges()
        contents  = make_graph(node["id"]+"_graph", contents)
    else:
        contents = make_edges()
        # ~ edges_string = make_edges()
        # ~ if edges_string:
            # ~ contents     = make_graph(node["id"]+"_graph", edges_string)
        
    
        
    
        
    return f'<node id=\"{node["id"]}\">\n'\
           f'{indent(props_str)}\n'\
           f'{indent(ports_str)}\n'\
           f'{indent(contents)}\n'\
           f'</node>\n'\

def emit(IR, nodes):
    global nodemap
    nodemap = nodes
    # ~ print ([n for n in nodes])
    graph    = make_graph("id", make_node(IR))
    document = make_document(graph)
    document = re.sub("\n\s*\n", "\n", document)
    # ~ document = re.sub("\n[ ]*?\n", "\n", document)
    # ~ open("/home/alexm/temp.gml", "w").write(document)
    return document

def main(args):
    print ("here is an example graph: \n")
    edge     = make_edge("node1", "node2", 0, 1, "Binary")
    graph    = make_graph("id", edge)

    document = make_document(graph)
    import os
    os.system ("echo '%s'| pygmentize -l xml" % document)
    
        # ~ xmllint --format xmlfile.xml | pygmentize -l xml | less
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
