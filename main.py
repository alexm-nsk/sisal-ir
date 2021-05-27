#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from parsimonious.grammar import Grammar
from parsimonious.nodes   import NodeVisitor

import pprint
import json

import os
import graphml

no_subs = ["Identifier", "Literal"]

#parameters:
move_nodes_from_empty_branches_to_parent = True

#TODO no arguments case
#TODO how to access a parent node in parsimonious
#TODO make chain function, that gets the top-level node containing required value

#--------------------------------------------------------------------------------

def get_location(node):

    text = node.full_text

    start_row    = text[:node.start].count("\n") + 1 # lines have to start from "1"
    start_column = len (  (text[:node.start].split("\n"))[-1]  )

    end_row      = text[:node.end].count("\n") + 1   # lines have to start from "1"
    end_column   = len (  (text[:node.end].split("\n"))[-1]  )

    return "{}:{}-{}:{}".format(start_row, start_column, end_row, end_column)

#--------------------------------------------------------------------------------

def unwrap_list(list_):

    while type(list_) == list:
        list_ = list_[0]
    return list_

#--------------------------------------------------------------------------------

class TreeVisitor(NodeVisitor):

    node_counter = 0
    functions = {}
    # Here we store parameters (as in input variables) of each node, addressed the
    # same way. Nodes like "function" and "if" must have those
    params = {}
    # Here we store all the nodes, addressed by their names like "node3"
    nodes  = {}
    edges  = []
    #--------------------------------------------------------------------------------

    def get_node_id(self):

        self.node_counter += 1

        return "node" + str(self.node_counter)

    #--------------------------------------------------------------------------------

    def visit_std_type(self, node, visited_children):
        return node.text

    #--------------------------------------------------------------------------------

    def visit_type(self, node, visited_children):
        return visited_children[0]

    #--------------------------------------------------------------------------------

    def generate_outports(self, retvals, node_id):
        return [{
                    "index" : n,
                    "nodeId" : node_id,
                    "type": {
                        "location" : "not applicable",# not always the case!
                        "name" : t
                    }
                }
                for n, t in enumerate (retvals)]

    #--------------------------------------------------------------------------------

    def generate_inports(self, args, nodeId):

        ports = []
        for n, a in enumerate(args):
            ports.append(dict(
                index  = n,
                nodeId = nodeId,
                type   = {"location" : "", "name": "integer"}
            ))
        return ports

    #--------------------------------------------------------------------------------
    # unpacks node lists defined by recursive grammar structures like:
    # type_list    = type (_ "," _ type)*
    #--------------------------------------------------------------------------------

    def unpack_rec_list(self, node):
        return [node[0]]    +    [r[-1] for r in node[1]]

    #--------------------------------------------------------------------------------
    def enum_print(self,obj):
        for n, o in enumerate(obj):
            print (n, ":", o)
    #--------------------------------------------------------------------------------

    def create_edge(self, node1_id, node2_id, src_index, dst_index):

        edge = [    {"index"  : src_index,
                     "nodeId" : node1_id,
                     "type"   : {
                        "location" : "",
                        "name"     : "integer" #TODO get actual type from node's port
                        }
                     }
                    ,
                    {"index"  : dst_index,
                     "nodeId" : node2_id,
                     "type"   : {
                        "location" : "",
                        "name"     : "integer" #TODO get actual type from node's port
                        }
                     }
                ]
        self.edges.append(edge)
        return edge

    #--------------------------------------------------------------------------------

    def visit_function(self, node, visited_children):
        node_id     = self.get_node_id()
        name        = visited_children[3]["identifier"]

        #--------------------------------------------------------------------------------
        # process args:
        #--------------------------------------------------------------------------------

        params   = []
        in_ports = []

        all_args  = self.unpack_rec_list( visited_children[7] )

        for arg_block in all_args:
            args        = arg_block[0]
            type_string = arg_block[-1]

            retvals     = self.unpack_rec_list( visited_children[11] )

            params      += [   # first - the name, second - the contents
                               [arg["identifier"],

                               {
                                   "index"    : n,
                                   "nodeId"   : node_id,
                                   "type":
                                   {
                                        "location" : arg["location"],
                                        "name"     : type_string
                                   }
                               }
                            ]
                           for n, arg in enumerate(args)
                           ]

            in_ports    += [ dict(
                             index  = n + len(in_ports), # we offset with len(in_ports)
                                                        # to keep proper indices order
                             nodeId = node_id,
                             type   = {"location" : arg["location"], "name": type_string}
                             )
                             for n, arg in enumerate(args)
                           ]

        #--------------------------------------------------------------------------------


        child_nodes = visited_children[-4]

        this_node = dict(
                         params       = params,
                                        # TODO make inports properly
                         inPorts      = in_ports,
                                        # TODO save outports for calls
                         outPorts     = self.generate_outports(retvals, node_id),
                         functionName = name,
                         nodes        = child_nodes,
                         id           = node_id,
                         name         = "Lambda",
                                        # TODO make edges
                         edges        = [self.create_edge(child_nodes[0]["id"],node_id, 0,0)],
                         location     = get_location(node),
                         )

        for child_node in this_node["nodes"]:
            child_node["parent_node"] = this_node["id"]

        self.nodes[node_id]  = this_node
        self.functions[name] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def visit_arg_def_list(self, node, visited_children):
        # due to recursive argument listing, the first argument and the rest are separated
        return self.unpack_rec_list (visited_children)

    #--------------------------------------------------------------------------------

    def get_all_nodes_in_a_row(self, sub_nodes, root):
        def _get_all_nodes_in_a_row_(node):
            #if root is identifier, we're done: add the edge and quit
            if (node["name"] == "Identifier"):
                root["edges"].append(self.create_edge(root["id"], root["id"], 0, 0))
                retval = []
            #otherwise, keep unpacking the subtree
            else:
                retval = [node]
                if "nodes" in node:

                    nodes = node["nodes"]

                    # process edges
                    for i, n in enumerate(nodes):
                        if n["name"] == "Identifier":
                            root["edges"].append(self.create_edge(root["id"], node["id"], 0, i))
                        else:
                            root["edges"].append(self.create_edge(n["id"], node["id"], 0, i))

                    #process sub_nodes
                    for n in node["nodes"]:
                        if not "nodes" in n:
                            # no more subnodes? append just this one
                            if not n["name"] == "Identifier":
                                retval.append(n)
                        else:
                            retval += _get_all_nodes_in_a_row_(n)

                    del (node["nodes"])
            return retval

        if (not "edges" in root): root["edges"] = []

        return _get_all_nodes_in_a_row_(sub_nodes)

    #--------------------------------------------------------------------------------

    def visit_if_else(self, node, visited_children):

        node_id   = self.get_node_id()
        then_node = unwrap_list(visited_children[6][0])
        else_node = unwrap_list(visited_children[10][0])

        cond_node = visited_children[2][0]

        def make_branch(node, name):
            branch_node_id = self.get_node_id()
            branch = dict(
                            nodes       = [],
                            id          = branch_node_id,
                            name        = name,
                            edges       = [self.create_edge(node["id"],branch_node_id,0,0)] if node["id"] !="not applicable" else [],
                            inPorts     = [],#\
                            outPorts    = [],#- filled out in the second pass
                            params      = [],#TODO do these!
                            location    = "not applicable",
                            parent_node = node_id,
                          )
            self.nodes[branch_node_id] = branch
            return branch

        then  = make_branch(then_node, "Then")
        then["nodes"] =self.get_all_nodes_in_a_row(then_node,then)

        else_ = make_branch(else_node, "Else")
        else_["nodes"] = self.get_all_nodes_in_a_row(else_node, else_)

        condition_node_id = self.get_node_id()

        cond_node["parent_node"] = condition_node_id

        cond  =    dict(
                         #nodes       = cond_node,
                         name        = "Condition",
                         edges       = [self.create_edge(cond_node["id"],condition_node_id,0,0)] if cond_node["id"] !="not applicable" else [],
                         id          = condition_node_id,
                         inPorts     = [],
                         outPorts    = [],
                         params      = [],#TODO do these!
                         location    = "not applicable",
                         parent_node = node_id,
                       )
        cond["nodes"] = self.get_all_nodes_in_a_row(cond_node, cond)
        self.nodes[condition_node_id] = cond

        this_node = dict(name      = "If",
                         nodes     = [],#leave empty
                         edges     = [],
                         inPorts   = [],
                         outPorts  = [],
                         params    = [], #TODO do these!
                         branches  = [then, else_],
                         condition = cond,
                         id        = node_id,
                         location  = get_location(node),
                         )

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    # TODO: replace identifiers with edges connecting current slot to master-node's input
    def visit_identifier(self, node, visited_children):

        node_id = "not applicable"
        this_node = dict(
                        name       = "Identifier",
                        identifier = node.text,
                        id         = node_id,
                        location   = get_location(node),
                        )

        return this_node

    #--------------------------------------------------------------------------------

    def visit_number(self, node, visited_children):

        node_id   = self.get_node_id()

        out_ports = [dict(index  = 0,
                                        nodeId = node_id,
                                        type   = {"location": "not applicable", "name": "integer"})]

        this_node = dict(
                         value    = int(node.text),
                         name     = "Literal",
                         id       = node_id,
                         outPorts = out_ports,
                         location = get_location(node),
                        )

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------
    op_to_type = {
        "<" : "boolean",
        ">" : "boolean",
        "+" : "integer",
        "-" : "integer",
        "*" : "integer",
    }
    def visit_bin(self, node, visited_children):

        node_id = self.get_node_id()

        left, _ ,op, _ ,right = visited_children
        left  = left[0]
        right = right[0]
        op    = op[0].text

        left ["parent_node"] = node_id
        right["parent_node"] = node_id

        # TODO get left and right types from left and right's out port types
        left_port =  dict( index  = 0,
                            nodeId = node_id,
                            type   = {"location": "not applicable",
                            "name": "integer"})

        right_port =  dict( index  = 1,
                            nodeId = node_id,
                            type   = {"location": "not applicable",
                            "name": "integer"})

        out_port =  dict( index  = 0,
                            nodeId = node_id,
                            type   = {"location": "not applicable",
                            "name": TreeVisitor.op_to_type[op]})

        this_node = dict(name        = "Binary",
                         nodes       = [left, right],
                         operator    = op,
                         id          = node_id,
                         location    = get_location(node),
                         inPorts     = [left_port, right_port],
                         outPorts    = [out_port]
                         )

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def visit_call(self, node, visited_children):

        node_id       = self.get_node_id()
        args          = [unwrap_list(self.unpack_rec_list(visited_children[5]))]

        #TODO count args, create ports for them, connect them with edges
        function_name = visited_children[1]["identifier"]

        this_node = dict(
                         callee   = function_name,
                         # TODO add a check that the call has the same in_ports as the function
                         inPorts  = self.generate_inports(args, node_id),
                         outPorts = [],#filled in second pass (see the "translate" method)
                         name     = "FunctionCall",
                         nodes    = args,
                         id       = node_id,
                         location = get_location(node),
                         )

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node

    #--------------------------------------------------------------------------------
    # returns a list of identifiers contained in the subtree under the specified node
    #--------------------------------------------------------------------------------

    def get_used_identifiers(self, node):
        def __get_used_identifiers__(node):
            result = []
            if node["name"] == "Identifier":
                result.append(node)

            if "nodes" in node:
                for n in node["nodes"]:
                    result += __get_used_identifiers__(n)

            if [] in result : result.remove([])

            return result

        return __get_used_identifiers__(node)

    #--------------------------------------------------------------------------------
    def set_edges_types(self):

        def is_parent(n1, n2):
            try:
                if not "nodes" in self.nodes[n1]:
                    return False
                if any([n for n in self.nodes[n1]["nodes"] if n["id"]==n2]):
                    return True
                return False
            except:
                print ([n for n in self.nodes],node1_id,node2_id)

        for e in self.edges:
            node1_id = e[0]["nodeId"]
            node2_id = e[1]["nodeId"]
            src_index = e[0]["index"]
            dst_index = e[1]["index"]
            source_port_type = "in" if is_parent(node1_id, node2_id) else "out"
            target_port_type = "out" if is_parent(node2_id, node1_id) else "in"
            type1 = self.nodes[node1_id][source_port_type + "Ports"][src_index]["type"]["name"]
            type2 = self.nodes[node2_id][target_port_type + "Ports"][dst_index]["type"]["name"]
            e[0]["type"]["name"] = type1
            e[1]["type"]["name"] = type2
            
    #--------------------------------------------------------------------------------
    def translate(self, parsed_data):

        # first pass: build our tree
        IR = super().visit(parsed_data)
        for n,(name, node) in enumerate(self.nodes.items()):
            if node["name"] == "FunctionCall":
                called_function  = self.functions[node["callee"]]
                node["outPorts"] = called_function["outPorts"]

            elif node["name"] == "If":
                p_n = self.nodes[node["parent_node"]]

                # TODO add recursive retrieveing of these (using getters and setters for example)
                node["params"]   = p_n["params"]
                node["inPorts"]  = p_n["inPorts"]
                node["outPorts"] = p_n["outPorts"]
                for n in node["branches"] + [node["condition"]]:
                    n["params"] = p_n["params"]
                    n["outPorts"] = p_n["outPorts"]
                    n["inPorts"] = p_n["inPorts"]

                node["condition"]["params"] = p_n["params"]

        if move_nodes_from_empty_branches_to_parent:
            for name, node in self.nodes.items():
                if(node["name"] in ["Then", "Else", "Condition"]):
                    if node["nodes"] == []:
                        parent_node = self.nodes[node["parent_node"]]
                        parent_node["edges"].extend(node["edges"])
                        #node["edges"] = []
                        del node["edges"]
                        print (node["name"], parent_node["name"] if "parent_node" in node else "")

        # delete the parent node references as we no longer need them
        for n,(name, node) in enumerate(self.nodes.items()):
            for name, node in self.nodes.items():
                if "parent_node" in node: del node["parent_node"]
        self.set_edges_types()
        return IR

#--------------------------------------------------------------------------------

def main(args):
    pp = pprint.PrettyPrinter(indent=0)

    grammar = Grammar(open("grammar.ini").read())

    text = open("fibs.sis").read()

    tv = TreeVisitor()
    IR = tv.translate(grammar.parse(text))

    json_data = json.dumps(IR, indent=2, sort_keys=True)
    
    gml = graphml.emit(IR, tv.nodes)
    # ~ gml = gml.replace ("<<", "less<")
    os.system ("echo '%s'| pygmentize -l xml" % gml)
    os.system ("echo '%s'| xmllint --noout -" %gml)
    
    open("IR.json", "w").write(json_data)

    # ~ os.system ("echo '%s'| jq" % json_data)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
