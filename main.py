#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from parsimonious.grammar import Grammar
from parsimonious.nodes   import NodeVisitor

import pprint
import json

no_subs = ["Identifier", "Literal"]

#TODO no arguments case
#TODO how to access a parent node in parsimonious
#TODO find how to use named arguments in Visitors
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
        return [    {"index"  : src_index,
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

    def get_all_nodes_in_a_row(self, root_node):

        
        def _get_all_nodes_in_a_row_(node):

            retval = [node]
            if "nodes" in node:
           
                if node["name"] == "Binary":
                    #print("Binary")
                    nodes = node["nodes"]
                    #nid = lambda x:nodes[x]["id"]
                    if (not "edges" in root_node): root_node["edges"] = []
                    root_node["edges"].append(self.create_edge(nodes[0]["id"], node["id"], 0,0))
                    root_node["edges"].append(self.create_edge(nodes[1]["id"], node["id"], 0,1))
                    pass
           
                for n in node["nodes"]:
                    if not "nodes" in n:
                        # no more subnodes? append just this one
                        retval.append(n)
                    else:
                        retval += _get_all_nodes_in_a_row_(n)
            
                del (node["nodes"])
            return retval
            
        return _get_all_nodes_in_a_row_(root_node)

    #--------------------------------------------------------------------------------

    def visit_if_else(self, node, visited_children):

        node_id   = self.get_node_id()
        then_node = unwrap_list(visited_children[6][0])
        else_node = unwrap_list(visited_children[10][0])
        
        cond_node = visited_children[2][0]

        def make_branch(node, name):
            branch_node_id = self.get_node_id()
            branch = dict(
                            nodes       = node,
                            id          = branch_node_id,
                            name        = name,
                            edges       = [],
                            inPorts     = [],#\
                            outPorts    = [],#- filled out in the second pass
                            params      = [],#/
                            location    = "not applicable",
                            parent_node = node_id,
                          )
            self.nodes[branch_node_id] = branch
            return branch

        then  = make_branch(self.get_all_nodes_in_a_row(then_node), "Then")
        else_ = make_branch(self.get_all_nodes_in_a_row(else_node), "Else")

        condition_node_id = self.get_node_id()

        cond_node["parent_node"] = condition_node_id

        cond  =    dict(
                         nodes       = self.get_all_nodes_in_a_row(cond_node),
                         name        = "Condition",
                         edges       = [],
                         id          = condition_node_id,
                         inPorts     = [],
                         outPorts    = [],
                         params      = [],
                         location    = "not applicable",
                         parent_node = node_id,
                       )

        self.nodes[condition_node_id] = cond

        this_node = dict(name      = "if",
                         nodes     = [],#leave empty
                         edges     = [],
                         inPorts   = [],
                         outPorts  = [],
                         params    = [],
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

        out_ports = {"outPorts" : [dict(index  = 0,
                                        nodeId = node_id,
                                        type   = {"location": "not applicable", "name": "integer"})]}

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

    def visit_bin(self, node, visited_children):

        node_id = self.get_node_id()

        left, _ ,op, _ ,right = visited_children
        left  = left[0]
        right = right[0]
        op    = op[0]

        left ["parent_node"] = node_id
        right["parent_node"] = node_id

        this_node = dict(name        = "Binary",
                         nodes       = [left, right],
                         operator    = op.text,
                         id          = node_id,
                         location    = get_location(node))

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
                         outPorts = [],# TODO see function definition to get ports count and types
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

    def translate(self, parsed_data):

        # first pass: build our tree
        IR = super().visit(parsed_data)
        for n,(name, node) in enumerate(self.nodes.items()):
            if node["name"] == "FunctionCall":
                called_function  = self.functions[node["callee"]]
                node["outPorts"] = called_function["outPorts"]

            elif node["name"] == "if":
                p_n = self.nodes[node["parent_node"]]

                # TODO add recursive retrieveing of these (using getters and setters for example)
                node["params"]   = p_n["params"]
                node["inPorts"]  = p_n["inPorts"]
                node["outPorts"] = p_n["outPorts"]

                # TODO add parent_node to all nodes
                # TODO ifs must be nested

        # delete the parent node references as we no longer need them
        for n,(name, node) in enumerate(self.nodes.items()):
            for name, node in self.nodes.items():
                if "parent_node" in node: del node["parent_node"]

        if (False):
            # second pass: add edges and output ports for function calls, etc.
                if "parent_node" in node :
                    print (n,
                            "node:{}, parent:{}".format(
                                node["name"],
                                self.nodes[node["parent_node"]]["name"])
                          )

        # ~ print(self.get_used_identifiers(self.nodes["node10"]))


        return IR

#--------------------------------------------------------------------------------

def main(args):
    pp = pprint.PrettyPrinter(indent=0)

    grammar = Grammar(open("grammar.ini").read())

    text = open("fibs.sis").read()

    tv = TreeVisitor()
    IR = tv.translate(grammar.parse(text))

    json_data = json.dumps(IR, indent=2, sort_keys=True)
    # ~ print (IR["nodes"])
    import os
    open("IR.json", "w").write(json_data)
    # ~ pp.pprint  (IR)
    os.system ("echo '{}'| jq".format(json_data))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))

#TODO add outports for function calls
