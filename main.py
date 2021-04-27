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

#plan:
# 1.function
# 2.ifelse
# 3.binary
# 4.literal
# 5.call

# edges

#save various data here for second pass (like connections between nodes)
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
#import inspect
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
        
        #print("node" + str(self.node_counter),inspect.stack()[0])
        
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

    def visit_function(self, node, visited_children):
        node_id     = self.get_node_id()
        name        = visited_children[3]["name"]

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
                               [arg["name"],

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
                         edges        = "",
                         location     = get_location(node),
                         )

        for c_n in this_node["nodes"]:
            c_n["parent_node"] = this_node["id"]

        self.nodes[node_id]  = this_node
        self.functions[name] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def visit_arg_def_list(self, node, visited_children):
        # due to recursive argument listing, the first argument and the rest are separated
        return self.unpack_rec_list (visited_children)

    #--------------------------------------------------------------------------------

    def visit_if_else(self, node, visited_children):
        node_id = self.get_node_id()

        def make_branch(node, name):
            branch_node_id = self.get_node_id()
            branch = dict(
                            nodes       = [node],
                            id          = branch_node_id,
                            name        = name,
                            edges       = [],
                            inPorts     = [],
                            outPorts    = [],
                            params      = [],
                            location    = "not applicable",
                            parent_node = node_id,
                          )
            self.nodes[branch_node_id] = branch
            return branch

        then   = make_branch(visited_children[6][0] ,"Then")
        else_  = make_branch(visited_children[10][0],"Else")
        
        condition_node_id = self.get_node_id()
        
        cond  =    dict(
                         node        = [visited_children[2][0]],
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
                         nodes     = [],
                         edges     = [],
                         inPorts   = [],
                         outPorts  = [],
                         params    = [],
                         branches  = [then, else_],
                         condition = cond,
                         id        = node_id,
                         location  = get_location(node),
                         )

        #visited_children[2]["parent_node"] = this_node["id"]

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    # TODO: replace identifiers with edges connectin current slot to master-node's input
    def visit_identifier(self, node, visited_children):

        node_id = "not applicable"#self.get_node_id()

        this_node = dict(name     = node.text,
                         id       = node_id,
                         location = get_location(node),
                         )

        #nodes[ node_id ] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def visit_number(self, node, visited_chidlren):

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

        this_node = dict(name   = "binary",
                         nodes  = [left[0], right[0]],
                         op     = op[0].text,
                         id     = node_id,
                         location = get_location(node))

        self.nodes[node_id] = this_node
        return this_node

    #--------------------------------------------------------------------------------

    def visit_call(self, node, visited_children):

        node_id       = self.get_node_id()

        args          = self.unpack_rec_list(visited_children[5])

        #TODO count args, create ports for them, connect them with edges
        function_name = visited_children[1]["name"]

        this_node = dict(
                         callee   = function_name,
                         # TODO add a check that the call has the same in_ports as the function
                         inPorts  = self.generate_inports(args, node_id),
                         outPorts = [],# see function definition to get ports count and types
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
    def translate(self, parsed_data):

        print ("translate called")

        # first pass: build our tree
        IR = super().visit(parsed_data)

        # second pass: add edges and output ports for function calls, etc.
        for name, node in self.nodes.items():
            print (name)
            if node["name"] == "FunctionCall":
                called_function = self.functions[node["callee"]]
                node["outPorts"] = called_function["outPorts"]
                #called_function["nodes"] += node["nodes"]
                #node["nodes"] = None
                
        for name, node in self.nodes.items():
            if "parent_node" in node: del node["parent_node"]
            
        return IR

#--------------------------------------------------------------------------------

tv = TreeVisitor()
IR = tv.translate(grammar.parse(text))
# second_pass(IR)
# TODO Go through all nodes and remove "parentnode"

json_data = json.dumps(IR, indent=2, sort_keys=True)
# ~ print (IR["nodes"])
# ~ open("IR.json", "w").write(json_data)
# ~ pp.pprint  (IR)
# ~ print (json_data)
#for k, v in nodes.items():            print (k)
