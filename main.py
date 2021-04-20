from parsimonious.grammar import Grammar
from parsimonious.nodes   import NodeVisitor
import pprint
import json

pp = pprint.PrettyPrinter(indent=0)

grammar = Grammar(open("grammar.ini").read())

text = open("fibs.sis").read()

def gen_ports(args, nodeId):
    ports = []
    for n, a in enumerate(args):
        ports.append(dict(
            index  = n,
            nodeId = nodeId,
            type   = {"location": "TODO: fill this", "name": "integer"}
        ))
    return ports

def unwrap_list(list_):
    while type(list_) == list:
        list_ = list_[0]
    return list_

class TreeVisitor(NodeVisitor):
    node_counter = 0
    def get_node_id(self):
        self.node_counter += 1
        return "node" + str(self.node_counter)

    def visit_function(self, node, visited_children):
        name     = visited_children[3]["name"]
        nodes    = visited_children[-4]
        args     = visited_children[7]
        num_args = len(args)
        node_id  = self.get_node_id()
        return dict(ports  = gen_ports(args, node_id),
                    name   = name,
                    nodes  = nodes,
                    nodeId = node_id,
                    type   = "function")

    def visit_arg_def_list(self, node, visited_children):
        #due to recursive argument listing, the first argument and the rest are separated
        return [visited_children[0]] + [ a[-1] for a in visited_children[1] ]

    def visit_if_else(self, node, visited_children):
        cond,  = visited_children[2]
        then,  = visited_children[6]
        else_ ,= visited_children[10]
        return dict(name   = "if",
                    Cond   = cond,
                    Then   = then,
                    Else   = else_,
                    nodeId = self.get_node_id(),
                    type   = "if_else")
                    
    # TODO: replace identifiers with connections to master-node's input
    def visit_identifier(self, node, visited_children):
        return dict(name   = node.text, 
                    type   = "identifier", 
                    nodeId = self.get_node_id())

    def visit_number(self, node, visited_children):
        node_id = self.get_node_id()
        port = {"outPorts" : [dict(index  = 0,
                              nodeId = node_id,
                              type   = {"location": "TODO: fill this", "name": "integer"})]}
                              
        return dict(value  = int(node.text), 
                    type   = "literal", 
                    nodeId = node_id,
                    ports  = port)

    def visit_bin(self, node, visited_children):
        left, _ ,op, _ ,right = visited_children

        return dict(name   = "binary",
                    nodes  = [left[0], right[0]],
                    op     = op[0].text,
                    nodeId = self.get_node_id(),
                    type   = "binary")

    def visit_call(self, node, visited_children):
        #due to recursive argument listing, the first argument and the rest are separated
        first_argument, other_arguments  = visited_children[5]

        args = [ unwrap_list( first_argument ) ] + [ unwrap_list( a[-1] ) for a in other_arguments ]
        #print( [a["nodeId"] for a in args] )
        #TODO count args, create ports for them, connect them with edges
        node_id = self.get_node_id()
        function_name = visited_children[1]["name"]
        
        return dict(callee = function_name,
                    ports  = gen_ports(args, node_id),
                    name   = "call",
                    nodes  = args,
                    nodeId = node_id,
                    type   = "call")

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node

tv = TreeVisitor()
IR = tv.visit(grammar.parse(text))

json_data = json.dumps( IR, indent=2, sort_keys=True)
#open("IR.json", "w").write(json_data)
pp.pprint  (IR)
