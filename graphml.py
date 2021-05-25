#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

#indent text within another block for propper nesting

#TODO rename ports in edges, make sure to target outports when nessessary

def indent(string):
    indentation = "  "
    return indentation + string.replace("\n", "\n" + indentation*2)

def make_document(content):
    return '<?xml version="1.0" encoding="UTF-8"?>\n'\
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"'\
           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'\
           'xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns'\
           'http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n'\
           '  <key id="type" for="node" attr.name="nodetype" attr.type="string" />\n'\
           '  <key id="location" for="node" attr.name="location" attr.type="string" />\n\n\n'\
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
                }

def make_node(node):
    props_str = ""
    
    for key, ir_name in props_to_save.items():
        if ir_name in node:
            props_str +=  f'<data key=\"{key}\">{node[ir_name]}</data>\n'
    
    if "nodes" in node and node["nodes"]:
        contents  = "\n".join([make_node(node) for node in node["nodes"]])
    elif "branches" in node:
        # ~ print (node["branches"])
        contents  = make_node(node["condition"])
        contents += make_node(node["branches"][0]) + make_node(node["branches"][1])
    else:
        contents = ""
    
    if "edges" in node:
        for e in node["edges"]:
            contents += "\n"+make_edge(e[0]["nodeId"],e[1]["nodeId"],e[0]["index"], e[1]["index"], e[0]["type"]["name"])
            
    return f'<node id=\"{node["id"]}\">\n'\
           f'{indent(props_str)}\n'\
           f'{indent(contents)}\n'\
           f'</node>'\

def make_graph(id, contents):
  return f'<graph id="{id}" edgedefault="directed">\n  {indent(contents)}\n</graph>'

def emit(IR):        
    graph    = make_graph("id", make_node(IR))
    document = make_document(graph)
    return document

def main(args):
    print ("here is an example graph: \n")
    edge     = make_edge("node1", "node2", 0, 1, "Binary")
    graph    = make_graph("id", edge)
    
    document = make_document(graph)
    import os
    os.system ("echo '%s'| pygmentize -l xml" % document)
    # ~ xmllint --format xmlfile.xml | pygmentize -l xml | less
   # print( document )
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
