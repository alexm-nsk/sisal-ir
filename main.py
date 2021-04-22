from parsimonious.grammar import Grammar
from parsimonious.nodes   import NodeVisitor
import pprint
import json

pp = pprint.PrettyPrinter(indent=0)

grammar = Grammar(open("grammar.ini").read())

text = open("fibs.sis").read()


# then, else must have in ports
# binary must have in ports
# check out outports on all nodes
# check out edges
# see PEP8 for brackets

#--------------------------------------------------------------------------------

def unwrap_list(list_):

    while type(list_) == list:
        list_ = list_[0]
    return list_

#--------------------------------------------------------------------------------

class TreeVisitor(NodeVisitor):

    node_counter = 0

    #--------------------------------------------------------------------------------

    def get_node_id(self):

        self.node_counter += 1
        return "node" + str(self.node_counter)

    #--------------------------------------------------------------------------------

    def visit_std_type ( self, node, visited_children ):
        #print ("type", node.text)
        return node.text

    #--------------------------------------------------------------------------------

    def visit_type ( self, node, visited_children ):
        #print ("found type", node.text)
        return visited_children[0]

    #--------------------------------------------------------------------------------
    '''
    "params": [
                                [
                                    "M",
                                    {
                                        "index": 0,
                                        "nodeId": "node3",
                                        "type": {
                                            "location": "2:19-2:26",
                                            "name": "integer"
                                        }
                                    }
                                ]
                            ]


             "outPorts": [
                {
                    "index": 0,
                    "nodeId": "node15",
                    "type": {
                        "location": "2:35-2:42",
                        "name": "integer"
                    }
                }
            ],



                            '''
    #--------------------------------------------------------------------------------
    
    def generate_outports(self, retvals, node_id):
        return [{
                    "index" : n,
                    "nodeId" : node_id,
                    "type": {
                        "location" : "",
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
                type   = {"location": "TODO: fill this", "name": "integer"}
            ))
        return ports

    #--------------------------------------------------------------------------------
    # unpacks node lists defined by recursive grammar structures like:
    # type_list    = type (_ "," _ type)*
    #--------------------------------------------------------------------------------
    
    def unpack_req_list(self, node):
        return [node[0]]    +    [r[-1] for r in node[1]]
        
    #--------------------------------------------------------------------------------

    def visit_function(self, node, visited_children):

        node_id     = self.get_node_id()
        name        = visited_children[ 3 ]["name"]
        args        = visited_children[ 7 ]
        type_string = visited_children[ 11 ].text
        #unpack return value strings in form of a list:
        retvals     = self.unpack_req_list( visited_children[15] )
        params      = [[arg["name"],
                       {
                           "index"    : n,
                           "nodeId"   : node_id,
                           "type":
                           {
                                "location" : "",
                                "name"     : type_string
                           }
                       }]
                       for n, arg in enumerate(args) ]
                       
        nodes       = visited_children[-4 ]
        num_args    = len(args)
        
        return dict(params       = params,
                    inPorts      = self.generate_inports(args, node_id),
                    outPorts     = self.generate_outports(retvals, node_id),
                    functionName = name,
                    nodes        = nodes,
                    id           = node_id,
                    location     = "",
                    name         = "Lambda",
                    edges        = "")

    #--------------------------------------------------------------------------------

    def visit_arg_def_list(self, node, visited_children):
        #due to recursive argument listing, the first argument and the rest are separated
        return self.unpack_req_list (visited_children)

    #--------------------------------------------------------------------------------

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

    #--------------------------------------------------------------------------------

    # TODO: replace identifiers with connections to master-node's input
    def visit_identifier(self, node, visited_children):

        return dict(name   = node.text,
                    type   = "identifier",
                    nodeId = self.get_node_id())

    #--------------------------------------------------------------------------------

    def visit_number(self, node, visited_children):

        node_id = self.get_node_id()
        port = {"outPorts" : [dict(index = 0,
                              nodeId     = node_id,
                              type       = {"location": "TODO: fill this", "name": "integer"})]}

        return dict(value  = int(node.text),
                    type   = "literal",
                    nodeId = node_id,
                    ports  = port)

    #--------------------------------------------------------------------------------

    def visit_bin(self, node, visited_children):

        left, _ ,op, _ ,right = visited_children

        return dict(name   = "binary",
                    nodes  = [left[0], right[0]],
                    op     = op[0].text,
                    nodeId = self.get_node_id(),
                    type   = "binary")

    #--------------------------------------------------------------------------------

    def visit_call(self, node, visited_children):

        args          = self.unpack_req_list ( visited_children[5] )

        #TODO count args, create ports for them, connect them with edges
        node_id       = self.get_node_id()
        function_name = visited_children[1]["name"]

        return dict(callee  = function_name,
                    inPorts = self.generate_inports(args, node_id),
                    name    = "call",
                    nodes   = args,
                    nodeId  = node_id,
                    type    = "call")

    #--------------------------------------------------------------------------------

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node

#--------------------------------------------------------------------------------

tv = TreeVisitor()
IR = tv.visit(grammar.parse(text))

json_data = json.dumps( IR, indent=2, sort_keys=True)
# ~ open("IR.json", "w").write(json_data)
pp.pprint  (IR)
