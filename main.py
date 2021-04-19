from parsimonious.grammar import Grammar
from parsimonious.nodes   import NodeVisitor
import pprint
import json

pp = pprint.PrettyPrinter(indent=1)

grammar = Grammar(open("grammar.ini").read())

text = open("fibs.sis").read()

class TreeVisitor(NodeVisitor):
    node_counter = 0
    def get_node_id(self):
        self.node_counter += 1
        return "node" + str(self.node_counter)
        
    def visit_function(self, node, visited_children):
        name    = visited_children[3]#.text
        nodes = visited_children[-4]
        return dict(name    = name,
                    nodes   =  nodes,
                    node_id = self.get_node_id(),
                    type    = "function")

    def visit_if_else(self, node, visited_children):
        cond,  = visited_children[2]
        then,  = visited_children[6][0]
        else_ ,= visited_children[10]
        return dict(name    = "if",
                    Cond    = cond,
                    Then    = then,
                    Else    = else_,
                    #nodes   =  [],
                    node_id = self.get_node_id(),
                    type    = "if_else")
                    
    def visit_identifier(self, node, visited_children):
        return dict(name = node.text, type = "identifier")
    
    def visit_number(self, node, visited_children):
        return dict(value = int(node.text), type = "literal")
        
    def visit_bin(self, node, visited_children):
        left, _ ,op, _ ,right = visited_children
        
        return dict(name    = "binary",
                    nodes   = [left[0], right[0]],
                    op      = op[0].text,
                    node_id = self.get_node_id(),
                    type    = "binary")
                    
    def visit_call(self, node, visited_children):
        return dict(name    = "call",
                    nodes   = visited_children[5][0],
                    node_id = self.get_node_id(),
                    type    = "call")
        
    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node

tv = TreeVisitor()
IR = tv.visit(grammar.parse(text))

json_data = json.dumps( IR, indent=2, sort_keys=True)
open("IR.json", "w").write(json_data)
pp.pprint  (IR)
